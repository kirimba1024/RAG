import gradio as gr
import json
from pathlib import Path
from typing import Literal, Sequence
from anthropic import Anthropic
from anthropic.types import TextBlockParam, DocumentBlockParam, MessageParam, ToolResultBlockParam, PlainTextSourceParam
from html import escape

from utils import CLAUDE_MODEL, ANTHROPIC_API_KEY, load_prompt, setup_logging
from tools import MAIN_SEARCH_TOOL, EXECUTE_COMMAND_TOOL, GET_CHUNKS_TOOL, DB_QUERY_TOOLS
from retriever import main_search, get_chunks
from utils import execute_command, DB_CONNECTIONS, db_query

logger = setup_logging(Path(__file__).stem)

BASE_LLM = Anthropic(api_key=ANTHROPIC_API_KEY)

NAVIGATION = load_prompt("prompts/system_navigation.txt")
SUMMARIZE = load_prompt("prompts/system_summarize.txt")
TOOLS = [MAIN_SEARCH_TOOL, EXECUTE_COMMAND_TOOL, GET_CHUNKS_TOOL] + DB_QUERY_TOOLS
MAX_TOOL_LOOPS = 8
RAW_THRESHOLD = 12000

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

def format_tool_log(name: str, input_data: dict, result) -> str:
    input_str = json.dumps(input_data, ensure_ascii=False, indent=2)
    result_str = json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, (dict, list)) else str(result)
    return f"""
<div style="margin: 10px 0; padding: 10px; border-left: 3px solid #4CAF50; background: #f5f5f5;">
<strong>🔧 {escape(name)}</strong>
<div style="margin-top: 8px;">
<details>
<summary style="cursor: pointer; color: #2196F3;">📥 Input</summary>
<pre style="margin: 5px 0; padding: 8px; background: white; border-radius: 4px; overflow-x: auto;">{escape(input_str)}</pre>
</details>
<details>
<summary style="cursor: pointer; color: #FF9800;">📤 Result</summary>
<pre style="margin: 5px 0; padding: 8px; background: white; border-radius: 4px; overflow-x: auto;">{escape(result_str)}</pre>
</details>
</div>
</div>
"""

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
    text_chunks = [b.text for b in response.content if b.type == "text"]
    summary_text = "\n".join(text_chunks).strip()
    summary_page = page_block_from_messages([assistant_text(summary_text)])
    return history, [summary_page], []

def chat(message, history, history_pages, raw):
    logger.info(f"💬 {message}...")
    history = history or []
    history_pages = history_pages or []
    raw = raw or []
    raw.append(user_text(message))
    answers = []
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
        text_chunks = [b.text for b in response.content if b.type == "text"]
        if text_chunks:
            text = "\n".join(text_chunks)
            raw.append(assistant_text(text))
            answers.append({"role": "assistant", "content": text})
            yield history + [{"role": "user", "content": message}] + answers, history_pages, raw, ""
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            break
        tool_names = ", ".join(tu.name for tu in tool_uses)
        status = f"🔧 {tool_names}..."
        yield history + [{"role": "user", "content": message}] + answers + [{"role": "assistant", "content": status}], history_pages, raw, ""
        last_tools = [tool_use_msg(tool_uses)]
        tool_results = []
        tool_logs = []
        for tu in tool_uses:
            if tu.name == "main_search":
                result = main_search(tu.input["question"], tu.input["path_prefix"], tu.input["top_n"], tu.input.get("symbols"), tu.input.get("use_reranker", True))
            elif tu.name == "execute_command":
                result = execute_command(tu.input["command"])
            elif tu.name == "get_chunks":
                result = get_chunks(tu.input["chunk_ids"])
            elif tu.name in DB_CONNECTIONS:
                result = db_query(tu.name, tu.input["question"])
            else:
                logger.exception("Unknown tool: %s", tu.name)
                result = {"error": f"unknown tool {tu.name}"}
            tool_logs.append(format_tool_log(tu.name, tu.input, result))
            tool_results.append(tool_result_block(tu.id, result))
        if tool_logs:
            log_content = "".join(tool_logs)
            answers.append({"role": "assistant", "content": log_content})
            yield history + [{"role": "user", "content": message}] + answers, history_pages, raw, ""
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

    with gr.Row():
        message_input = gr.Textbox(
            placeholder="Задайте вопрос...", show_label=False, container=False, scale=7
        )
        submit = gr.Button("Отправить", variant="primary", scale=1)
        summarize_btn = gr.Button("Суммаризировать", scale=1)
        clear = gr.Button("Очистить", scale=1)

    gr.Examples(
        examples=[
            "Как сущности есть в этом проекте?",
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

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
