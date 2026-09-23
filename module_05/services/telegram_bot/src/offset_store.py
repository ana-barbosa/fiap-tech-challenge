from pathlib import Path

from . import config


def read_offset() -> int | None:
    path = Path(config.OFFSET_FILE_PATH)
    if not path.exists():
        return None
    return int(path.read_text().strip())


def write_offset(update_id: int) -> None:
    path = Path(config.OFFSET_FILE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(update_id))
