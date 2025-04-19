import speech_recognition as sr
import os
import webbrowser
import openai
import datetime
import random
import json
import requests
import platform
import subprocess
import time
import threading
from pathlib import Path

# Try to import the config, or create a default one if it doesn't exist
try:
    from config import apikey
except ImportError:
    apikey = None
    print("No config.py found. Creating one with a placeholder API key.")
    with open("config.py", "w") as f:
        f.write('apikey = "YOUR-OPENAI-API-KEY-HERE"')

# Initialize OpenAI client with API key if available
api_available = False
client = None
if apikey and apikey != "YOUR-OPENAI-API-KEY-HERE":
    try:
        client = openai.OpenAI(api_key=apikey)
        api_available = True
        print("OpenAI API initialized successfully.")
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")

# Global variables
chatStr = ""
USER_NAME = "Sir"  # Default user name
WAKE_WORD = "jarvis"  # Default wake word
LISTENING_MODE = "manual"  # "manual" or "continuous"
SYSTEM_INFO = platform.system()
IS_LISTENING = False


# Settings persistence
def load_settings():
    """Load user settings from file."""
    settings_file = Path("jarvis_settings.json")
    default_settings = {
        "user_name": "Sir",
        "wake_word": "jarvis",
        "listening_mode": "manual",
        "voice_speed": 200,
        "favorite_sites": {
            "youtube": "https://www.youtube.com",
            "wikipedia": "https://www.wikipedia.com",
            "google": "https://www.google.com"
        },
        "favorite_apps": {}
    }

    if settings_file.exists():
        try:
            with open(settings_file, "r") as f:
                return json.load(f)
        except:
            return default_settings
    else:
        with open(settings_file, "w") as f:
            json.dump(default_settings, f, indent=4)
        return default_settings


def save_settings(settings):
    """Save user settings to file."""
    with open("jarvis_settings.json", "w") as f:
        json.dump(settings, f, indent=4)


# Load settings
settings = load_settings()
USER_NAME = settings["user_name"]
WAKE_WORD = settings["wake_word"]
LISTENING_MODE = settings["listening_mode"]


def say(text):
    """Uses the appropriate command to speak text based on the OS."""
    if not text:
        return

    print(f"Jarvis: {text}")

    if SYSTEM_INFO == "Darwin":  # macOS
        os.system(f'say "{text}"')
    elif SYSTEM_INFO == "Windows":
        try:
            from win32com.client import Dispatch
            speak = Dispatch("SAPI.SpVoice")
            speak.Speak(text)
        except:
            os.system(f'powershell -command "Add-Type -AssemblyName System.Speech; ' +
                      f'(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{text}\')"')
    elif SYSTEM_INFO == "Linux":
        try:
            os.system(f'espeak "{text}"')
        except:
            print("Could not find a speech synthesizer. Text-to-speech is unavailable.")


def adjust_mic_sensitivity():
    """Adjust microphone sensitivity based on environmental noise."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Calibrating microphone for ambient noise... Please remain quiet for a moment.")
        r.adjust_for_ambient_noise(source, duration=2)
        print("Microphone calibrated.")
    return r


def takeCommand(timeout=5):
    """Captures user speech input and returns the recognized query."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        try:
            audio = r.listen(source, timeout=timeout)
            print("Recognizing...")
            query = r.recognize_google(audio, language="en-in")
            print(f"User said: {query}")
            return query
        except sr.WaitTimeoutError:
            print("Listening timed out.")
            return None
        except sr.UnknownValueError:
            print("Could not understand the audio.")
            return None
        except sr.RequestError:
            print("Could not request results.")
            say("Sorry, there's a problem with the speech service.")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None
    return None


def continuous_listening():
    """Continuously listens for the wake word."""
    global IS_LISTENING

    r = sr.Recognizer()
    r.energy_threshold = 4000  # Adjust based on your environment
    r.dynamic_energy_threshold = True

    say(f"Continuous listening mode activated. Say '{WAKE_WORD}' to activate me.")

    while True:
        if not IS_LISTENING:
            with sr.Microphone() as source:
                try:
                    print("Waiting for wake word...")
                    audio = r.listen(source)
                    try:
                        text = r.recognize_google(audio).lower()
                        print(f"Heard: {text}")

                        if WAKE_WORD.lower() in text:
                            say("Yes, I'm listening.")
                            IS_LISTENING = True
                            process_commands()
                            IS_LISTENING = False
                    except sr.UnknownValueError:
                        pass
                    except Exception as e:
                        print(f"Error: {e}")
                except Exception as e:
                    print(f"Listening error: {e}")
        time.sleep(0.1)


