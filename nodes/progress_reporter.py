"""
RM Progress Reporter - Reports workflow progress to the Playground Viewer app.
"""

import json
import os
import glob
import time

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False

VIEWER_URL = "http://127.0.0.1:3001/api/comfy-progress"
PREVIEW_DIR = r"C:\Users\rober\Playground\Viewer\public\previews"


def ensure_preview_dir():
    """Create preview directory if it doesn't exist."""
    if not os.path.exists(PREVIEW_DIR):
        os.makedirs(PREVIEW_DIR, exist_ok=True)


def send_progress(data: dict) -> bool:
    """Send progress data to the Viewer app."""
    try:
        json_data = json.dumps(data)

        if HAS_REQUESTS:
            response = requests.post(VIEWER_URL, json=data, timeout=2)
            return response.status_code == 200
        else:
            req = urllib.request.Request(
                VIEWER_URL,
                data=json_data.encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=2) as response:
                return response.status == 200
    except Exception:
        # Viewer app may not be running - fail silently
        return False
