import os
import tempfile
from pathlib import Path

_tmp_dir = tempfile.mkdtemp()
os.environ["CHROMA_PATH"] = str(Path(_tmp_dir) / "chroma")
os.environ["CRM_INTERNAL_URL"] = "http://crm.invalid"
