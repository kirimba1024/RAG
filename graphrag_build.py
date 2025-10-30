import subprocess
from pathlib import Path
from utils import REPOS_ROOT, to_posix, setup_logging

logger = setup_logging(Path(__file__).stem)


def graph_rag_reindex() -> None:
    root_path = REPOS_ROOT
    subprocess.run(["graphrag", "init"], cwd=to_posix(root_path), check=False, capture_output=True)
    proc = subprocess.run(["graphrag", "run", "index"], cwd=to_posix(root_path), check=True, capture_output=True, text=True)
    if proc.stdout:
        logger.info(proc.stdout.strip())


if __name__ == "__main__":
    graph_rag_reindex()
