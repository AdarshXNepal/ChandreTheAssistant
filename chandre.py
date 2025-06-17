import json
import speech_recognition as sr
import datetime
import google.generativeai as genai
import os 
from dotenv import load_dotenv
import webbrowser
import urllib.parse
import pywhatkit
import openmeteo_requests
import requests_cache
from retry_requests import retry
from openmeteo_requests import Client
from gtts import gTTS
import random
import psutil
import shutil
import requests
import time

# Load environment variables from .env file
load_dotenv()

# AI Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Weather response config (open meteo)
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# Global speech recognizer
recognizer = sr.Recognizer()

def cleanup_audio_resources():
    """Clean up audio resources"""
    try:
        if os.path.exists("voice.mp3"):
            os.remove("voice.mp3")
        os.system("pkill -f afplay")  # Kill macOS audio player
        time.sleep(0.2)
        print("Audio resources cleaned up")
    except Exception as e:
        print(f"Audio cleanup error: {e}")

def speak(text):
    """Text to speech function"""
    try:
        tts = gTTS(text=text, lang='en')
        tts.save("voice.mp3")
        os.system("afplay voice.mp3")  # macOS audio player
    except Exception as e:
        print(f"TTS Error: {e}")

def listen():
    """Speech to text function"""
    global recognizer
    
    try:
        with sr.Microphone() as source:
            print("Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=3, phrase_time_limit=5)
        
        command = recognizer.recognize_google(audio)
        print(f"You said: {command}")
        return command.lower()
    except sr.WaitTimeoutError:
        print("Listening timeout")
        return ""
    except sr.UnknownValueError:
        speak("I'm sorry, I couldn't quite catch that. Could you please repeat?")
        return ""
    except Exception as e:
        print(f"Listen error: {e}")
        return ""

# Configure Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash') 
     
def ai_chat(question):
    """AI chat function"""
    if not question:
        speak("I didn't catch your question. What would you like to know?")
        return

    try:
        speak("Let me think about that for you...")
        prompt = (
            f"You are a friendly and helpful voice assistant. "
            f"Respond in a natural, spoken tone that sounds human. "
            f"Keep your answer short and clear. Don't include phrases like 'here is your answer' or 'as an AI'. "
            f"Just talk like you're directly replying to the user.\n\n"
            f"User asked: {question}"
        )

        response = model.generate_content(prompt)
        answer = response.text.strip()
        print(f"AI Response: {answer}")
        speak(answer)

    except Exception as e:
        speak("I'm having trouble finding that information right now. Please try again in a moment.")
        print("AI Error:", e)

def load_notes():
    """Load notes from file"""
    try:
        with open("notes.json", "r") as f:
            return json.load(f)
    except:
        return {}
    
def save_notes(notes):
    """Save notes to file"""
    with open("notes.json", "w") as f:
        json.dump(notes, f, indent=2)
        
def take_note():
    """Take a note"""
    speak("I'm ready to take a note for you. What should I write down?")
    note = listen()
    if not note:
        speak("I didn't catch that. We can try again whenever you're ready.")
        return
        
    notes = load_notes()
    notes.setdefault("notes", []).append(note)
    save_notes(notes)
    speak("Perfect! I've saved that note for you.")
    
def read_notes():
    """Read saved notes"""
    notes = load_notes()
    note_list = notes.get("notes", [])
    if note_list:
        speak("Here are your saved notes:")
        for note in note_list:
            speak(note)
    else:
        speak("You don't have any notes saved yet.")

def play_music():
    """Play music on YouTube"""
    speak("What song or artist would you like to listen to?")
    song = listen()
    if song:
        try:
            speak(f"Great choice! Let me find {song} for you on YouTube.")
            pywhatkit.playonyt(song)
            speak("Here we go! Enjoy your music.")
        except Exception as e:
            print(f"Error playing song: {e}")
            speak("I'm having trouble finding that song right now. Would you like to try a different one?")
    else:
        speak("I didn't catch the song name. What would you like to hear?")      

def get_weather():
    """Get current weather using Open-Meteo API"""
    try:
        # Default coordinates (you can change these)
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 40.7128,  # New York coordinates (change as needed)
            "longitude": -74.0060,
            "current": ["temperature_2m", "relative_humidity_2m", "weather_code", "wind_speed_10m"]
        }
        
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
        
        current = response.Current()
        temperature = round(current.Variables(0).Value(), 1)
        humidity = round(current.Variables(1).Value(), 1)
        weather_code = current.Variables(2).Value()
        wind_speed = round(current.Variables(3).Value(), 1)
        
        # Weather descriptions
        weather_descriptions = {
            0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
            45: "foggy", 51: "light drizzle", 61: "slight rain", 63: "moderate rain"
        }
        
        weather_desc = weather_descriptions.get(int(weather_code), "unknown conditions")
        
        weather_report = (
            f"Right now we have {weather_desc}. "
            f"The temperature is {temperature} degrees Celsius. "
            f"Humidity is at {humidity} percent, "
            f"and wind speed is {wind_speed} kilometers per hour."
        )
        
        return weather_report
        
    except Exception as e:
        print(f"Weather API Error: {e}")
        return "I'm sorry, I can't get the weather information at the moment."

