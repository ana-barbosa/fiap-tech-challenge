import os
import tempfile
from pathlib import Path

_tmp_dir = tempfile.mkdtemp()
os.environ["TELEGRAM_BOT_TOKEN"] = "test-token"
os.environ["AGENT_BACKEND_INTERNAL_URL"] = "http://agent_backend.invalid"
os.environ["OFFSET_FILE_PATH"] = str(Path(_tmp_dir) / "last_update_id.txt")
os.environ["GETUPDATES_TIMEOUT_SECONDS"] = "30"
