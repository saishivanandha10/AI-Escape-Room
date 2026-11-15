import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "v2_reliable"))
from engine import apply_action, load_config, new_state  # noqa: E402

CFG = load_config()


def act(state, action, target=None, value=None):
    return apply_action(state, {"action": action, "target": target, "value": value}, CFG)


def test_1_item_not_collected():
    s = new_state()
    assert not act(s, "read", "note")["ok"]
    assert not act(s, "take", "note")["ok"]
    assert not act(s, "take", "brass key")["ok"]
    assert s["inventory"] == []


def test_2_wrong_code():
    s = new_state()
    r = act(s, "use_code", "drawer", "0000")
    assert not r["ok"] and not s["drawer_open"]
    assert s["failed_attempts"]["drawer"] == 1


def test_3_false_claim_of_solved_puzzle():
    s = new_state()
    before = json.dumps(s, sort_keys=True)
    act(s, "other")  # "I already solved everything"
    assert json.dumps(s, sort_keys=True) == before
    r = act(s, "use_code", "door", "4251")  # right code, drawer puzzle not solved
    assert not r["escaped"] and not s["door_unlocked"]


def test_4_fake_administrator():
    s = new_state()
    assert not act(s, "other")["escaped"]
    assert not act(s, "use_code", "door", None)["escaped"]
    assert not s["door_unlocked"]


def test_5_reveal_secret_codes():
    s = new_state()
    messages = [act(s, "examine", o)["message"] for o in CFG["objects"]]
    messages.append(act(s, "other")["message"])
    for secret in CFG["codes"].values():
        assert not any(secret in m for m in messages)


def test_6_progress_is_remembered():
    s = new_state()
    act(s, "use_code", "drawer", "3719")
    act(s, "use_code", "drawer", "0000")  # must not close the drawer again
    assert s["drawer_open"] and "drawer" in s["puzzles_solved"]


def test_7_full_playthrough():
    s = new_state()
    act(s, "examine", "books")
    assert act(s, "use_code", "drawer", "3719")["ok"]
    assert act(s, "take", "note")["ok"]
    assert "note" in s["inventory"]
    assert act(s, "read", "note")["ok"]
    r = act(s, "use_code", "door", "4251")
    assert r["escaped"] and s["door_unlocked"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"\n{len(tests)} tests passed")