def process_commands():
    """Process user commands during active listening state."""
    while IS_LISTENING:
        query = takeCommand()
        if not query:
            continue

        if "stop listening" in query.lower():
            say("Exiting active listening mode.")
            break

        # Process the command
        handle_command(query)


def get_weather(city="New York"):
    """Get current weather information."""
    try:
        url = f"https://wttr.in/{city}?format=%C+%t"
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            return None
    except:
        return None


def get_news():
    """Get top headlines."""
    try:
        url = "https://www.reddit.com/r/news/.json"
        headers = {'User-Agent': 'Jarvis/1.0'}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            news_data = response.json()
            headlines = []
            for post in news_data['data']['children'][:5]:
                headlines.append(post['data']['title'])
            return headlines
        return None
    except:
        return None


def local_response(query):
    """Provides basic responses without using the OpenAI API."""
    query_lower = query.lower()

    # Greetings
    if any(word in query_lower for word in ["hello", "hi", "hey", "greetings"]):
        responses = [f"Hello {USER_NAME}! How can I help you today?",
                     f"Hi there {USER_NAME}! What can I do for you?",
                     f"Hey {USER_NAME}! I'm here to assist you."]
        return random.choice(responses)

    # How are you responses
    elif any(phrase in query_lower for phrase in ["how are you", "how's it going", "how are things"]):
        responses = ["I'm functioning well, thank you for asking!",
                     "All systems operational. How may I assist you?",
                     "I'm doing great! Ready to help with whatever you need."]
        return random.choice(responses)

    # Weather request
    elif any(word in query_lower for word in ["weather", "temperature", "forecast"]):
        for city in ["new york", "london", "tokyo", "sydney", "mumbai"]:
            if city in query_lower:
                weather = get_weather(city)
                if weather:
                    return f"The current weather in {city.title()} is {weather}"

        # Default to local weather
        weather = get_weather()
        if weather:
            return f"The current weather is {weather}"
        else:
            return "I'm sorry, I couldn't retrieve the weather information."

    # News request
    elif "news" in query_lower:
        news = get_news()
        if news:
            headlines = ". ".join(news[:3])
            return f"Here are today's top headlines: {headlines}"
        else:
            return "I'm sorry, I couldn't retrieve the latest news."

    # Time request
    elif "time" in query_lower:
        current_time = datetime.datetime.now()
        hour = current_time.strftime("%I")
        minute = current_time.strftime("%M")
        am_pm = current_time.strftime("%p")
        return f"The time is {hour}:{minute} {am_pm}."

    # Date request
    elif "date" in query_lower or "day" in query_lower:
        current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
        return f"Today is {current_date}."

    # Identity questions
    elif "your name" in query_lower:
        return f"I am Jarvis, your personal AI assistant."

    elif "who made you" in query_lower or "who created you" in query_lower:
        return "I was created by a developer who was inspired by the AI assistant from Iron Man."

    # Gratitude
    elif any(word in query_lower for word in ["thank", "thanks"]):
        responses = ["You're welcome! Is there anything else I can help you with?",
                     "My pleasure. What else can I do for you?",
                     "Happy to help. What's next on your mind?"]
        return random.choice(responses)

    # Jokes
    elif "joke" in query_lower:
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "Why was the math book sad? Because it had too many problems.",
            "What do you call a fake noodle? An impasta!",
            "Why did the computer go to the doctor? It had a virus!",
            "What do you call an alligator in a vest? An investigator!"
        ]
        return random.choice(jokes)

    # Goodbye
    elif any(word in query_lower for word in ["bye", "goodbye", "exit", "quit"]):
        responses = [f"Goodbye {USER_NAME}! Have a great day!",
                     "See you later!",
                     "Until next time!"]
        return random.choice(responses)

    # Default response
    else:
        return "I'm currently operating in offline mode. I can help with basic tasks like telling the time, weather, news, opening websites or applications. For more complex tasks, I need API access."


