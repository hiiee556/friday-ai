from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import dotenv_values
import os
import mtranslate as mt
import time
import keyboard

# Load environment variables
env_vars = dotenv_values(".env")
InputLanguage = env_vars.get("InputLanguage", "en")

HtmlCode = """<!DOCTYPE html>
<html lang="en">
<head><title>Speech Recognition</title></head>
<body>
    <button id="start" onclick="startRecognition()">Start</button>
    <button id="end" onclick="stopRecognition()">Stop</button>
    <p id="output"></p>
    <script>
        const output = document.getElementById('output');
        let recognition;
        function startRecognition() {
            output.innerHTML = "";
            recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.lang = "en-US";
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.onresult = function(event) {
                let finalTranscript = '';
                for (let i = 0; i < event.results.length; ++i) {
                    finalTranscript += event.results[i][0].transcript;
                }
                output.innerHTML = finalTranscript;
            };
            recognition.start();
        }
        function stopRecognition() {
            if (recognition) { recognition.stop(); }
        }
    </script>
</body>
</html>"""

HtmlCode = HtmlCode.replace('recognition.lang = "en-US";', f'recognition.lang = "{InputLanguage}";')

with open("DataVoice.html", "w") as f:
    f.write(HtmlCode)

current_dir = os.getcwd()
chrome_options = Options()
chrome_options.add_argument("--use-fake-ui-for-media-stream")
chrome_options.add_argument("--headless=new")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

TempDirPath = rf"{current_dir}/Frontend/Files"
if not os.path.exists(TempDirPath):
    os.makedirs(TempDirPath)

def SetAssistantStatus(Status):
    with open(rf"{TempDirPath}/Status.data", "w", encoding="utf-8") as file:
        file.write(Status)

def QueryModifier(Query):
    new_query = Query.lower().strip()
    if not new_query: return ""
    question_words = ["how", "what", "who", "where", "when", "why", "can", "is", "should"]
    if any(new_query.startswith(word) for word in question_words):
        if not new_query.endswith("?"): new_query += "?"
    else:
        if not new_query.endswith("."): new_query += "."
    return new_query.capitalize()

def UniversalTranslator(Text):
    return mt.translate(Text, "en", "auto").capitalize()

def SpeechRecognition():
    # Only load the page if it's not already loaded
    if driver.current_url != f"file:///{current_dir.replace(os.sep, '/')}/DataVoice.html":
        driver.get(f"file:///{current_dir}/DataVoice.html")
    
    SetAssistantStatus("Hold 'Caps Lock' to Speak")
    
    # Wait for 'A' key
    while not keyboard.is_pressed('caps lock'):
        time.sleep(0.01)
        
    SetAssistantStatus("Listening...")
    driver.find_element(By.ID, "start").click()
    
    # Wait for 'A' release
    while keyboard.is_pressed('caps lock'):
        time.sleep(0.01)
        
    driver.find_element(By.ID, "end").click()
    time.sleep(0.2)
    
    Text = driver.find_element(By.ID, "output").text.strip()
    
    if not Text:
        return ""

    if "en" in InputLanguage.lower():
        return QueryModifier(Text)
    else:
        SetAssistantStatus("Translating...")
        return QueryModifier(UniversalTranslator(Text))

if __name__ == "__main__":
    while True:
        print(SpeechRecognition())