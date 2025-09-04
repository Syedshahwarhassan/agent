#!/usr/bin/env python3
"""
termux_assistant_voice.py
Fully voice-controlled Termux assistant with:
 - ASCII blinking eyes animation
 - JSON memory (memory.json)
 - Voice input & wake word activation
 - Voice output (termux-tts-speak or pyttsx3)
 - Text commands processed via voice
"""

import os
import sys
import json
import time
import threading
import random
import shutil
import subprocess
from datetime import datetime
try:
    import speech_recognition as sr
    HAS_SPEECH = True
except ImportError:
    HAS_SPEECH = False

# ---------------------
# Config & paths
# ---------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_PATH = os.path.join(BASE_DIR, "memory.json")
EYES_REFRESH = 0.12  # seconds between animation frames
SCREEN_CLEAR = "\x1b[2J\x1b[H"
WAKE_WORD = "jarvis"  # Wake word for the assistant

# ---------------------
# JSON memory
# ---------------------
def load_memory():
    if not os.path.exists(MEMORY_PATH):
        return {}
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_memory(mem):
    tmp = MEMORY_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(mem, f, ensure_ascii=False, indent=2)
    os.replace(tmp, MEMORY_PATH)

memory = load_memory()

# ---------------------
# TTS
# ---------------------
def has_termux_tts():
    return shutil.which("termux-tts-speak") is not None

TTS_ENGINE = None
def speak(text):
    text = str(text)
    if has_termux_tts():
        subprocess.run(["termux-tts-speak", text])
    else:
        global TTS_ENGINE
        try:
            if TTS_ENGINE is None:
                import pyttsx3
                TTS_ENGINE = pyttsx3.init()
            TTS_ENGINE.say(text)
            TTS_ENGINE.runAndWait()
        except Exception:
            print("(no TTS available) ->", text)

# ---------------------
# Voice input
# ---------------------
def listen_for_voice(timeout=5, phrase_time_limit=10):
    if not HAS_SPEECH:
        return None, "Speech recognition not available. Install 'SpeechRecognition' package."
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            speak("Listening...")
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            try:
                text = r.recognize_google(audio)
                return text, None
            except sr.UnknownValueError:
                return None, "Could not understand the audio."
            except sr.RequestError as e:
                return None, f"Speech recognition error: {e}"
    except Exception as e:
        return None, f"Microphone error: {e}. Ensure Termux has microphone permission."

# ---------------------
# ASCII blinking eyes
# ---------------------
EYE_OPEN = [
    r"   _____       _____   ",
    r"  /     \_____/     \  ",
    r" /                   \ ",
    r"|   O           O     |",
    r" \                   / ",
    r"  \_____     _____/   ",
    r"        \___/         ",
]
EYE_HALF = [
    r"   _____       _____   ",
    r"  /     \_____/     \  ",
    r" /                   \ ",
    r"|   -           -     |",
    r" \                   / ",
    r"  \_____     _____/   ",
    r"        \___/         ",
]
EYE_CLOSED = [
    r"   _____       _____   ",
    r"  /     \_____/     \  ",
    r" /                   \ ",
    r"|   -------------     |",
    r" \                   / ",
    r"  \_____     _____/   ",
    r"        \___/         ",
]
FACE_PADDING = " " * 6

class EyeAnimator:
    def __init__(self):
        self._stop = threading.Event()
        self._blink = threading.Event()
        self._auto = threading.Event()
        self._auto.set()
        self._state = 1.0
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=1)

    def trigger_blink(self):
        self._blink.set()

    def set_auto(self, enabled: bool):
        if enabled:
            self._auto.set()
        else:
            self._auto.clear()

    def _draw(self, level):
        if level >= 0.66:
            art = EYE_OPEN
        elif level >= 0.33:
            art = EYE_HALF
        else:
            art = EYE_CLOSED
        lines = []
        for l in art:
            lines.append(FACE_PADDING + l + "   " + l)
        return "\n".join(lines)

    def _run(self):
        last_auto_blink = time.time() + random.uniform(0.5, 2.5)
        while not self._stop.is_set():
            now = time.time()
            if self._auto.is_set() and now >= last_auto_blink:
                self._do_blink()
                last_auto_blink = now + random.uniform(2.0, 5.5)
            if self._blink.is_set():
                self._blink.clear()
                self._do_blink()
            with self._lock:
                art = self._draw(self._state)
                sys.stdout.write(SCREEN_CLEAR)
                sys.stdout.write(art + "\n\n")
                sys.stdout.flush()
            time.sleep(EYES_REFRESH)

    def _do_blink(self):
        steps = [0.8, 0.5, 0.2, 0.0]
        for s in steps:
            with self._lock:
                self._state = s
            time.sleep(0.04)
        time.sleep(0.08 + random.uniform(0.0, 0.12))
        for s in reversed(steps):
            with self._lock:
                self._state = s
            time.sleep(0.04)
        with self._lock:
            self._state = 1.0

animator = EyeAnimator()

# ---------------------
# Commands
# ---------------------
JOKES = [
    "Why did the computer show up at work late? It had a hard drive.",
    "Why do programmers prefer dark mode? Because light attracts bugs!",
    "I would tell you a UDP joke, but you might not get it.",
]