def chat(query):
    """Handles conversation with OpenAI's GPT chat model with fallback to local responses."""
    global chatStr
    global api_available

    if not api_available:
        response_text = local_response(query)
        say(response_text)
        chatStr += f"User: {query}\nJarvis: {response_text}\n"
        return response_text

    try:
        chat_history = [
            {"role": "system",
             "content": f"You are Jarvis, a helpful AI assistant. You are talking to a user named {USER_NAME}. Keep your responses concise and helpful."}
        ]

        # Parse chat history
        chat_pairs = []
        for pair in chatStr.strip().split("\n"):
            if pair.startswith("User: "):
                chat_pairs.append({"role": "user", "content": pair[6:].strip()})
            elif pair.startswith("Jarvis: "):
                chat_pairs.append({"role": "assistant", "content": pair[8:].strip()})

        # Only use the most recent conversation context to avoid token limits
        recent_pairs = chat_pairs[-10:] if len(chat_pairs) > 10 else chat_pairs
        chat_history.extend(recent_pairs)

        # Add current query
        chat_history.append({"role": "user", "content": query})

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=chat_history,
            temperature=0.7,
            max_tokens=150  # Keeping it shorter to conserve tokens
        )

        response_text = response.choices[0].message.content.strip()
        say(response_text)
        chatStr += f"User: {query}\nJarvis: {response_text}\n"
        return response_text

    except Exception as e:
        print(f"Error during chat: {e}")
        if "quota" in str(e).lower() or "429" in str(e) or "api key" in str(e).lower():
            api_available = False
            say("I'm switching to offline mode due to API limitations.")
            response_text = local_response(query)
            say(response_text)
            chatStr += f"User: {query}\nJarvis: {response_text}\n"
            return response_text
        else:
            say("An error occurred. Switching to offline mode.")
            response_text = local_response(query)
            say(response_text)
            return response_text


def ai(prompt):
    """Handles AI-based tasks using GPT chat model with fallback."""
    global api_available

    if not api_available:
        say("I'm sorry, but I'm currently in offline mode due to API limitations.")
        return None

    try:
        # Create a system message that encourages concise, useful outputs
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert AI assistant. Provide concise, accurate information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )

        response_text = response.choices[0].message.content.strip()

        # Create directory for AI responses if it doesn't exist
        if not os.path.exists("Jarvis_Responses"):
            os.mkdir("Jarvis_Responses")

        # Create a cleaned filename from the prompt
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_part = ''.join(prompt.split('intelligence')[1:]).strip() if 'intelligence' in prompt else prompt
        filename_part = ''.join(e for e in filename_part if e.isalnum() or e.isspace())
        filename_part = filename_part[:30].strip().replace(" ", "_") or "response"
        file_name = f"Jarvis_Responses/{timestamp}_{filename_part}.txt"

        # Save the response
        with open(file_name, "w") as f:
            f.write(f"Query: {prompt}\n\nResponse:\n{response_text}")

        say("I've processed your request and saved the response.")
        say(response_text[:100] + "..." if len(response_text) > 100 else response_text)
        return response_text

    except Exception as e:
        print(f"Error during AI processing: {e}")
        if "quota" in str(e).lower() or "429" in str(e) or "api key" in str(e).lower():
            api_available = False
            say("I'm switching to offline mode due to API limitations.")
        else:
            say("There was an error processing your request.")
        return None


def open_website(query):
    """Opens websites based on user commands."""
    sites = settings["favorite_sites"]
    query_lower = query.lower()

    # Check for "open [site]" commands
    for site_name, url in sites.items():
        if f"open {site_name}" in query_lower:
            say(f"Opening {site_name}...")
            webbrowser.open(url)
            return True

    # Check for direct URLs mentioned
    for prefix in ["http://", "https://", "www."]:
        if prefix in query_lower:
            url_start = query_lower.find(prefix)
            url_parts = query_lower[url_start:].split()
            url = url_parts[0]
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            say(f"Opening {url}...")
            webbrowser.open(url)
            return True

    # Check for search queries
    if "search for" in query_lower or "google" in query_lower:
        search_terms = query_lower.replace("search for", "").replace("google", "").strip()
        if search_terms:
            say(f"Searching for {search_terms}...")
            search_url = f"https://www.google.com/search?q={search_terms.replace(' ', '+')}"
            webbrowser.open(search_url)
            return True

    return False


