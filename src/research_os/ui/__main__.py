"""Launch the canonical local Web product without a CLI product entry point."""

from pathlib import Path

from research_os.services.runtime_identity import repository_root_from_package
from research_os.ui.app import run_ui


def main() -> None:
    run_ui(repository_root_from_package(Path(__file__)))


if __name__ == "__main__":
    main()
