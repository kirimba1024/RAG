import gradio as gr
import json
from pathlib import Path
from typing import Sequence
from anthropic import Anthropic
from anthropic.types import TextBlockParam, DocumentBlockParam, MessageParam, ToolResultBlockParam
from html import escape

from utils import (
    CLAUDE_MODEL,
    ANTHROPIC_API_KEY,
    load_prompt,
    setup_logging,
    execute_command,
    DB_CONNECTIONS,
    db_query,
)
from tools import MAIN_SEARCH_TOOL, EXECUTE_COMMAND_TOOL, DB_QUERY_TOOLS
from retriever import main_search

logger = setup_logging(Path(__file__).stem)

BASE_LLM = Anthropic(api_key=ANTHROPIC_API_KEY)

NAVIGATION = load_prompt("templates/system_navigation.txt")
TOOL_OUTPUT_TEMPLATE = load_prompt("templates/tool_output.html")
TOOL_INPUT_TEMPLATE = load_prompt("templates/tool_input.html")
STATS_TEMPLATE = load_prompt("templates/stats.html")
TOOLS = [MAIN_SEARCH_TOOL, EXECUTE_COMMAND_TOOL] + DB_QUERY_TOOLS
MAX_TOOL_LOOPS = 12

TOKEN_STATS = {"input": 0, "cache_write": 0, "cache_read": 0, "output": 0}

def track_tokens(response):
    if not response.usage:
        return
    cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
    cache_creation = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
    TOKEN_STATS["input"] += response.usage.input_tokens
    TOKEN_STATS["cache_write"] += cache_creation
    TOKEN_STATS["cache_read"] += cache_read
    TOKEN_STATS["output"] += response.usage.output_tokens

def canon_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

def text_block_cached(value: str) -> TextBlockParam:
    return {"type": "text", "text": value, "cache_control": {"type": "ephemeral"}}

def doc_block(doc_data) -> DocumentBlockParam:
    data = canon_json(doc_data) if isinstance(doc_data, (dict, list)) else str(doc_data)
    return {
        "type": "document",
        "source": {"type": "text", "media_type": "text/plain", "data": data},
    }

def user_text(text: str) -> MessageParam | None:
    text = (text or "").strip()
    if not text:
        return None
    return {"role": "user", "content": [{"type": "text", "text": text}]}

def assistant_text(text: str) -> MessageParam | None:
    text = (text or "").strip()
    if not text:
        return None
    return {"role": "assistant", "content": [{"type": "text", "text": text}]}

def ui_msg(role: str, text: str) -> dict:
    return {"role": role, "content": text}

def tool_use_msg(tool_uses: Sequence) -> MessageParam:
    return {
        "role": "assistant",
        "content": [
            {"type": "tool_use", "id": tu.id, "name": tu.name, "input": tu.input}
            for tu in tool_uses
        ],
    }

def tool_result_block(tool_use_id: str, tool_result_data) -> ToolResultBlockParam:
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": [doc_block(tool_result_data)],
    }

def user_tool_results(results: list) -> MessageParam:
    return {"role": "user", "content": results}

SYSTEM_NAVIGATION_BLOCK = text_block_cached(canon_json({"nav": NAVIGATION}))

def format_tool_input(name: str, input_data: dict) -> str:
    return TOOL_INPUT_TEMPLATE.format(
        name=escape(name),
        input=escape(json.dumps(input_data, ensure_ascii=False, indent=2)),
    )

def format_tool_output(name: str, result) -> str:
    if isinstance(result, (dict, list)):
        result_str = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        result_str = str(result)
    return TOOL_OUTPUT_TEMPLATE.format(name=escape(name), result=escape(result_str))

def get_text_chunks(response) -> list[str]:
    return [
        b.text.strip()
        for b in response.content
        if b.type == "text" and b.text.strip()
    ]

def update_stats(history_pages):
    texts = [p["text"] for p in history_pages[-3:]]
    texts = [""] * (3 - len(texts)) + texts
    chars = [len(t) for t in texts]
    input_total = (
        TOKEN_STATS["input"]
        + TOKEN_STATS["cache_write"]
        + TOKEN_STATS["cache_read"]
    )
    paid_equiv = (
        TOKEN_STATS["input"]
        + 1.25 * TOKEN_STATS["cache_write"]
        + 0.1 * TOKEN_STATS["cache_read"]
    )
    total_equiv = paid_equiv + TOKEN_STATS["output"]
    saved_equiv = input_total - paid_equiv
    return STATS_TEMPLATE.format(
        pages_count=len(history_pages),
        page1_chars=chars[2],
        page2_chars=chars[1],
        page3_chars=chars[0],
        page1_text=escape(texts[2]),
        page2_text=escape(texts[1]),
        page3_text=escape(texts[0]),
        total_equiv=total_equiv,
        saved_equiv=saved_equiv,
        input=TOKEN_STATS["input"],
        cache_write=TOKEN_STATS["cache_write"],
        cache_read=TOKEN_STATS["cache_read"],
        output=TOKEN_STATS["output"],
    )

