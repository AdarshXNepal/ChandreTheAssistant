import json
import pyttsx3
import speech_recognition as sr
import datetime
import face_recognition
import cv2
import google.generativeai as genai
import os 
from dotenv import load_dotenv
import webbrowser
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
import re
import time
import threading

# Load environment variables from .env file
load_dotenv()

#ai
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

#whatsapp
BABA=os.getenv("BABA")
MOM=os.getenv("MOM")
SISTER=os.getenv("SISTER")

#NEWS
NEWS_API_KEY=os.getenv("NEWS_API_KEY")


#email
EMAIL_APP_PASSWORD = os.getenv('EMAIL_APP_PASSWORD')
SENDER_EMAIL_ADDRESS=os.getenv("SENDER_EMAIL_ADDRESS")
RECEIVER_EMAIL_ADDRESS=os.getenv("RECEIVER_EMAIL_ADDRESS")

# Global audio cleanup flag
audio_cleanup_needed = False

#weather response config (open metro)
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)


# Global speech recognizer to reuse
recognizer = sr.Recognizer()

def cleanup_audio_resources():
    """Clean up all audio resources"""
    global audio_cleanup_needed
    try:
        # Remove any temporary audio files
        if os.path.exists("voice.mp3"):
            os.remove("voice.mp3")
        
        # Force stop any audio processes
        os.system("pkill -f afplay")  # Kill macOS audio player
        
        # Small delay to ensure cleanup
        time.sleep(0.2)
        
        audio_cleanup_needed = False
        print("Audio resources cleaned up")
    except Exception as e:
        print(f"Audio cleanup error: {e}")

def speak(text):
    """Improved speak function with cleanup"""
    global audio_cleanup_needed
    try:
        tts = gTTS(text=text, lang='en')
        tts.save("voice.mp3")
        os.system("afplay voice.mp3")  # macOS audio player
        audio_cleanup_needed = True
    except Exception as e:
        print(f"TTS Error: {e}")

def listen():
    """Improved listen function with timeout and cleanup"""
    global recognizer, audio_cleanup_needed
    
    try:
        with sr.Microphone() as source:
            print("Listening...")
            # Reduce timeout to prevent hanging
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

def recognize_face():
    cap = None
    try:
        known_image = face_recognition.load_image_file("photo.jpg")
        known_encoding = face_recognition.face_encodings(known_image)[0]
    except:
        speak("I'm having trouble accessing your photo. Please check the file.")
        return False

    try:
        cap = cv2.VideoCapture(0)
        speak("Please look at the camera while I verify your identity...")
        
        start_time = time.time()
        timeout = 10  # 10 second timeout
        
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Timeout check
            if time.time() - start_time > timeout:
                speak("Verification timeout. Please try again.")
                break
            
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            faces = face_recognition.face_encodings(rgb)
            
            for face in faces:
                match = face_recognition.compare_faces([known_encoding], face)
                if match[0]:
                    return True
                
            cv2.imshow("Camera", frame)
            if cv2.waitKey(1) == ord('q'):
                break
        
        return False
        
    except Exception as e:
        print(f"Face recognition error: {e}")
        return False
    finally:
        if cap:
            cap.release()
        cv2.destroyAllWindows()
        time.sleep(0.5)  # Give time for camera to release

def send_whatsapp():
    speak("Sure thing! Who would you like to send a message to?")
    
    Baba=BABA
    Mom=MOM
    Sister=SISTER
    
    response=listen()
    
    if "Baba" in response:
        phone_number=Baba
        speak("Got it! Preparing to send a message to Baba.")
    elif "Mom" in response:
        phone_number=Mom
        speak("Perfect! Setting up a message for Mom.")
    elif "Sister" in response:
        phone_number=Sister
        speak("Alright! Getting ready to message your sister.")
    else:
        speak("I couldn't find that contact in your list. Please try again with Baba, Mom, or Sister.")
        return
    
    speak("What message would you like to send?")
    
    message=listen()
    if not message:
        speak("I didn't catch the message. Let's try again later.")
        return
        
    encoded_message = urllib.parse.quote(message)
    url = f"https://web.whatsapp.com/send?phone={phone_number}&text={encoded_message}"
    webbrowser.open(url)
    speak("WhatsApp is now open with your message ready! Just hit Enter to send it off.")

