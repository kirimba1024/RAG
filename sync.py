from pathlib import Path
import shutil


def main() -> None:
    root = Path.cwd()
    src = root / "repos"
    dst = root / "knowledge"

    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)


if __name__ == "__main__":
    main()