def cmd_help():
    lines = [
        "Available commands:",
        "  help                      - show this help",
        "  say <text>                - speak text (TTS)",
        "  remember <key> = <value>  - store a value in memory",
        "  recall <key>              - get value from memory",
        "  list                      - list all memory keys",
        "  forget <key>              - remove key from memory",
        "  time                      - show current time",
        "  joke                      - tell a random joke",
        "  blink                     - force a blink",
        "  blink_auto on|off         - enable/disable auto blinking",
        "  clear                     - clear the assistant screen",
        "  wakeword                  - start wake-word voice control",
        "  exit / quit               - exit the assistant",
    ]
    return "\n".join(lines)

def cmd_remember(arg: str):
    if "=" not in arg:
        return "Use: remember key = value"
    key, val = arg.split("=", 1)
    key = key.strip()
    val = val.strip()
    memory[key] = val
    save_memory(memory)
    return f"Okay, remembered {key} = {val!r}"

def cmd_recall(arg: str):
    key = arg.strip()
    if not key:
        return "Use: recall key"
    if key in memory:
        return f"{key} = {memory[key]!r}"
    return f"I don't have {key!r} in memory."

def cmd_list(_):
    if not memory:
        return "Memory is empty."
    return "\n".join(f"{k} = {v!r}" for k, v in memory.items())

def cmd_forget(arg: str):
    key = arg.strip()
    if not key:
        return "Use: forget key"
    if key in memory:
        val = memory.pop(key)
        save_memory(memory)
        return f"Forgot {key} (was {val!r})"
    return f"No memory for {key!r}"

def cmd_time(_):
    return datetime.now().strftime("Current time: %Y-%m-%d %H:%M:%S")

def cmd_joke(_):
    res = random.choice(JOKES)
    speak(res)
    return res

def cmd_clear(_):
    with animator._lock:
        sys.stdout.write(SCREEN_CLEAR)
        sys.stdout.flush()
    return None

# ---------------------
# Main command handler
# ---------------------
def handle_command(line: str):
    line = line.strip()
    if not line:
        return ""
    parts = line.split(" ", 1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""
    
    if cmd in ("help", "?"):
        return cmd_help()
    if cmd == "say":
        if not arg:
            return "Use: say <text>"
        speak(arg)
        return "(spoken)"
    if cmd == "remember":
        return cmd_remember(arg)
    if cmd == "recall":
        return cmd_recall(arg)
    if cmd == "list":
        return cmd_list(arg)
    if cmd == "forget":
        return cmd_forget(arg)
    if cmd in ("time", "now"):
        return cmd_time(arg)
    if cmd == "joke":
        return cmd_joke(arg)
    if cmd == "blink":
        animator.trigger_blink()
        return "(blinked)"
    if cmd == "blink_auto":
        a = arg.strip().lower()
        if a in ("on", "1", "true", "yes"):
            animator.set_auto(True)
            return "Auto-blink: ON"
        elif a in ("off", "0", "false", "no"):
            animator.set_auto(False)
            return "Auto-blink: OFF"
        else:
            return "Use: blink_auto on|off"
    if cmd == "clear":
        return cmd_clear(arg)
    if cmd in ("exit", "quit"):
        raise SystemExit
    if cmd == "wakeword":
        threading.Thread(target=wakeword_loop, daemon=True).start()
        return f"Wake-word mode started (listening for '{WAKE_WORD}')"
    if "name" in line.lower():
        return "I'm your Termux assistant. I respond to voice commands. Say 'Jarvis' to wake me up."
    if "hello" in line.lower() or "hi" in line.lower():
        return "Hello! Say 'Jarvis' to start a command."
    return "Sorry, I don't understand that. Type 'help' for commands."

# ---------------------
# Wake-word voice control
# ---------------------
def listen_for_wakeword():
    """Wait until the wake word is detected."""
    while True:
        text, error = listen_for_voice()
        if error:
            continue
        if text and WAKE_WORD in text.lower():
            speak("Yes?")
            return True

def wakeword_loop():
    """Main loop: waits for wake word, then listens for a voice command."""
    try:
        while True:
            if listen_for_wakeword():
                text, error = listen_for_voice()
                if error:
                    print(error)
                    continue
                if text:
                    print(f"Command: {text}")
                    response = handle_command(text)
                    if response:
                        print(response)
    except KeyboardInterrupt:
        speak("Stopping wake-word detection.")

# ---------------------
# Main input loop (optional, for typing)
# ---------------------
def main_loop():
    try:
        while True:
            with animator._lock:
                sys.stdout.write(">>> ")
                sys.stdout.flush()
            try:
                line = sys.stdin.readline()
                if not line:
                    break
            except KeyboardInterrupt:
                print()
                continue
            line = line.rstrip("\n")
            try:
                res = handle_command(line)
            except SystemExit:
                break
            except Exception as e:
                res = f"Error handling command: {e}"
            if res is None:
                continue
            if res != "":
                with animator._lock:
                    print(res)
                    speak(res)
    finally:
        animator.stop()
        print("\nGoodbye — memory saved.")
        save_memory(memory)

# ---------------------
# Entry point
# ---------------------
if __name__ == "__main__":
    print(SCREEN_CLEAR)
    print("Termux Voice Assistant — say 'Jarvis' to start commands. (Ctrl+C to interrupt)")
    speak("Hello! Termux Voice Assistant started. Say 'Jarvis' to give a command.")
    try:
        main_loop()
    except SystemExit:
        pass