def send_email():
    #email confirugation
    sender = SENDER_EMAIL_ADDRESS
    app_password = EMAIL_APP_PASSWORD  # mail App Password 
    receiver = RECEIVER_EMAIL_ADDRESS
    
    speak("I'd be happy to help you send an email! What should the subject line be?")
    subject=listen()
    if not subject:
        subject="Voice assistant Email"
        speak("No worries, I'll use a default subject for you.")
        
    speak("Now, what would you like to say in your email?")
    body=listen()
    if not body:
        speak("I didn't catch your message. Let's try sending an email later.")
        return
        
    speak("Let me craft a professional email for you. Just a moment...")
    prompt = f"This is a overlook of content in mail {body}: rephrase and make it nice and cooperative and give response your output will be direclty sent so dont include any starting text like here is your... give direct response give a proper mail dont keep [topic 1] give yourself"
    response = model.generate_content(prompt)
    mailbody = response.text.strip()
    print(mailbody)
    
    try:
        #create message
        msg=MIMEMultipart()
        msg['From']=sender
        msg['To']=receiver
        msg['Subject']=subject
        
        #Add body to email
        msg.attach(MIMEText(mailbody,'plain'))
        
        #Gmail SMTP confirugation
        server=smtplib.SMTP("smtp.gmail.com",587)
        server.starttls() #check encrytion
        server.login(sender,app_password)
        
        #convert message to string and send
        text=msg.as_string()
        server.sendmail(sender,receiver,text)
        server.quit()
        
        speak(f"Excellent! Your email has been sent successfully. The recipient should receive it shortly.")
    
    except Exception as e:
        speak("I'm sorry, there was an issue sending your email. Please check your connection and try again.")
        print(e)

genai.configure(api_key=GEMINI_API_KEY)
model=genai.GenerativeModel('gemini-2.0-flash') 
     
def ai(question):
    if not question:
        speak("I didn't catch your question. What would you like to know?")
        return

    try:
        speak("Let me think about that for you...")
        prompt = (
            f"You are a friendly and helpful voice assistant responding questoin of user. "
            f"Respond in a natural, spoken tone that sounds human. "
            f"Keep your answer short, clear, eg. Is there any football match today (response - Yes there is a match between ...vs .. today at .. time ). Don't include phrases like 'here is your answer' or 'as an AI'. "
            f"Just talk like you're directly replying to the user, without being too formal dont aspect or ask user again.\n\n"
            f"User asked: {question}"
        )

        response = model.generate_content(prompt)
        answer = response.text.strip()
        print(f"Gemini: {answer}")
        speak(answer)

    except Exception as e:
        speak("I'm having trouble finding that information right now. Please try again in a moment.")
        print("Gemini Error:", e)

def load_memory():
    try:
        with open("todo.json","r") as f:
            return json.load(f)
    except:
        return {}
    
def save_memory(memory):
    with open("todo.json","w") as f:
        json.dump(memory,f,indent=2)
        
def remember_task():
    speak("I'm ready to remember something important for you. What should I note down?")
    task=listen()
    if not task:
        speak("I didn't catch that. We can try again whenever you're ready.")
        return
        
    memory=load_memory()
    memory.setdefault("todo",[]).append(task)
    save_memory(memory)
    speak("Perfect! I've got that saved for you. I won't forget.")
    
def recall_task():
    memory = load_memory()
    tasks = memory.get("todo", [])
    if tasks:
        speak("Here are the things you asked me to remember:")
        for task in tasks:
            speak(task)
    else:
        speak("Your task list is completely clear! Nothing to worry about right now.")

def play_music():
    speak("What song or artist would you like to listen to?")
    song=listen()
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
        # API parameters for your location (you can change coordinates)
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 27.7005,  # Kathmandu coordinates
            "longitude": 83.4484,
            "current": ["temperature_2m", "relative_humidity_2m", "weather_code", "wind_speed_10m"],
            "timezone": "Asia/Kathmandu"
        }
        
        # Make API request
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
        
        # Get current weather data
        current = response.Current()
        temperature = round(current.Variables(0).Value(), 1)  # Temperature
        humidity = round(current.Variables(1).Value(), 1)     # Humidity
        weather_code = current.Variables(2).Value()           # Weather condition code
        wind_speed = round(current.Variables(3).Value(), 1)   # Wind speed
        
        # Convert weather code to description (simplified)
        weather_descriptions = {
            0: "clear sky",
            1: "mainly clear",
            2: "partly cloudy",
            3: "overcast",
            45: "foggy",
            48: "depositing rime fog",
            51: "light drizzle",
            53: "moderate drizzle",
            55: "dense drizzle",
            61: "slight rain",
            63: "moderate rain",
            65: "heavy rain",
            80: "slight rain showers",
            81: "moderate rain showers",
            82: "violent rain showers"
        }
        
        weather_desc = weather_descriptions.get(int(weather_code), "unknown conditions")
        
        # Create weather report
        weather_report = (
            f"Right now we have {weather_desc}. "
            f"The temperature is a comfortable {temperature} degrees Celsius. "
            f"Humidity levels are at {humidity} percent, "
            f"and there's a gentle breeze of {wind_speed} kilometers per hour."
        )
        
        return weather_report
        
    except Exception as e:
        print(f"Weather API Error: {e}")
        return "I'm sorry, I can't get the weather information at the moment. Please try again later."

