import os
import speech_recognition as sr
import threading
import time

# -------- SETTINGS -------- #
WAKE_WORD = "jarvis"   # Wake word trigger
LISTEN_TIMEOUT = 5     # Timeout for listening
# -------------------------- #

recognizer = sr.Recognizer()
mic = sr.Microphone()

# Speak function using espeak
def speak(text: str):
    print(f"Assistant: {text}")
    os.system(f'espeak "{text}"')

# Listen from microphone
def listen():
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=LISTEN_TIMEOUT, phrase_time_limit=8)
            text = recognizer.recognize_google(audio).lower()
            print(f"You: {text}")
            return text
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            speak("Network error")
            return ""

# Handle voice commands
def handle_command(command: str):
    if "time" in command:
        speak("The time is " + time.strftime("%I:%M %p"))
    elif "date" in command:
        speak("Today's date is " + time.strftime("%A, %d %B %Y"))
    elif "stop" in command or "exit" in command or "quit" in command:
        speak("Goodbye")
        os._exit(0)
    else:
        speak("I heard " + command)

# Wake word loop
def wakeword_loop():
    speak(f"Say {WAKE_WORD} to activate me")
    while True:
        text = listen()
        if WAKE_WORD in text:
            speak("Yes, I'm listening")
            command = listen()
            if command:
                handle_command(command)

# Run assistant
if __name__ == "__main__":
    wakeword_loop()
