import gradio as gr
import json
import time
import html
from pathlib import Path
from anthropic import Anthropic
from llama_index.core.prompts.chat_prompts import CHAT_REFINE_PROMPT
from llama_index.llms.openai.utils import CHAT_MODELS

from utils import CLAUDE_MODEL, ANTHROPIC_API_KEY, load_prompt, setup_logging
from tools import (
    TOOLS_SCHEMA,
    main_search,
    grep_files,
    browse_path,
    query_graph,
    read_file_lines,
)

logger = setup_logging(Path(__file__).stem)

BASE_LLM = Anthropic(api_key=ANTHROPIC_API_KEY)
CHAT_GATHER = load_prompt("prompts/chat_system_gather.txt")
CHAT_ANSWER = load_prompt("prompts/chat_system_answer.txt")
CACHE_BLOCK = {"cache_control": {"type": "ephemeral"}}
TOOLS_MAP = {
    "main_search": lambda p: main_search(p["question"], p.get("path_prefix", "")),
    "grep_files": lambda p: grep_files(p["pattern"], p.get("path_prefix", ""), p.get("case_sensitive", True)),
    "browse_path": lambda p: browse_path(p.get("path", "")),
    "query_graph": lambda p: query_graph(p["query"], p.get("limit", 20)),
    "read_file_lines": lambda p: read_file_lines(p["path"], p["start_line"], p["end_line"]),
}


def system_block(text, summary=""):
    blocks = [{"type": "text", "text": text, **CACHE_BLOCK}]
    if summary:
        blocks.append({"type": "text", "text": summary, **CACHE_BLOCK})
    return blocks


def execute_tool(tool_name, tool_input):
    try:
        return TOOLS_MAP[tool_name](tool_input)
    except Exception as e:
        logger.exception("Tool failed: %s %s", tool_name, tool_input)
        return f"Ошибка: {e}"


def chat(message, history, summary):
    logger.info(f"💬 {message}...")
    accumulated_text = ""
    messages = [{"role": "user", "content": [{"type": "text", "text": message}]}]
    logger.info(f"🔄 Этап 1: GATHER")
    system_gather = system_block(CHAT_GATHER, summary)
    system_answer = system_block(CHAT_ANSWER, summary)
    assistant_content = []
    current_text = ""
    current_tool = None
    with BASE_LLM.messages.stream(
        model=CLAUDE_MODEL,
        system=system_gather,
        messages=messages,
        tools=TOOLS_SCHEMA,
        max_tokens=4096,
    ) as stream:
        for event in stream:
            if event.type == "content_block_start":
                if event.content_block.type == "text":
                    current_text = ""
                elif event.content_block.type == "tool_use":
                    current_tool = {
                        "type": "tool_use",
                        "id": event.content_block.id,
                        "name": event.content_block.name,
                        "input": "",
                    }
            elif event.type == "content_block_delta":
                if event.delta.type == "text_delta":
                    current_text += event.delta.text
                    accumulated_text += event.delta.text
                    yield history + [[message, accumulated_text]], summary, ""
                elif event.delta.type == "input_json_delta":
                    current_tool["input"] += event.delta.partial_json
            elif event.type == "content_block_stop":
                if current_text:
                    assistant_content.append({"type": "text", "text": current_text})
                    current_text = ""
                if current_tool:
                    current_tool["input"] = (
                        json.loads(current_tool["input"])
                        if current_tool["input"]
                        else {}
                    )
                    assistant_content.append(current_tool)
                    current_tool = None
    tool_uses = [b for b in assistant_content if b.get("type") == "tool_use"]
    if not tool_uses:
        logger.error(f"⚠️ ОШИБКА: Этап 1 не вернул инструменты!")
        yield history + [[message, accumulated_text]], summary, ""
        return
    logger.info(f"📋 Выполнение {len(tool_uses)} инструментов")
    tool_results = []
    for tool_use in tool_uses:
        t0 = time.perf_counter()
        result = execute_tool(tool_use["name"], tool_use["input"])
        accumulated_text += (
            f"<details><summary>🔧 <b>{tool_use['name']}</b></summary>\n"
            f"<details open><summary>📥 <b>Аргументы</b></summary>\n"
            f"<pre>{html.escape(json.dumps(tool_use['input'], ensure_ascii=False, indent=2))}</pre>\n"
            f"</details>\n"
            f"✓ {(time.perf_counter() - t0):.2f}s\n"
            f"<details open><summary>📤 <b>Результат</b></summary>\n"
            f"<pre>{html.escape(json.dumps(result, ensure_ascii=False, indent=2))}</pre>\n"
            f"</details>\n"
            f"</details>\n"
        )
        yield history + [[message, accumulated_text]], summary, ""
        tool_results.append(
            {
                "type": "tool_result",
                "tool_use_id": tool_use["id"],
                "content": json.dumps(result, ensure_ascii=False),
            }
        )
    messages.append({"role": "assistant", "content": assistant_content})
    messages.append({"role": "user", "content": tool_results})
    logger.info(f"🔄 Этап 2: ANSWER")
    summary = ""
    with BASE_LLM.messages.stream(
        model=CLAUDE_MODEL,
        system=system_answer,
        messages=messages,
        tools=TOOLS_SCHEMA,
        max_tokens=4096,
    ) as stream:
        for event in stream:
            if event.type == "content_block_delta" and event.delta.type == "text_delta":
                accumulated_text += event.delta.text
                summary += event.delta.text
                yield history + [[message, accumulated_text]], summary, ""

    yield history + [[message, accumulated_text]], summary, ""


with gr.Blocks(title="RAG Assistant") as demo:
    gr.Markdown("# 🤖 RAG Assistant\n**Claude** с инструментами для навигации по коду")
    summary_state = gr.State("")

    chatbot = gr.Chatbot(
        height=600,
        placeholder="Задавайте вопросы по вашей кодовой базе",
        show_label=False,
        type="tuples",
        sanitize_html=False,
    )

    with gr.Row():
        msg = gr.Textbox(
            placeholder="Задайте вопрос...", show_label=False, container=False, scale=8
        )
        submit = gr.Button("Отправить", variant="primary", scale=1)
        stop = gr.Button("⏹️ Прервать", variant="stop", scale=1)
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

    submit_event = msg.submit(
        chat,
        inputs=[msg, chatbot, summary_state],
        outputs=[chatbot, summary_state, msg],
    )
    click_event = submit.click(
        chat,
        inputs=[msg, chatbot, summary_state],
        outputs=[chatbot, summary_state, msg],
    )
    stop.click(None, None, None, cancels=[submit_event, click_event])
    clear.click(lambda: ([], "", ""), outputs=[chatbot, summary_state, msg])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
