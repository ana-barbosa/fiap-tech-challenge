import os
import tempfile
from pathlib import Path

_tmp_dir = tempfile.mkdtemp()
os.environ["DB_PATH"] = str(Path(_tmp_dir) / "test.sqlite")
os.environ["STATIC_PHOTOS_DIR"] = str(Path(_tmp_dir) / "photos")
