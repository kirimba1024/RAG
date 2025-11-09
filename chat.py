import gradio as gr
import json
from pathlib import Path
from anthropic import Anthropic

from utils import CLAUDE_MODEL, ANTHROPIC_API_KEY, load_prompt, setup_logging
from tools import MAIN_SEARCH_TOOL, EXECUTE_COMMAND_TOOL, GET_CHUNKS_TOOL
from retriever import main_search, get_chunks
from utils import execute_command

logger = setup_logging(Path(__file__).stem)

BASE_LLM = Anthropic(api_key=ANTHROPIC_API_KEY)

NAVIGATION = load_prompt("prompts/system_navigation.txt")
CACHE_BLOCK = {"cache_control": {"type": "ephemeral"}}
TOOLS = [MAIN_SEARCH_TOOL, EXECUTE_COMMAND_TOOL, GET_CHUNKS_TOOL]
MAX_TOOL_LOOPS = 8
RAW_THRESHOLD = 3000

def canon_json(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

def make_nav_block(text):
    return {
        "type": "document",
        "source": {"type": "text", "media_type": "application/json", "data": canon_json({"nav": text})},
        **CACHE_BLOCK
    }

SYSTEM_NAVIGATION_BLOCK = [make_nav_block(NAVIGATION)]

def make_cached_page_block(page_messages_json_str):
    return {
        "type": "document",
        "source": {
            "type": "text",
            "media_type": "application/json",
            "data": page_messages_json_str
        },
        **CACHE_BLOCK
    }

def chat(message, history, history_pages, raw):
    logger.info(f"💬 {message}...")
    history = history + [[message, ""]]
    history_pages = history_pages or []
    raw = raw or []
    messages = [json.loads(msg) for msg in raw]
    messages.append({"role": "user", "content": [{"type": "text", "text": message}]})
    page_log = [{"role": "user", "content": [{"type": "text", "text": message}]}]
    final_text_parts = []
    loops = 0
    had_any_text = False
    tool_facts = []
    while True:
        loops += 1
        if loops > MAX_TOOL_LOOPS:
            logger.warning("Max tool loops reached")
            break
        response = BASE_LLM.messages.create(
            model=CLAUDE_MODEL,
            system=SYSTEM_NAVIGATION_BLOCK + history_pages[-3:],
            messages=messages,
            tools=TOOLS,
            max_tokens=4096,
        )
        text_chunks = [b.text for b in response.content if b.type == "text"]
        if text_chunks:
            had_any_text = True
            text = "\n".join(text_chunks)
            messages.append({"role": "assistant", "content": [{"type": "text", "text": text}]})
            page_log.append({"role": "assistant", "content": [{"type": "text", "text": text}]})
            final_text_parts.append(text)
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            break
        for tu in tool_uses:
            if tu.name == "main_search":
                tool_facts.append(f"search: {tu.input.get('question', '')}@{tu.input.get('path_prefix', '')} top={tu.input.get('top_n')}")
            elif tu.name == "get_chunks":
                tool_facts.append(f"get_chunks: {len(tu.input.get('chunk_ids', []))} ids")
            elif tu.name == "execute_command":
                tool_facts.append(f"exec: {tu.input.get('command', '')[:60]}")
        messages.append({
            "role": "assistant",
            "content": [{"type": "tool_use", "id": tu.id, "name": tu.name, "input": tu.input} for tu in tool_uses]
        })
        page_log.append({
            "role": "assistant",
            "content": [{"type": "tool_use", "id": tu.id, "name": tu.name, "input": tu.input} for tu in tool_uses]
        })
        results = []
        for tu in tool_uses:
            if tu.name == "main_search":
                r = main_search(tu.input["question"], tu.input["path_prefix"], tu.input["top_n"], tu.input.get("symbols"), tu.input.get("use_reranker", True))
            elif tu.name == "execute_command":
                r = execute_command(tu.input["command"])
            elif tu.name == "get_chunks":
                r = get_chunks(tu.input["chunk_ids"])
            else:
                logger.exception("Unknown tool: %s", tu.name)
                r = {"error": f"unknown tool {tu.name}"}
            is_json = isinstance(r, (dict, list))
            results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": [{
                    "type": "document",
                    "source": {
                        "type": "text",
                        "media_type": "application/json" if is_json else "text/plain",
                        "data": canon_json(r) if is_json else str(r),
                    }
                }]
            })
        messages.append({"role": "user", "content": results})
        page_log.append({"role": "user", "content": results})
    accumulated_text = "\n".join(final_text_parts).strip()
    page_text_only = []
    for m in page_log:
        if any(c.get("type") == "text" for c in (m.get("content") or [])):
            page_text_only.append(m)
    if not had_any_text and tool_facts:
        fact_line = " · ".join(tool_facts)[:500]
        page_text_only.append({"role": "assistant", "content": [{"type": "text", "text": f"[facts] {fact_line}"}]})
    page_json = canon_json(page_text_only)
    new_page_block = make_cached_page_block(page_json)
    raw_size = sum(len(s) for s in raw) + len(page_json)
    if raw_size > RAW_THRESHOLD:
        history_pages.append(new_page_block)
        raw = []
    else:
        raw.extend([canon_json(m) for m in page_text_only])
    return history + [[message, accumulated_text]], history_pages, raw, ""


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