def open_website():
    speak("Which website would you like me to open for you?")
    site=listen().replace(" ","").lower()
    if not site:
        speak("I didn't catch the website name. Could you repeat that?")
        return
        
    url=f"https://www.{site}.com"
    speak(f"Opening {site} for you right now!")
    webbrowser.open(url)

def recommend_movie():
    speak("What kind of movie or show are you in the mood for? Action, comedy, drama, or something else?")
    genre = listen()
    if not genre:
        speak("No problem! Let me suggest something popular for you.")
        genre = "popular"
        
    speak("Let me think of something perfect for you...")
    prompt = f"Suggest a good {genre} movie or series for a user to watch today. just respond with 2 names nothing other."
    response = model.generate_content(prompt)
    recommendation = response.text.strip()
    speak(recommendation)

def take_selfie():
    cap = None
    try:
        cap = cv2.VideoCapture(0)
        speak("Get ready for your close-up! Say cheese in 3... 2... 1...")
        time.sleep(3)
        ret, frame = cap.read()
        if ret:
            filename = f"selfie_{random.randint(1000, 9999)}.jpg"
            cv2.imwrite(filename, frame)
            speak("Perfect shot! Your selfie has been saved. You're looking great today!")
        else:
            speak("Oops! I couldn't take the photo. Let's try again later.")
    except Exception as e:
        print(f"Selfie error: {e}")
        speak("I'm having trouble with the camera right now.")
    finally:
        if cap:
            cap.release()
        cv2.destroyAllWindows()
        time.sleep(0.5)

def get_time_date():
    """Get current time and date"""
    now = datetime.datetime.now()
    current_time = now.strftime("%I:%M %p")
    current_date = now.strftime("%A, %B %d, %Y")
    
    time_response = f"The current time is {current_time}"
    date_response = f"Today is {current_date}"
    
    return time_response, date_response

def get_system_info():
    """Get system information like battery, disk space, memory"""
    try:
        # Battery information (for laptops)
        battery = psutil.sensors_battery()
        if battery:
            battery_percent = battery.percent
            battery_status = "charging" if battery.power_plugged else "not charging"
            battery_info = f"Your battery is at {battery_percent}% and {battery_status}."
        else:
            battery_info = "Battery information is not available on this system."
        
        # Disk space information
        disk_usage = shutil.disk_usage("/")
        total_space = disk_usage.total // (1024**3)  # Convert to GB
        free_space = disk_usage.free // (1024**3)   # Convert to GB
        used_space = (disk_usage.total - disk_usage.free) // (1024**3)
        
        disk_info = f"Your disk has {free_space} GB free out of {total_space} GB total space."
        
        # Memory information
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_info = f"Memory usage is at {memory_percent}%."
        
        # CPU information
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_info = f"CPU usage is at {cpu_percent}%."
        
        return f"{battery_info} {disk_info} {memory_info} {cpu_info}"
        
    except Exception as e:
        return "I'm having trouble getting system information right now."

def get_news():
    """Get latest news headlines"""
    try:
        speak("Let me fetch the latest news for you...")
        
        # Using NewsAPI with your actual API key
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            'country': 'np',  # Nepal - you can change this to 'us', 'in', 'gb', etc.
            'apiKey': NEWS_API_KEY,
            'pageSize': 5
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            news_data = response.json()
            articles = news_data.get('articles', [])
            
            if articles:
                headlines = []
                for i, article in enumerate(articles[:3], 1):  # Get top 3 headlines
                    title = article.get('title', 'No title available')
                    source = article.get('source', {}).get('name', 'Unknown source')
                    headlines.append(f"Headline {i}: {title} from {source}")
                
                news_summary = ". ".join(headlines)
                return f"Here are today's top headlines: {news_summary}"
            else:
                return "No news articles found at the moment."
        else:
            return "I'm having trouble connecting to the news service right now."
        
    except Exception as e:
        print(f"News API Error: {e}")
        return "I'm having trouble getting the news right now. Please try again later."

