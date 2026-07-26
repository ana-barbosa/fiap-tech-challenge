"""Video filename parsing shared by pose_extraction.py and gait_risk_score.py.

Kept dependency-free (stdlib only) so gait_risk_score.py doesn't have to import
pose_extraction's heavy ML dependencies (ultralytics, mediapipe) just for this.
"""

import re
from pathlib import Path

VIDEO_NAME_RE = re.compile(r"^(OAW\d+)-(top|bottom)$", re.IGNORECASE)


def parse_video_id(video_path):
    """OAW01-top.mp4 -> ('OAW01', 'top'). Self-recorded clips have no camera suffix."""
    stem = Path(video_path).stem
    match = VIDEO_NAME_RE.match(stem)
    if match:
        return match.group(1).upper(), match.group(2).lower()
    return stem, None