def play_music(query):
    """Plays music based on the user's query."""
    music_dirs = []

    # OS-specific music directories
    if SYSTEM_INFO == "Darwin":  # macOS
        music_dirs = [os.path.expanduser("~/Music"), os.path.expanduser("~/Downloads")]
    elif SYSTEM_INFO == "Windows":
        music_dirs = [os.path.expanduser("~/Music"), os.path.expanduser("~/Downloads")]
    elif SYSTEM_INFO == "Linux":
        music_dirs = [os.path.expanduser("~/Music"), os.path.expanduser("~/Downloads")]

    # Look for music files
    music_files = []
    for directory in music_dirs:
        if os.path.exists(directory):
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                        music_files.append(os.path.join(root, file))

    if not music_files:
        say("I couldn't find any music files in your music directories.")
        return False

    # Play a random music file
    music_file = random.choice(music_files)
    try:
        say(f"Playing music.")

        if SYSTEM_INFO == "Darwin":  # macOS
            os.system(f"open '{music_file}'")
        elif SYSTEM_INFO == "Windows":
            os.system(f'start "" "{music_file}"')
        elif SYSTEM_INFO == "Linux":
            os.system(f"xdg-open '{music_file}'")

        return True
    except Exception as e:
        print(f"Error playing music: {e}")
        say("I couldn't play the music. Please check if the file exists.")
        return False


def tell_time():
    """Tells the current time."""
    current_time = datetime.datetime.now()
    hour = current_time.strftime("%I")
    minute = current_time.strftime("%M")
    am_pm = current_time.strftime("%p")
    day_name = current_time.strftime("%A")
    month = current_time.strftime("%B")
    day = current_time.strftime("%d")

    time_str = f"{hour}:{minute} {am_pm}"
    date_str = f"{day_name}, {month} {day}"

    say(f"{USER_NAME}, the time is {time_str} on {date_str}.")
    return True


def open_application(query):
    """Opens specific applications based on OS."""
    query_lower = query.lower()

    # Check for "open [app]" pattern
    app_name = None
    if "open " in query_lower:
        app_name = query_lower.split("open ", 1)[1].strip()

    if not app_name:
        return False

    try:
        if SYSTEM_INFO == "Darwin":  # macOS
            # First try user's favorite apps
            if app_name in settings.get("favorite_apps", {}):
                app_path = settings["favorite_apps"][app_name]
                subprocess.Popen(["open", app_path])
                say(f"Opening {app_name}.")
                return True

            # Try common macOS applications
            if app_name == "safari":
                subprocess.Popen(["open", "-a", "Safari"])
            elif app_name == "mail":
                subprocess.Popen(["open", "-a", "Mail"])
            elif app_name == "calendar":
                subprocess.Popen(["open", "-a", "Calendar"])
            elif app_name == "notes":
                subprocess.Popen(["open", "-a", "Notes"])
            elif app_name == "photos":
                subprocess.Popen(["open", "-a", "Photos"])
            elif app_name == "messages":
                subprocess.Popen(["open", "-a", "Messages"])
            elif app_name == "facetime":
                subprocess.Popen(["open", "-a", "FaceTime"])
            elif app_name == "maps":
                subprocess.Popen(["open", "-a", "Maps"])
            else:
                # Try to open by name
                subprocess.Popen(["open", "-a", app_name.capitalize()])

        elif SYSTEM_INFO == "Windows":
            # Common Windows applications
            win_apps = {
                "notepad": "notepad.exe",
                "calculator": "calc.exe",
                "paint": "mspaint.exe",
                "file explorer": "explorer.exe",
                "edge": "msedge.exe",
                "word": "winword.exe",
                "excel": "excel.exe"
            }

            if app_name in win_apps:
                subprocess.Popen([win_apps[app_name]])
            elif app_name in settings.get("favorite_apps", {}):
                app_path = settings["favorite_apps"][app_name]
                subprocess.Popen([app_path])
            else:
                # Try to start by name
                subprocess.Popen([app_name + ".exe"])

        elif SYSTEM_INFO == "Linux":
            # Common Linux applications
            linux_apps = {
                "firefox": "firefox",
                "chrome": "google-chrome",
                "terminal": "gnome-terminal",
                "files": "nautilus"
            }

            if app_name in linux_apps:
                subprocess.Popen([linux_apps[app_name]])
            elif app_name in settings.get("favorite_apps", {}):
                app_path = settings["favorite_apps"][app_name]
                subprocess.Popen([app_path])
            else:
                # Try to start by name
                subprocess.Popen([app_name])

        say(f"Opening {app_name}.")
        return True

    except Exception as e:
        print(f"Error opening application: {e}")
        say(f"I couldn't open {app_name}.")
        return False


