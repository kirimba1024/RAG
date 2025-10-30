from pathlib import Path
from pathspec import PathSpec
from utils import setup_logging, to_posix, REPOS_ROOT

logger = setup_logging(Path(__file__).stem)

if not REPOS_ROOT.exists():
    logger.error("❌ repos/ не найдена: %s", REPOS_ROOT)
    raise SystemExit(2)

IGNORE_FILE = Path(".ignore")
if not IGNORE_FILE.exists():
    logger.error("❌ .ignore не найден: %s", IGNORE_FILE)
    raise SystemExit(1)

IGNORE_SPEC = PathSpec.from_lines("gitwildmatch", IGNORE_FILE.read_text(encoding="utf-8").splitlines())

def is_ignored(rel_path: Path) -> bool:
    return IGNORE_SPEC.match_file(to_posix(rel_path))
