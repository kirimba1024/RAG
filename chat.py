import gradio as gr
import json
from pathlib import Path
from typing import Literal, Sequence
from anthropic import Anthropic
from anthropic.types import TextBlockParam, DocumentBlockParam, MessageParam, ToolResultBlockParam, PlainTextSourceParam
from html import escape

from utils import CLAUDE_MODEL, ANTHROPIC_API_KEY, load_prompt, setup_logging
from tools import MAIN_SEARCH_TOOL, EXECUTE_COMMAND_TOOL, DB_QUERY_TOOLS
from retriever import main_search
from utils import execute_command, DB_CONNECTIONS, db_query

logger = setup_logging(Path(__file__).stem)

BASE_LLM = Anthropic(api_key=ANTHROPIC_API_KEY)

NAVIGATION = load_prompt("templates/system_navigation.txt")
SUMMARIZE = load_prompt("templates/system_summarize.txt")
TOOL_OUTPUT_TEMPLATE = load_prompt("templates/tool_output.html")
TOOL_INPUT_TEMPLATE = load_prompt("templates/tool_input.html")
TOOLS = [MAIN_SEARCH_TOOL, EXECUTE_COMMAND_TOOL] + DB_QUERY_TOOLS
MAX_TOOL_LOOPS = 8
RAW_THRESHOLD = 12000

TOKEN_STATS = {"input": 0, "cache_write": 0, "cache_read": 0, "output": 0}

def track_tokens(response):
    if response.usage:
        cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
        cache_creation = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
        TOKEN_STATS["input"] += response.usage.input_tokens
        TOKEN_STATS["cache_write"] += cache_creation
        TOKEN_STATS["cache_read"] += cache_read
        TOKEN_STATS["output"] += response.usage.output_tokens


def canon_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

def text_block(value: str) -> TextBlockParam:
    return {"type": "text", "text": value}

def text_block_cached(value: str) -> TextBlockParam:
    return {"type": "text", "text": value, "cache_control": {"type": "ephemeral"}}

def doc_block(doc_data) -> DocumentBlockParam:
    is_json = isinstance(doc_data, (dict, list))
    data = canon_json(doc_data) if is_json else str(doc_data)
    media_type: Literal["text/plain"] = "text/plain"
    source: PlainTextSourceParam = {"type": "text", "media_type": media_type, "data": data}
    return {"type": "document", "source": source}

def nav_block(text: str) -> TextBlockParam:
    return text_block_cached(canon_json({"nav": text}))

def summarize_block(text: str) -> TextBlockParam:
    return text_block_cached(canon_json({"summarize": text}))

def page_block_from_messages(messages_list: list) -> TextBlockParam:
    return text_block_cached(canon_json(messages_list))

def msg(role: Literal["user", "assistant"], content) -> MessageParam:
    if isinstance(content, str):
        content = [text_block(content)]
    elif isinstance(content, dict):
        content = [content]
    return {"role": role, "content": content}

def user_text(text: str) -> MessageParam:
    return msg("user", text)

def assistant_text(text: str) -> MessageParam:
    return msg("assistant", text)

def tool_use_msg(tool_uses: Sequence) -> MessageParam:
    return msg("assistant", [
        {"type": "tool_use", "id": tu.id, "name": tu.name, "input": tu.input}
        for tu in tool_uses
    ])

def tool_result_block(tool_use_id: str, tool_result_data) -> ToolResultBlockParam:
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": [doc_block(tool_result_data)],
    }

def user_tool_results(results: list) -> MessageParam:
    return {"role": "user", "content": results}

SYSTEM_NAVIGATION_BLOCK = nav_block(NAVIGATION)
SYSTEM_SUMMARIZE_BLOCK = summarize_block(SUMMARIZE)

def format_tool_input(name: str, input_data: dict) -> str:
    input_str = json.dumps(input_data, ensure_ascii=False, indent=2)
    return TOOL_INPUT_TEMPLATE.format(
        name=escape(name),
        input=escape(input_str)
    )

def format_tool_output(name: str, result) -> str:
    result_str = json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, (dict, list)) else str(result)
    return TOOL_OUTPUT_TEMPLATE.format(
        name=escape(name),
        result=escape(result_str)
    )

def summarize_dialog(history, history_pages, raw):
    logger.info("📝 Суммаризация диалога...")
    history = history or []
    history_pages = history_pages or []
    raw = raw or []
    all_messages = []
    for page in history_pages:
        page_data = json.loads(page["text"])
        all_messages.extend(page_data)
    all_messages.extend(raw)
    if not all_messages:
        logger.warning("Нет данных для суммаризации")
        return history, history_pages, raw
    response = BASE_LLM.messages.create(
        model=CLAUDE_MODEL,
        system=[SYSTEM_SUMMARIZE_BLOCK],
        messages=all_messages,
        max_tokens=4096,
    )
    track_tokens(response)
    text_chunks = [b.text for b in response.content if b.type == "text"]
    summary_text = "\n".join(text_chunks).strip()
    summary_page = page_block_from_messages([assistant_text(summary_text)])
    summary_message = {"role": "assistant", "content": f"📝 **Суммаризация диалога:**\n\n{summary_text}"}
    updated_history = history + [summary_message]
    return updated_history, [summary_page], []