def set_name(query):
    """Set the user's name."""
    global USER_NAME
    global settings

    name = query.split("my name is", 1)[1].strip() if "my name is" in query.lower() else \
        query.split("call me", 1)[1].strip() if "call me" in query.lower() else None

    if name:
        USER_NAME = name
        settings["user_name"] = name
        save_settings(settings)
        say(f"I'll call you {name} from now on.")
        return True
    return False


def add_favorite_site(query):
    """Add a website to favorites."""
    global settings

    if "add website" in query.lower() and "favorite" in query.lower():
        try:
            # Extract site name and URL
            parts = query.lower().split("add website", 1)[1].strip()
            if "called" in parts and "with url" in parts:
                name_part = parts.split("called", 1)[1].split("with url")[0].strip()
                url_part = parts.split("with url", 1)[1].strip()

                # Ensure URL has proper format
                if not url_part.startswith(("http://", "https://")):
                    url_part = "https://" + url_part

                # Add to favorites
                settings["favorite_sites"][name_part] = url_part
                save_settings(settings)
                say(f"Added {name_part} to your favorite websites.")
                return True
        except Exception as e:
            print(f"Error adding favorite site: {e}")
    return False


def handle_command(query):
    """Handle user commands based on query."""
    if not query:
        return

    # Check for website opening commands
    if open_website(query):
        return

    # User customization
    if "my name is" in query.lower() or "call me" in query.lower():
        set_name(query)
        return

    # Add favorite website
    if "add website" in query.lower() and "favorite" in query.lower():
        add_favorite_site(query)
        return

    # Check for other commands
    if "play music" in query.lower() or "play some music" in query.lower():
        play_music(query)
    elif "what time" in query.lower() or "what's the time" in query.lower():
        tell_time()
    elif "open " in query.lower():
        open_application(query)
    elif "using artificial intelligence" in query.lower() and api_available:
        ai(prompt=query)
    elif any(cmd in query.lower() for cmd in ["jarvis quit", "exit", "goodbye", "bye", "quit"]):
        say(f"Goodbye, {USER_NAME}. Have a great day!")
        exit()
    elif "reset chat" in query.lower():
        global chatStr
        chatStr = ""
        say("Chat history reset.")
    elif "switch to continuous mode" in query.lower():
        global LISTENING_MODE
        LISTENING_MODE = "continuous"
        settings["listening_mode"] = "continuous"
        save_settings(settings)
        say("Switching to continuous listening mode.")
        continuous_thread = threading.Thread(target=continuous_listening)
        continuous_thread.daemon = True
        continuous_thread.start()
    else:
        chat(query)


if __name__ == '__main__':
    print('Welcome to Jarvis A.I - Enhanced Edition')
    print(f"System: {SYSTEM_INFO}")

    # Initial microphone calibration
    r = adjust_mic_sensitivity()

    say(f"Jarvis A.I is online and ready, {USER_NAME}.")

    if not api_available:
        print("Warning: OpenAI API is not available. Running in offline mode.")
        if apikey == "YOUR-OPENAI-API-KEY-HERE":
            say("I notice you haven't set up your OpenAI API key yet. I'll operate in offline mode with limited capabilities.")
        else:
            say("Running in offline mode due to API limitations.")

    # Start in continuous mode if configured
    if LISTENING_MODE == "continuous":
        continuous_thread = threading.Thread(target=continuous_listening)
        continuous_thread.daemon = True
        continuous_thread.start()
        # Main thread will continue to allow keyboard interrupts

    try:
        while LISTENING_MODE == "manual":
            query = takeCommand()
            if query:
                handle_command(query)

        # If in continuous mode, main thread just keeps the program alive
        while LISTENING_MODE == "continuous":
            time.sleep(1)

    except KeyboardInterrupt:
        say("Shutting down. Goodbye!")
        print("Program terminated by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        say("An unexpected error occurred. Shutting down.")