def open_website():
    """Open a website"""
    speak("Which website would you like me to open for you?")
    site = listen().replace(" ", "").lower()
    if not site:
        speak("I didn't catch the website name. Could you repeat that?")
        return
        
    url = f"https://www.{site}.com"
    speak(f"Opening {site} for you right now!")
    webbrowser.open(url)

def get_time_date():
    """Get current time and date"""
    now = datetime.datetime.now()
    current_time = now.strftime("%I:%M %p")
    current_date = now.strftime("%A, %B %d, %Y")
    
    return current_time, current_date

def get_system_info():
    """Get basic system information"""
    try:
        battery = psutil.sensors_battery()
        if battery:
            battery_percent = battery.percent
            battery_status = "charging" if battery.power_plugged else "not charging"
            battery_info = f"Your battery is at {battery_percent}% and {battery_status}."
        else:
            battery_info = "Battery information is not available."
        
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_info = f"CPU usage is at {cpu_percent}%."
        
        return f"{battery_info} {cpu_info}"
        
    except Exception as e:
        return "I'm having trouble getting system information right now."

def perform_action(command):
    """Perform actions based on commands"""
    
    if "chat" in command or "ask" in command or "question" in command:
        speak("I'm here to help! What would you like to know?")
        question = listen()
        ai_chat(question)
        
    elif "play" in command or "music" in command or "song" in command:
        play_music()
    
    elif "weather" in command:
        speak("Let me check the current weather conditions for you...")
        weather_info = get_weather()
        speak(weather_info)
    
    elif "website" in command:
        open_website()
     
    elif "youtube" in command:
        speak("Taking you to YouTube right now!")
        webbrowser.open("https://www.youtube.com")  
    
    elif "google" in command:
        speak("Opening Google for you!")
        webbrowser.open("https://www.google.com")
    
    elif "time" in command:
        current_time, _ = get_time_date()
        speak(f"The current time is {current_time}")
    
    elif "date" in command:
        _, current_date = get_time_date()
        speak(f"Today is {current_date}")
    
    elif "system" in command or "battery" in command:
        speak("Let me check your system information...")
        system_info = get_system_info()
        speak(system_info)
    
    elif "note" in command:
        take_note()
        
    elif "read notes" in command or "my notes" in command:
        read_notes()
    
    elif "exit" in command or "stop" in command or "goodbye" in command:
        return "exit"
    
    else:
        speak("I'm not sure how to help with that yet. Try asking me to play music, check weather, or take notes!")
    
    return "continue"

def main():
    """Main function"""
    try:
        speak("Hello! I'm your voice assistant. I'm ready to help you today. What can I do for you?")
        
        while True:
            command = listen()
            
            if not command:
                continue
            
            # Simple command processing
            result = perform_action(command)
            if result == "exit":
                speak("It's been a pleasure helping you today! Take care!")
                break
    
    finally:
        cleanup_audio_resources()
        print("Assistant cleanup completed")

if __name__ == "__main__":
    main()
