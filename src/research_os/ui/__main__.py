"""Launch the local Web product without a CLI product entry point."""

from pathlib import Path

from research_os.ui.app import run_ui


def main() -> None:
    run_ui(Path.cwd())


if __name__ == "__main__":
    main()
