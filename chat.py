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

def system_block(text):
    return [{"type": "text", "text": text, **CACHE_BLOCK}]

SYSTEM_NAVIGATION_BLOCK = system_block(NAVIGATION)

RAW_THRESHOLD = 3000

def canon_json(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

def chat(message, history, history_pages, raw):
    logger.info(f"💬 {message}...")
    history = history + [[message, ""]]
    history_pages = history_pages or []
    raw = raw or []
    responses = []
    tool_results_list = []
    while True:
        messages = [json.loads(msg) for msg in raw]
        messages.append({"role": "user", "content": [{"type": "text", "text": message}]})
        for i, response in enumerate(responses):
            text_blocks = [block.text for block in response.content if block.type == "text"]
            if text_blocks:
                messages.append({"role": "assistant", "content": [{"type": "text", "text": "\n".join(text_blocks)}]})
            if i < len(tool_results_list):
                messages.append({"role": "user", "content": tool_results_list[i]})
        response = BASE_LLM.messages.create(
            model=CLAUDE_MODEL,
            system=SYSTEM_NAVIGATION_BLOCK + history_pages[-3:],
            messages=messages,
            tools=[MAIN_SEARCH_TOOL, EXECUTE_COMMAND_TOOL, GET_CHUNKS_TOOL],
            max_tokens=4096,
        )
        responses.append(response)
        tool_uses = [block for block in response.content if block.type == "tool_use"]
        if not tool_uses:
            break
        tool_results = []
        for tool_use in tool_uses:
            if tool_use.name == "main_search":
                result = main_search(tool_use.input["question"], tool_use.input["path_prefix"], tool_use.input["top_n"], tool_use.input.get("symbols"), tool_use.input.get("use_reranker", True))
            elif tool_use.name == "execute_command":
                result = execute_command(tool_use.input["command"])
            elif tool_use.name == "get_chunks":
                result = get_chunks(tool_use.input["chunk_ids"])
            else:
                logger.exception("Unknown tool: %s", tool_use.name)
                result = f"Ошибка: неизвестный инструмент {tool_use.name}"
            media_type = "application/json" if isinstance(result, (list, dict)) else "text/plain"
            data = json.dumps(result, ensure_ascii=False, separators=(",", ":")) if isinstance(result, (list, dict)) else str(result)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": [{
                    "type": "document",
                    "source": {
                        "type": "text",
                        "media_type": media_type,
                        "data": data
                    }
                }]
            })
        tool_results_list.append(tool_results)
    accumulated_text = "".join(block.text for response in responses for block in response.content if block.type == "text")
    page_messages = [{"role": "user", "content": [{"type": "text", "text": message}]}]
    for response in responses:
        text_blocks = [block.text for block in response.content if block.type == "text"]
        if text_blocks:
            page_messages.append({"role": "assistant", "content": [{"type": "text", "text": "\n".join(text_blocks)}]})
    new_page_block = {"type": "text", "text": canon_json(page_messages), **CACHE_BLOCK}
    raw_size = sum(len(msg) for msg in raw) + len(new_page_block["text"])
    if raw_size > RAW_THRESHOLD:
        history_pages.append(new_page_block)
        raw = []
    else:
        raw.extend([canon_json(msg) for msg in page_messages])
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
            "Как устроен граф знаний в этом проекте?",
            "Объясни, как работает frontend?",
            "Какие промпты используются в проекте?",
        ],
        inputs=msg,
        label="💡 Примеры вопросов",
    )

    msg.submit(chat, inputs=[msg, chatbot, history_pages_state, raw_state], outputs=[chatbot, history_pages_state, raw_state, msg])
    submit.click(chat, inputs=[msg, chatbot, history_pages_state, raw_state], outputs=[chatbot, history_pages_state, raw_state, msg])
    clear.click(lambda: ([], [], [], ""), outputs=[chatbot, history_pages_state, raw_state, msg])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
