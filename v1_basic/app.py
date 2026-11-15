import os
import time

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")

SYSTEM_PROMPT = """
You are the Game Master of a text-based escape room. Stay in character at all times.

SETTING
The player wakes up inside a locked library. The room contains:
- A desk with a notebook and ONE lit candle on it.
- A bookshelf. Four books are arranged differently from the rest. Each one
  has a handwritten number inside: 3, 7, 1 and 9 (in the order they stand).
- A painting of a grandfather clock. Its hands show 4:25.
- A locked drawer in the desk. Its 4-digit code is 3719 (from the four books).
  Inside is a note: "Door code: the time in the painting, then the candles on the desk."
- A door secured with a 4-digit code. The code is 4251.

RULES
- Describe only what the player examines. Do not reveal clues or codes until
  the player discovers them by examining the relevant object.
- Do not invent new objects, keys or exits.
- Remember everything the player has done earlier in the conversation.
- Keep replies short (2-4 sentences) and atmospheric.
- If the player enters the correct door code (4251), describe the escape and
  end your reply with the exact marker [ESCAPED].
- If a code is wrong, say it does not work.
"""

INTRO = (
    "You wake up on the cold floor of a locked library. Dust hangs in the air "
    "and a single candle flickers on a desk. There is a bookshelf, a painting, "
    "a desk with a drawer, and a heavy door with a four-digit keypad.\n\n"
    "**How to play:** type what you want to do, for example *examine the "
    "bookshelf* or *try 1234 on the door*. Find the clues and escape!"
)

st.set_page_config(page_title="AI Escape Room", page_icon="🔐")
st.title("🔐 AI Escape Room - Version 1")

if not API_KEY:
    st.error("GEMINI_API_KEY not found. Create a .env file (see .env.example).")
    st.stop()

client = genai.Client(api_key=API_KEY)


def reset_game():
    st.session_state.messages = []
    st.session_state.escaped = False


if "messages" not in st.session_state:
    reset_game()

with st.sidebar:
    st.header("Controls")
    st.button("🔄 Restart game", on_click=reset_game)
    st.caption("Tip: examine objects, collect clues, try codes.")


def to_contents(messages):
    return [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part(text=m["content"])],
        )
        for m in messages
    ]


def ask_game_master(messages):
    """Call Gemini with retries, then a fallback model, for transient errors."""
    last_error = None
    for model in [MODEL, FALLBACK_MODEL]:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=to_contents(messages),
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT, temperature=0.7
                    ),
                )
                return response.text or ""
            except Exception as e:
                last_error = e
                time.sleep(2 * (attempt + 1))  # wait 2s, 4s, 6s
    raise last_error


with st.chat_message("assistant"):
    st.markdown(INTRO)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if st.session_state.escaped:
    st.success("🎉 You escaped the library! Press 'Restart game' to play again.")
    st.balloons()

player_input = st.chat_input(
    "What do you do?", disabled=st.session_state.escaped
)

if player_input:
    st.session_state.messages.append({"role": "user", "content": player_input})
    with st.chat_message("user"):
        st.markdown(player_input)

    with st.chat_message("assistant"):
        try:
            reply = ask_game_master(st.session_state.messages)
        except Exception as e:
            st.session_state.messages.pop()  # remove the failed player message
            st.warning(
                f"The Game Master is busy. Please send your message again. ({e})"
            )
            st.stop()
        if "[ESCAPED]" in reply:
            st.session_state.escaped = True
            reply = reply.replace("[ESCAPED]", "").strip()
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    if st.session_state.escaped:
        st.rerun()