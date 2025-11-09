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

RAW_THRESHOLD = 8000

def extract_messages_from_history(user_msg, responses, tool_results_list):
    messages = []
    messages.append({"role": "user", "content": [{"type": "text", "text": user_msg}]})
    for i, response in enumerate(responses):
        text_blocks = [block.text for block in response.content if block.type == "text"]
        if text_blocks:
            messages.append({"role": "assistant", "content": [{"type": "text", "text": "\n".join(text_blocks)}]})
        if i < len(tool_results_list):
            messages.append({"role": "user", "content": tool_results_list[i]})
    return messages

def summarize_context(messages):
    response = BASE_LLM.messages.create(
        model=CLAUDE_MODEL,
        system=SYSTEM_SUMMARIZE_BLOCK,
        messages=messages,
        max_tokens=4096,
    )
    return "".join(block.text for block in response.content if block.type == "text")

def to_api_messages(history_cache, current_user_msg, current_responses, current_tool_results_list):
    messages = []
    if history_cache["summary"]:
        messages.append({"role": "user", "content": [{"type": "text", "text": f"[Контекст из предыдущих сообщений]\n{history_cache['summary']}"}]})
    for batch in history_cache["batches"]:
        messages.extend(batch)
    messages.extend(history_cache["raw"])
    messages.append({"role": "user", "content": [{"type": "text", "text": current_user_msg}]})
    for i, response in enumerate(current_responses):
        text_blocks = [block.text for block in response.content if block.type == "text"]
        if text_blocks:
            messages.append({"role": "assistant", "content": [{"type": "text", "text": "\n".join(text_blocks)}]})
        if i < len(current_tool_results_list):
            messages.append({"role": "user", "content": current_tool_results_list[i]})
    return messages

def update_history_cache(history_cache, user_msg, responses, tool_results_list):
    new_messages = extract_messages_from_history(user_msg, responses, tool_results_list)
    raw_size = sum(len(str(msg)) for msg in history_cache["raw"]) + sum(len(str(msg)) for msg in new_messages)
    if raw_size > RAW_THRESHOLD:
        all_messages = []
        if history_cache["summary"]:
            all_messages.append({"role": "user", "content": [{"type": "text", "text": f"[Контекст из предыдущих сообщений]\n{history_cache['summary']}"}]})
        for batch in history_cache["batches"]:
            all_messages.extend(batch)
        all_messages.extend(history_cache["raw"])
        all_messages.extend(new_messages)
        history_cache["summary"] = summarize_context(all_messages)
        history_cache["batches"] = [new_messages]
        history_cache["raw"] = []
    else:
        history_cache["raw"].extend(new_messages)
        if len(history_cache["batches"]) < 2:
            history_cache["batches"].append(history_cache["raw"].copy())
            history_cache["raw"] = []
        elif len(history_cache["batches"]) == 2:
            all_messages = []
            if history_cache["summary"]:
                all_messages.append({"role": "user", "content": [{"type": "text", "text": f"[Контекст из предыдущих сообщений]\n{history_cache['summary']}"}]})
            for batch in history_cache["batches"]:
                all_messages.extend(batch)
            all_messages.extend(history_cache["raw"])
            history_cache["summary"] = summarize_context(all_messages)
            history_cache["batches"] = [history_cache["raw"].copy()]
            history_cache["raw"] = []
    return history_cache

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

def chat(message, history, history_cache_state):
    logger.info(f"💬 {message}...")
    history = history + [[message, ""]]
    if history_cache_state is None:
        history_cache_state = {"summary": "", "batches": [], "raw": []}
    responses = []
    tool_results_list = []
    while True:
        api_messages = to_api_messages(history_cache_state, message, responses, tool_results_list)
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
    history_cache_state = update_history_cache(history_cache_state, message, responses, tool_results_list)
    return history + [[message, accumulated_text]], history_cache_state, ""


with gr.Blocks(title="RAG Assistant") as demo:
    gr.Markdown("# 🤖 RAG Assistant\n**Claude** с инструментами для навигации по коду")
    history_cache_state = gr.State({"summary": "", "batches": [], "raw": []})

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

    msg.submit(chat, inputs=[msg, chatbot, history_cache_state], outputs=[chatbot, history_cache_state, msg])
    submit.click(chat, inputs=[msg, chatbot, history_cache_state], outputs=[chatbot, history_cache_state, msg])
    clear.click(lambda: ([], {"summary": "", "batches": [], "raw": []}, ""), outputs=[chatbot, history_cache_state, msg])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
