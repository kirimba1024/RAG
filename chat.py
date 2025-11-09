import gradio as gr
import json
from pathlib import Path
from anthropic import Anthropic

from utils import CLAUDE_MODEL, ANTHROPIC_API_KEY, load_prompt, setup_logging
from tools import MAIN_SEARCH_TOOL, EXECUTE_COMMAND_TOOL, execute_tool

logger = setup_logging(Path(__file__).stem)

BASE_LLM = Anthropic(api_key=ANTHROPIC_API_KEY)

NAVIGATION = load_prompt("prompts/system_navigation.txt")
SUMMARIZE = load_prompt("prompts/system_summarize.txt")
CACHE_BLOCK = {"cache_control": {"type": "ephemeral"}}

def system_block(text):
    return [{"type": "text", "text": text, **CACHE_BLOCK}]

SYSTEM_NAVIGATION_BLOCK = system_block(NAVIGATION)
SYSTEM_SUMMARIZE_BLOCK = system_block(SUMMARIZE)

def summarize_context(messages):
    response = BASE_LLM.messages.create(
        model=CLAUDE_MODEL,
        system=SYSTEM_SUMMARIZE_BLOCK,
        messages=messages,
        max_tokens=4096,
    )
    return "".join(block.text for block in response.content if block.type == "text")

def to_api_messages(user_messages, responses, tool_results_list):
    messages = [{"role": "user", "content": [{"type": "text", "text": msg}]} for msg in user_messages]
    for i, response in enumerate(responses):
        text_blocks = [block.text for block in response.content if block.type == "text"]
        if text_blocks:
            messages.append({"role": "assistant", "content": [{"type": "text", "text": "\n".join(text_blocks)}]})
        if i < len(tool_results_list):
            messages.append({"role": "user", "content": tool_results_list[i]})
    return messages

def create_tool_results(tool_uses):
    tool_results = []
    for tool_use in tool_uses:
        result = execute_tool(tool_use.name, tool_use.input)
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
    return tool_results

def chat(message, history, summary):
    logger.info(f"💬 {message}...")
    history = history + [[message, ""]]
    user_messages = [message]
    if summary:
        user_messages.insert(0, f"[Контекст из предыдущих сообщений]\n{summary}")
    responses = []
    tool_results_list = []
    while True:
        api_messages = to_api_messages(user_messages, responses, tool_results_list)
        response = BASE_LLM.messages.create(
            model=CLAUDE_MODEL,
            system=SYSTEM_NAVIGATION_BLOCK,
            messages=api_messages,
            tools=[MAIN_SEARCH_TOOL, EXECUTE_COMMAND_TOOL],
            max_tokens=4096,
        )
        responses.append(response)
        tool_uses = [block for block in response.content if block.type == "tool_use"]
        if not tool_uses:
            break
        tool_results_list.append(create_tool_results(tool_uses))
    accumulated_text = "".join(block.text for response in responses for block in response.content if block.type == "text")
    summary = accumulated_text
    return history + [[message, accumulated_text]], summary, ""


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

    msg.submit(chat, inputs=[msg, chatbot, summary_state], outputs=[chatbot, summary_state, msg])
    submit.click(chat, inputs=[msg, chatbot, summary_state], outputs=[chatbot, summary_state, msg])
    clear.click(lambda: ([], "", ""), outputs=[chatbot, summary_state, msg])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
