import json
from pathlib import Path
from typing import List, Dict, Any
from anthropic import Anthropic

from utils import (
    CLAUDE_MODEL, ANTHROPIC_API_KEY,
    REPOS_SAFE_ROOT, LANG_BY_EXT, setup_logging
)

logger = setup_logging("build_llm")

CLAUDE = Anthropic(api_key=ANTHROPIC_API_KEY)

LLM_VERSION = "v1"

def split_file_into_blocks(text: str, lang: str, rel_path: str) -> List[Dict[str, Any]]:
    system_prompt = f"""Разбей файл на семантические блоки (функции, классы, секции конфига, логические группы кода).

Правила:
- Блоки без перекрытий
- Конец блока - начало следующего или EOF
- Минимум 10 строк на блок
- Возврати JSON массив: [{{"start_line": N, "end_line": M, "title": "краткое название", "kind": "function|class|config|other"}}]
- Язык файла: {lang}
- Путь: {rel_path}
"""

    user_content = f"Разбей файл:\n\n```{lang}\n{text}\n```"

    response = CLAUDE.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        temperature=0,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}]
    )

    content = response.content[0].text
    blocks_raw = content.strip()
    if blocks_raw.startswith("```json"):
        blocks_raw = blocks_raw[7:]
    if blocks_raw.startswith("```"):
        blocks_raw = blocks_raw[3:]
    blocks_raw = blocks_raw.strip().rstrip("`")
    
    blocks = json.loads(blocks_raw)
    logger.info(f"Разбито на {len(blocks)} блоков: {rel_path}")
    return blocks

def describe_block(block_text: str, lang: str, rel_path: str, block_idx: int) -> Dict[str, Any]:
    system_prompt = f"""Извлеки метаданные из блока кода.

Язык: {lang}
Путь: {rel_path}
Блок #{block_idx}

Верни строгий JSON с полями:
- chunk_title: до 80 символов
- chunk_summary: до 600 символов, 1-3 предложения
- tags: массив до 10 элементов [domain, layer, framework]
- entities: массив до 20 нормализованных сущностей (lowercase kebab-case)
- public_symbols: массив до 20 элементов [{{"name": "...", "kind": "function|class|config_key", "signature": "..."}}]
- io: массив до 20 I/O артефактов (таблицы, топики, URLs, файлы)
- security_flags: массив из ["pii","secrets","crypto","authz","audit"] если есть
- likely_queries: массив до 5 коротких вопросов

Важно: только факты из блока, без выдумок.
"""

    user_content = f"Блок:\n\n```{lang}\n{block_text}\n```"

    response = CLAUDE.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        temperature=0,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}]
    )

    content = response.content[0].text.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    content = content.strip().rstrip("`")
    
    meta = json.loads(content)
    return meta

def analyze_file(rel_path: str) -> List[Dict[str, Any]]:
    full_path = REPOS_SAFE_ROOT / rel_path
    if not full_path.exists():
        return []
    
    text = full_path.read_text(encoding='utf-8', errors='ignore')
    ext = full_path.suffix.lower()
    lang = LANG_BY_EXT.get(ext, "text")
    
    blocks = split_file_into_blocks(text, lang, rel_path)
    
    chunks = []
    for i, block_def in enumerate(blocks):
        start = block_def["start_line"]
        end = block_def["end_line"]
        lines = text.split('\n')
        block_text = '\n'.join(lines[start-1:end])
        
        meta = describe_block(block_text, lang, rel_path, i)
        
        chunks.append({
            "start_line": start,
            "end_line": end,
            "kind": block_def.get("kind", "other"),
            "lang": lang,
            "text": block_text,
            **meta
        })
    
    logger.info(f"Проанализировано {len(chunks)} чанков для {rel_path}")
    return chunks

