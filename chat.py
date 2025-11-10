import gradio as gr
import json
from pathlib import Path
from anthropic import Anthropic
from anthropic.types import TextBlockParam, DocumentBlockParam, MessageParam, ToolResultBlockParam

from utils import CLAUDE_MODEL, ANTHROPIC_API_KEY, load_prompt, setup_logging
from tools import MAIN_SEARCH_TOOL, EXECUTE_COMMAND_TOOL, GET_CHUNKS_TOOL
from retriever import main_search, get_chunks
from utils import execute_command

logger = setup_logging(Path(__file__).stem)

BASE_LLM = Anthropic(api_key=ANTHROPIC_API_KEY)

NAVIGATION = load_prompt("prompts/system_navigation.txt")
TOOLS = [MAIN_SEARCH_TOOL, EXECUTE_COMMAND_TOOL, GET_CHUNKS_TOOL]
MAX_TOOL_LOOPS = 8
RAW_THRESHOLD = 3000

def canon_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

def text_block(value: str) -> TextBlockParam:
    return {"type": "text", "text": value}

def text_block_cached(value: str) -> TextBlockParam:
    return {"type": "text", "text": value, "cache_control": {"type": "ephemeral"}}

def doc_block(doc_data) -> DocumentBlockParam:
    is_json = isinstance(doc_data, (dict, list))
    data = canon_json(doc_data) if is_json else str(doc_data)
    media = "application/json" if is_json else "text/plain"
    return {"type": "document", "source": {"type": "text", "media_type": media, "data": data}}

def nav_block(text: str) -> TextBlockParam:
    return text_block_cached(canon_json({"nav": text}))

def page_block_from_messages(messages_list: list) -> TextBlockParam:
    return text_block_cached(canon_json(messages_list))

def msg(role: str, content) -> MessageParam:
    if isinstance(content, str):
        content = [text_block(content)]
    elif isinstance(content, dict):
        content = [content]
    return {"role": role, "content": content}

def user_text(text: str) -> MessageParam:
    return msg("user", text)

def assistant_text(text: str) -> MessageParam:
    return msg("assistant", text)

def tool_use_msg(tool_uses) -> MessageParam:
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
            answers.append(text)
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            break
        last_tools = [tool_use_msg(tool_uses)]
        tool_results = []
        for tu in tool_uses:
            if tu.name == "main_search":
                result = main_search(tu.input["question"], tu.input["path_prefix"], tu.input["top_n"], tu.input.get("symbols"), tu.input.get("use_reranker", True))
            elif tu.name == "execute_command":
                result = execute_command(tu.input["command"])
            elif tu.name == "get_chunks":
                result = get_chunks(tu.input["chunk_ids"])
            else:
                logger.exception("Unknown tool: %s", tu.name)
                result = {"error": f"unknown tool {tu.name}"}
            tool_results.append(tool_result_block(tu.id, result))
        last_tools.append(user_tool_results(tool_results))
        raw_size = sum(len(canon_json(entry)) for entry in raw)
        if raw_size > RAW_THRESHOLD:
            history_pages.append(page_block_from_messages(raw))
            raw = []
    return history + [[message, "\n".join(answers).strip()]], history_pages, raw, ""

with gr.Blocks(title="RAG Assistant") as demo:
    gr.Markdown("# 🤖 RAG Assistant\n**Claude** с инструментами для навигации по коду")
    history_pages_state = gr.State([])
    raw_state = gr.State([])

    chatbot = gr.Chatbot(
        height=600,
        placeholder="Задавайте вопросы по вашей кодовой базе",
        show_label=False,
        type="tuples",
        sanitize_html=False,
    )

    with gr.Row():
        msg = gr.Textbox(
            placeholder="Задайте вопрос...", show_label=False, container=False, scale=7
        )
        submit = gr.Button("Отправить", variant="primary", scale=1)
        clear = gr.Button("Очистить", scale=1)

    gr.Examples(
        examples=[
            "Как сущности есть в этом проекте?",
            "Объясни, как работает frontend?",
            "Найди люьбую сущность из проекта, а потом все связанные с ней места кода.",
        ],
        inputs=msg,
        label="💡 Примеры вопросов",
    )

    msg.submit(chat, inputs=[msg, chatbot, history_pages_state, raw_state], outputs=[chatbot, history_pages_state, raw_state, msg])
    submit.click(chat, inputs=[msg, chatbot, history_pages_state, raw_state], outputs=[chatbot, history_pages_state, raw_state, msg])
    clear.click(lambda: ([], [], [], ""), outputs=[chatbot, history_pages_state, raw_state, msg])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
