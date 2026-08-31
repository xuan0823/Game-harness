import json
import os
import fcntl if os.name != 'nt' else None

STATE_FILE = "state.json"

DEFAULT_STATE = {
    "year": 1628,
    "title": "崇祯元年",
    "treasury": 5000000,
    "food": 2000000,
    "stability": 60,
    "rebels": 20,
    "jianzhou": 30,
    "history": [] # 记录奏折历史
}

def _lock_file(f):
    if os.name != 'nt':
        fcntl.flock(f, fcntl.LOCK_EX)

def _unlock_file(f):
    if os.name != 'nt':
        fcntl.flock(f, fcntl.LOCK_UN)

def get_state():
    if not os.path.exists(STATE_FILE):
        return DEFAULT_STATE.copy()
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        _lock_file(f)
        try:
            return json.load(f)
        except Exception:
            return DEFAULT_STATE.copy()
        finally:
            _unlock_file(f)

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        _lock_file(f)
        try:
            json.dump(state, f, ensure_ascii=False, indent=2)
        finally:
            _unlock_file(f)