def chat(message, history, history_pages, raw):
    logger.info(f"💬 {message}...")
    history = history or []
    history_pages = history_pages or []
    raw = raw or []
    raw.append(user_text(message))
    answers = []
    yield history + [{"role": "user", "content": message}], history_pages, raw, ""
    loops = 0
    last_tools = []
    while True:
        loops += 1
        if loops > MAX_TOOL_LOOPS:
            logger.warning("Max tool loops reached")
            break
        response = BASE_LLM.messages.create(
            model=CLAUDE_MODEL,
            system=[SYSTEM_NAVIGATION_BLOCK] + history_pages[-3:],
            messages=raw + last_tools,
            tools=TOOLS,
            max_tokens=4096,
        )
        track_tokens(response)
        text_chunks = [b.text for b in response.content if b.type == "text" and b.text.strip()]
        if text_chunks:
            text = "\n".join(text_chunks)
            logger.info(f"🤖 {text}")
            raw.append(assistant_text(text))
            answers.append({"role": "assistant", "content": text})
            yield history + [{"role": "user", "content": message}] + answers, history_pages, raw, ""
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            break
        logger.info(f"🔧 Использование инструментов: {tool_uses}")
        input_logs = [format_tool_input(tu.name, tu.input) for tu in tool_uses]
        if input_logs:
            input_content = "".join(input_logs)
            answers.append({"role": "assistant", "content": input_content})
            yield history + [{"role": "user", "content": message}] + answers, history_pages, raw, ""
        last_tools = [tool_use_msg(tool_uses)]
        tool_results = []
        for tu in tool_uses:
            if tu.name == "main_search":
                result = main_search(tu.input["question"], tu.input["path_prefix"], tu.input["top_n"], tu.input.get("symbols"), tu.input.get("use_reranker", True))
            elif tu.name == "execute_command":
                result = execute_command(tu.input["command"])
            elif tu.name in DB_CONNECTIONS:
                result = db_query(tu.name, tu.input["question"])
            else:
                logger.exception("Unknown tool: %s", tu.name)
                result = {"error": f"unknown tool {tu.name}"}
            input_preview = json.dumps(tu.input, ensure_ascii=False, separators=(",", ":"))
            result_preview = json.dumps(result, ensure_ascii=False, separators=(",", ":")) if isinstance(result, (dict, list)) else str(result)
            logger.info(f"🔧 {tu.name}: input={input_preview}, result={result_preview}")
            result_content = format_tool_output(tu.name, result)
            answers.append({"role": "assistant", "content": result_content})
            yield history + [{"role": "user", "content": message}] + answers, history_pages, raw, ""
            tool_results.append(tool_result_block(tu.id, result))
        last_tools.append(user_tool_results(tool_results))
        raw_size = sum(len(canon_json(entry)) for entry in raw)
        if raw_size > RAW_THRESHOLD:
            history_pages.append(page_block_from_messages(raw))
            raw = []
    yield history + [{"role": "user", "content": message}] + answers, history_pages, raw, ""

with gr.Blocks(title="RAG Assistant") as demo:
    gr.Markdown("# 🤖 RAG Assistant\n**Claude** с инструментами для навигации по коду")
    history_pages_state = gr.State([])
    raw_state = gr.State([])

    chatbot = gr.Chatbot(
        height=600,
        placeholder="Задавайте вопросы по вашей кодовой базе",
        show_label=False,
        type="messages",
        sanitize_html=False,
    )

    def update_tokens():
        if TOKEN_STATS["input"] == 0 and TOKEN_STATS["output"] == 0:
            return "Токены: 0"
        input_total = TOKEN_STATS["input"] + TOKEN_STATS["cache_write"] + TOKEN_STATS["cache_read"]
        paid_equiv = TOKEN_STATS["input"] + 1.25 * TOKEN_STATS["cache_write"] + 0.1 * TOKEN_STATS["cache_read"]
        total_equiv = paid_equiv + TOKEN_STATS["output"]
        saved_equiv = input_total - paid_equiv
        return f"Токены: {total_equiv:,.0f} (экономия: {saved_equiv:,.0f})<br>Сырые: input={TOKEN_STATS['input']:,}, cache_write={TOKEN_STATS['cache_write']:,}, cache_read={TOKEN_STATS['cache_read']:,}, output={TOKEN_STATS['output']:,}"

    token_display = gr.Markdown(update_tokens())

    with gr.Row():
        message_input = gr.Textbox(
            placeholder="Задайте вопрос...", show_label=False, container=False, scale=7
        )
        submit = gr.Button("Отправить", variant="primary", scale=1)
        summarize_btn = gr.Button("Суммаризировать", scale=1)
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

    message_input.submit(chat, inputs=[message_input, chatbot, history_pages_state, raw_state], outputs=[chatbot, history_pages_state, raw_state, message_input])
    submit.click(chat, inputs=[message_input, chatbot, history_pages_state, raw_state], outputs=[chatbot, history_pages_state, raw_state, message_input])
    summarize_btn.click(summarize_dialog, inputs=[chatbot, history_pages_state, raw_state], outputs=[chatbot, history_pages_state, raw_state])
    clear.click(lambda: ([], [], [], ""), outputs=[chatbot, history_pages_state, raw_state, message_input])

    timer = gr.Timer(value=1, active=True)
    timer.tick(update_tokens, outputs=[token_display])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