def chat(message, history, history_pages):
    message = (message or "").strip()
    logger.info("💬 %s...", message)
    history = history or []
    history_pages = history_pages or []
    if not message:
        yield history, history_pages, ""
        return
    raw: list[MessageParam] = []
    user_msg = user_text(message)
    if user_msg:
        raw.append(user_msg)
    answers = []
    current_history = history + [ui_msg("user", message)]
    yield current_history, history_pages, ""
    loops = 0
    last_tool_use: list[MessageParam] = []
    last_tool_results: list[MessageParam] = []
    while True:
        loops += 1
        if loops > MAX_TOOL_LOOPS:
            break
        try:
            response = BASE_LLM.messages.create(
                model=CLAUDE_MODEL,
                system=[SYSTEM_NAVIGATION_BLOCK] + history_pages[-3:],
                messages=raw + last_tool_use + last_tool_results,
                tools=TOOLS,
                max_tokens=4096,
            )
        except Exception:
            logger.exception("Ошибка при вызове LLM")
            answers.append(ui_msg("assistant", "Произошла ошибка при обращении к модели. Посмотри логи."))
            yield current_history + answers, history_pages, ""
            return
        track_tokens(response)
        last_tool_use = []
        last_tool_results = []
        text_chunks = get_text_chunks(response)
        if text_chunks:
            text = "\n".join(text_chunks)
            logger.info("🤖 %s", text)
            assistant_msg = assistant_text(text)
            if assistant_msg:
                raw.append(assistant_msg)
            answers.append(ui_msg("assistant", text))
            yield current_history + answers, history_pages, ""
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if tool_uses:
            logger.info("🔧 Использование инструментов: %s", tool_uses)
            last_tool_use = [tool_use_msg(tool_uses)]
            input_logs = [format_tool_input(tu.name, tu.input) for tu in tool_uses]
            if input_logs:
                answers.append(ui_msg("assistant", "".join(input_logs)))
                yield current_history + answers, history_pages, ""
            tool_results = []
            for tu in tool_uses:
                if tu.name == "main_search":
                    result = main_search(
                        tu.input["question"],
                        tu.input["path_prefix"],
                        tu.input["top_n"],
                        tu.input.get("symbols"),
                        tu.input.get("use_reranker", True),
                    )
                elif tu.name == "execute_command":
                    result = execute_command(tu.input["command"])
                elif tu.name in DB_CONNECTIONS:
                    result = db_query(tu.name, tu.input["question"])
                else:
                    result = {"error": f"unknown tool {tu.name}"}
                logger.info(
                    "🔧 %s: input=%s, result=%s",
                    tu.name,
                    canon_json(tu.input),
                    canon_json(result) if isinstance(result, (dict, list)) else str(result),
                )
                answers.append(ui_msg("assistant", format_tool_output(tu.name, result)))
                yield current_history + answers, history_pages, ""
                tool_results.append(tool_result_block(tu.id, result))
            last_tool_results = [user_tool_results(tool_results)]
        if not tool_uses:
            break
    if raw:
        history_pages.append(text_block_cached(canon_json(raw)))
        logger.info("📝 Добавлена новая страница, всего страниц: %d", len(history_pages))
    yield current_history + answers, history_pages, ""

with gr.Blocks(title="RAG Assistant") as demo:
    gr.Markdown("# 🤖 RAG Assistant\n**Claude** с инструментами для навигации по коду")
    history_pages_state = gr.State([])

    chatbot = gr.Chatbot(
        height=600,
        placeholder="Задавайте вопросы по вашей кодовой базе",
        show_label=False,
        type="messages",
        sanitize_html=False,
    )

    token_display = gr.Markdown(value=update_stats([]))

    with gr.Row():
        message_input = gr.Textbox(
            placeholder="Задайте вопрос...", show_label=False, container=False, scale=7
        )
        submit = gr.Button("Отправить", variant="primary", scale=1)
        clear = gr.Button("Очистить", scale=1)

    gr.Examples(
        examples=[
            "Как сущности есть?",
            "Объясни, как работает frontend?",
            "Найди любую сущность из проекта, а потом все связанные с ней места кода.",
        ],
        inputs=message_input,
        label="💡 Примеры вопросов",
    )

    def clear_chat():
        return [], [], ""

    def update_stats_hook(history_pages):
        return update_stats(history_pages)

    chat_fn = message_input.submit(
        chat,
        inputs=[message_input, chatbot, history_pages_state],
        outputs=[chatbot, history_pages_state, message_input],
    )
    chat_fn.then(update_stats_hook, inputs=[history_pages_state], outputs=[token_display])
    submit_fn = submit.click(
        chat,
        inputs=[message_input, chatbot, history_pages_state],
        outputs=[chatbot, history_pages_state, message_input],
    )
    submit_fn.then(update_stats_hook, inputs=[history_pages_state], outputs=[token_display])

    clear_fn = clear.click(clear_chat, outputs=[chatbot, history_pages_state, message_input])
    clear_fn.then(lambda: update_stats([]), outputs=[token_display])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
