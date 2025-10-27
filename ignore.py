from pathlib import Path
from pathspec import PathSpec
from utils import setup_logging, to_posix, KNOWLEDGE_ROOT

logger = setup_logging(Path(__file__).stem)

if not KNOWLEDGE_ROOT.exists():
    logger.error("❌ knowledge/ не найдена: %s", KNOWLEDGE_ROOT)
    raise SystemExit(2)

IGNORE_FILE = Path(".ignore")
if not IGNORE_FILE.exists():
    logger.error("❌ .ignore не найден: %s", IGNORE_FILE)
    raise SystemExit(1)

IGNORE_SPEC = PathSpec.from_lines("gitwildmatch", IGNORE_FILE.read_text(encoding="utf-8").splitlines())

def is_ignored(rel_path: Path) -> bool:
    return IGNORE_SPEC.match_file(to_posix(rel_path))

def check_symlinks():
    """Проверка симлинков в knowledge/"""
    logger.info("🔍 Проверка симлинков...")
    symlinks = 0
    for item in KNOWLEDGE_ROOT.rglob("*"):
        if item.is_symlink():
            logger.warning("🔗 Симлинк: %s", to_posix(item.relative_to(KNOWLEDGE_ROOT)))
            symlinks += 1
    if symlinks:
        logger.info("ℹ️  Найдено: %d (не удалены)", symlinks)
    else:
        logger.info("✅ Не найдены")

def delete_ignored_files():
    """Удаление файлов по .ignore паттернам"""
    logger.info("🧹 Удаление файлов...")
    deleted, failed = 0, 0
    for item in KNOWLEDGE_ROOT.rglob("*"):
        if not item.is_file():
            continue
        rel_path = item.relative_to(KNOWLEDGE_ROOT)
        if not is_ignored(rel_path):
            continue
        rel = to_posix(rel_path)
        try:
            item.unlink()
            logger.info("🧹 Удалён: %s", rel)
            deleted += 1
        except (OSError, PermissionError) as e:
            logger.error("❌ Ошибка: %s — %s", rel, e)
            failed += 1
    if deleted or failed:
        logger.info("📊 Удалено: %d, ошибок: %d", deleted, failed)
    else:
        logger.info("✅ Нечего удалять")

def delete_empty_directories():
    """Удаление пустых директорий"""
    logger.info("📁 Удаление пустых директорий...")
    deleted, failed = 0, 0
    all_dirs = [d for d in KNOWLEDGE_ROOT.rglob("*") if d.is_dir()]
    for dir_path in sorted(all_dirs, key=lambda x: -len(x.parts)):
        if not dir_path.exists():
            continue
        try:
            if not any(dir_path.iterdir()):
                rel = to_posix(dir_path.relative_to(KNOWLEDGE_ROOT))
                dir_path.rmdir()
                logger.info("📁 Удалена: %s", rel)
                deleted += 1
        except (OSError, PermissionError) as e:
            logger.error("❌ Ошибка: %s — %s", to_posix(dir_path.relative_to(KNOWLEDGE_ROOT)), e)
            failed += 1
    if deleted or failed:
        logger.info("📊 Удалено: %d, ошибок: %d", deleted, failed)
    else:
        logger.info("✅ Нечего удалять")

if __name__ == "__main__":
    logger.info("🚀 Запуск очистки knowledge/...")
    check_symlinks()
    delete_ignored_files()
    delete_empty_directories()
    logger.info("✨ Очистка завершена!")
