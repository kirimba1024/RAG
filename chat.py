import gradio as gr
import json
import time
import html
from pathlib import Path
from anthropic import Anthropic

from utils import CLAUDE_MODEL, ANTHROPIC_API_KEY, load_prompt, setup_logging
from tools import (
    TOOLS_SCHEMA,
    main_search,
    query_graph,
    code_stats,
    architecture_stats,
    execute_command,
)

logger = setup_logging(Path(__file__).stem)

BASE_LLM = Anthropic(api_key=ANTHROPIC_API_KEY)
NAVIGATION = load_prompt("prompts/chat_system_navigation.txt")
CHAT_GATHER = load_prompt("prompts/chat_system_gather.txt")
CHAT_ANSWER = load_prompt("prompts/chat_system_answer.txt")
CACHE_BLOCK = {"cache_control": {"type": "ephemeral"}}
TOOLS_MAP = {
    "main_search": lambda p: main_search(p["question"], p.get("path_prefix", "")),
    "query_graph": lambda p: query_graph(p["query"], p.get("limit", 20)),
    "code_stats": lambda p: code_stats(p.get("path_prefix", "")),
    "architecture_stats": lambda p: architecture_stats(p.get("path_prefix", "")),
    "execute_command": lambda p: execute_command(p["command"]),
}

def system_block(text):
    return [{"type": "text", "text": text, **CACHE_BLOCK}]

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
    system_navigation = system_block(NAVIGATION)
    system_gather = system_block(CHAT_GATHER)
    system_answer = system_block(CHAT_ANSWER)
    system_summary = system_block(summary)
    assistant_content = []
    current_text = ""
    current_tool = None
    with BASE_LLM.messages.stream(
        model=CLAUDE_MODEL,
        system=system_navigation + system_gather + system_summary,
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
            f"### 🔧 {tool_use['name']} ({(time.perf_counter() - t0):.2f}s)\n\n"
            f"**Аргументы:**\n"
            f"```json\n{json.dumps(tool_use['input'], ensure_ascii=False, indent=2)}\n```\n\n"
            f"**Результат:**\n"
            f"```\n{str(result)}\n```\n\n"
        )
        yield history + [[message, accumulated_text]], summary, ""
        tool_results.append(
            {
                "type": "tool_result",
                "tool_use_id": tool_use["id"],
                "content": str(result),
            }
        )
    messages.append({"role": "assistant", "content": assistant_content})
    messages.append({"role": "user", "content": tool_results})
    logger.info(f"🔄 Этап 2: ANSWER")
    summary = ""
    with BASE_LLM.messages.stream(
        model=CLAUDE_MODEL,
        system=system_navigation + system_answer + system_summary,
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