def perform_action(command):
    #send whatsapp
    if "whatsapp" in command or "send_whatsapp" in command:
        send_whatsapp()
    
    #send email
    elif "email" in command or "send_email" in command or "mail" in command:
        send_email()
    
    elif "movie" in command:
        recommend_movie()
        
    elif "website" in command:
        open_website()
    #ask question in web
    elif ("ask" in command or 
    "answer my question" in command or 
    "web" in command or
    "search" in command or
    "question" in command or
    "tell me about" in command):
        speak("I'm here to help! What would you like to know?")
        question=listen()
        ai(question)
        
    #listen music
    elif "play" in command or "play music" in command or "play song" in command:
        play_music()
    
    elif "weather" in command or "whats the weather" in command or "whether outside" in command:
        speak("Let me check the current weather conditions for you...")
        weather_info = get_weather()
        speak(weather_info)
    
    elif "calculator" in command:
        speak("Opening the calculator app for you!")
        os.system("open -a Calculator")
     
    elif "selfi" in command:
        take_selfie()
           
    elif "finder" in command:
        speak("Opening Finder so you can browse your files!")
        os.system("open -a Finder")
        
    elif "youtube" in command or "open youtube" in command:
        speak("Taking you to YouTube right now!")
        webbrowser.open("https://www.youtube.com")  
    
    elif "google" in command:
        speak("Opening Google for you. Ready to search!")
        webbrowser.open("https://www.google.com")
    
    # NEW FEATURES
    elif "time" in command:
        time_response, _ = get_time_date()
        speak(time_response)
    
    elif "date" in command:
        _, date_response = get_time_date()
        speak(date_response)
    
    elif "system" in command or "battery" in command or "disk" in command:
        speak("Let me check your system information...")
        system_info = get_system_info()
        speak(system_info)
    
    elif "news" in command:
        news_info = get_news()
        speak(news_info)
    
    elif "exit" in command or "stop" in command:
        return "exit"  # Return exit instead of calling exit()
    
    elif "scan" in command or "who am i" in command:
        recognize_face()
    
    elif "rememeber" in command or "note this" in command:
        remember_task()
        
    elif "todo" in command or "my todo" in command:
        recall_task()       
    else:
        speak("Hmm, I'm not sure how to help with that yet, but I'm always learning! Is there something else I can do for you?")
    
    return "continue"

def main():
    global audio_cleanup_needed
    
    try:
        speak("Hello there! I need to verify your identity first. Let me check if you're my boss.")
        if recognize_face():
            
            speak("Identity confirmed. Welcome back boss! I'm here and ready to assist you. What can I help you with today?")
            
            while True:
                command = listen()

                if not command:
                    continue

                prompt = (
                    "You are a command extractor. The user will give natural language commands like 'Can you send an email?', "
                    "'What's the weather today?', or 'Open YouTube'. You must analyze the intent and respond with "
                    "**only one** exact word from this list of available commands:\n\n"
                    "whatsapp, email, ask, play, weather, calculator, website, movie, finder, youtube, google, selfi, time, date, system, news, translate, math,exit\n\n"
                    "Until user says good bye , end chat or something more like that dont give command exit , exit command should be if user ask more properly"
                    "Until user ask like i want to know something , or help me with something o ask in that way dont give command ask"
                    "Respond with just the matching command word, nothing else.\n\n"
                    f"User command: {command}"
                )
                try:
                    response = model.generate_content(prompt)
                    action_command = response.text.strip().lower()
                    print(f"Gemini interpreted command as: {action_command}")

                    # Check if the command is "exit"
                    if action_command == "exit":
                        speak("It's been a pleasure helping you today boss! Take care and see you next time!")
                        break

                    result = perform_action(action_command)
                    if result == "exit":
                        speak("It's been a pleasure helping you today boss! Take care and see you next time!")
                        break

                except Exception as e:
                    print("Error with Gemini command generation:", e)
                    speak("I'm having a bit of trouble understanding that command. Could you try rephrasing it for me?")
        else:
            speak("I'm sorry, but I couldn't verify your identity. Access is restricted to authorized users only.")
    
    finally:
        # Always cleanup audio resources when exiting
        cleanup_audio_resources()
        
        # Additional cleanup
        try:
            if 'openmeteo' in globals():
                del openmeteo
        except:
            pass
        
        print("Assistant cleanup completed")

if __name__ == "__main__":
    main()