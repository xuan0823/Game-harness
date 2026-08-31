import json
import os
import fcntl if os.name != 'nt' else None

STATE_FILE = "state.json"

PROVINCES = [
    "北直隶", "南直隶", "山东", "山西", "河南", "陕西",
    "四川", "湖广", "江西", "浙江", "福建", "广东",
    "广西", "云南", "贵州", "辽东"
]

def _init_provinces():
    provinces = {}
    for p in PROVINCES:
        owner = "大明"
        status = "正常"
        if p == "辽东":
            status = "战乱"
            rebel_risk = 80
            stability = 30
        elif p == "陕西":
            status = "饥荒"
            rebel_risk = 70
            stability = 20
        else:
            rebel_risk = 10
            stability = 60

        provinces[p] = {
            "name": p,
            "owner": owner,
            "status": status,
            "stability": stability,
            "food": 100000,
            "tax_revenue": 500000 if p not in ["陕西", "辽东"] else 0,
            "rebel_risk": rebel_risk,
            "troops": [] # 驻扎在该省的军队ID
        }
    return provinces

DEFAULT_STATE = {
    "year": 1628,
    "title": "崇祯元年",
    "treasury": 1000000,
    "neitang": 3000000,
    "provinces": _init_provinces(),
    "armies": {
        "army_1": {"id": "army_1", "name": "关宁铁骑", "location": "辽东", "count": 50000, "morale": 70, "combat_power": 90},
        "army_2": {"id": "army_2", "name": "秦军", "location": "陕西", "count": 30000, "morale": 50, "combat_power": 60},
        "army_3": {"id": "army_3", "name": "京营", "location": "北直隶", "count": 100000, "morale": 40, "combat_power": 40}
    },
    "factions": {
        "东林党": 40,
        "阉党": 20,
        "武将集团": 50,
        "勋贵": 60
    },
    "jianzhou_threat": 60,
    "history": []
}

for army_id, army in DEFAULT_STATE["armies"].items():
    DEFAULT_STATE["provinces"][army["location"]]["troops"].append(army_id)

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
