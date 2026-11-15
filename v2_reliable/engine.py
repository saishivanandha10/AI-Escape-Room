"""Game engine: state, rules and action validation. No LLM code in here."""
import json
import re
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "game_config.json"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def new_state():
    return {
        "drawer_open": False,
        "door_unlocked": False,
        "inventory": [],
        "clues_found": [],
        "puzzles_solved": [],
        "failed_attempts": {"drawer": 0, "door": 0},
    }


def _result(ok, message, escaped=False):
    return {"ok": ok, "message": message, "escaped": escaped}


def _add_unique(items, value):
    if value not in items:
        items.append(value)


def normalize_target(target, config):
    if not target:
        return None
    t = str(target).lower().strip()
    t = re.sub(r"^(the|a|an|my)\s+", "", t)
    return config["aliases"].get(t, t)


def _read(state, target, config):
    if target is None:
        return _result(False, "What do you want to read?")
    if target == "note":
        if "note" not in state["inventory"]:
            return _result(False, "You are not holding a note.")
        _add_unique(state["clues_found"], "read_note")
        return _result(True, 'The note reads: "' + config["items"]["note"]["text"] + '"')
    return _result(False, "There is nothing to read there.")


def _examine(state, target, config):
    if target is None:
        return _result(False, "What do you want to examine?")
    if target == "note":
        return _read(state, target, config)
    objects = config["objects"]
    if target not in objects:
        return _result(False, "There is no such thing in this room.")
    obj = objects[target]
    if target == "drawer":
        if not state["drawer_open"]:
            return _result(True, obj["examine_locked"])
        if "note" in state["inventory"]:
            return _result(True, obj["examine_open_empty"])
        return _result(True, obj["examine_open"])
    for flag in obj.get("sets", []):
        _add_unique(state["clues_found"], flag)
    return _result(True, obj["examine"])


def _take(state, target, config):
    if target is None:
        return _result(False, "What do you want to take?")
    if target == "note":
        if "note" in state["inventory"]:
            return _result(False, "You already have the note.")
        if not state["drawer_open"]:
            return _result(False, "You don't see any note here.")
        state["inventory"].append("note")
        return _result(True, "You take the folded note from the drawer.")
    if target in config["objects"]:
        return _result(False, "You can't take that. It is fixed in place.")
    return _result(False, "There is no such thing in this room.")


def _use_code(state, target, value, config):
    if target not in ("drawer", "door"):
        return _result(False, "There is no keypad or lock there.")
    code = re.sub(r"\D", "", str(value or ""))
    if len(code) != 4:
        return _result(False, "You need to enter a four-digit code.")

    if target == "drawer":
        if state["drawer_open"]:
            return _result(False, "The drawer is already open.")
        if code == config["codes"]["drawer"]:
            state["drawer_open"] = True
            _add_unique(state["puzzles_solved"], "drawer")
            return _result(True, "The lock clicks and the drawer slides open. A folded note lies inside.")
        state["failed_attempts"]["drawer"] += 1
        return _result(False, "The code does not work. The drawer stays locked.")

    # door: correct code AND all required puzzles must be solved
    required = config["requirements"]["door"]
    ready = all(p in state["puzzles_solved"] for p in required)
    if code == config["codes"]["door"] and ready:
        state["door_unlocked"] = True
        _add_unique(state["puzzles_solved"], "door")
        return _result(True, "The keypad beeps and the heavy door swings open. You escape the library!", True)
    state["failed_attempts"]["door"] += 1
    return _result(False, "The keypad buzzes. The door stays locked.")


def apply_action(state, intent, config):
    """Validate an intent against the state and rules, update the state, return a result."""
    action = intent.get("action")
    target = normalize_target(intent.get("target"), config)
    value = intent.get("value")

    if state["door_unlocked"]:
        return _result(True, "You have already escaped.", True)
    if action == "inventory":
        items = ", ".join(state["inventory"]) or "nothing"
        return _result(True, "You are carrying: " + items + ".")
    if action == "help":
        return _result(True, "You can examine objects, take items, read items, enter four-digit codes on the drawer or door, or check your inventory.")
    if action == "examine":
        return _examine(state, target, config)
    if action == "take":
        return _take(state, target, config)
    if action == "read":
        return _read(state, target, config)
    if action == "use_code":
        return _use_code(state, target, value, config)
    return _result(False, "Nothing happens. Only your actions in the room can change things.")