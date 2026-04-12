from Frontend.GUI import (
    GraphicalUserInterface,
    SetAssistantStatus,
    ShowTextToScreen,
    TempDirectoryPath,
    SetMicrophoneStatus,
    AnswerModifier,
    QueryModifier,
    GetMicrophoneStatus,
    GetAssistantStatus,
    GetStopStatus,
    SetStopStatus
)
from backend.Model import FirstLayerDMM
from backend.RealtimeSearchEngin import RealtimeSearchEngine
from backend.Automation import Automation
from backend.SpeechToText import SpeechRecognition
from backend.Chatbot import ChatBot
from backend.TextToSpeech import TextToSpeech
from dotenv import dotenv_values
from asyncio import run
from time import sleep
from queue import Queue
import subprocess
import threading
import json
import os
import sys
import keyboard
import re
import time
import io

# Force UTF-8 encoding for standard output
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

env_vars = dotenv_values(".env")
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
DefaultMessage = f'''{Username} : Hello {Assistantname}, How are you?
{Assistantname} : Welcome {Username}. I am doing well. How may i help you?'''
subprocesses = []
Functions = ["open", "close", "play", "system", "google search", "youtube search", "content", "reminder"]

def ShowDefaultChatIfNoChats():
    try:
        File = open(r'Data\ChatLog.json', "r", encoding='utf-8')
        if len(File.read()) < 5:
            with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
                file.write("")
            with open(TempDirectoryPath('Responses.data'), 'w', encoding='utf-8') as file:
                file.write(DefaultMessage)
        File.close()
    except: pass

def ReadChatLogJson():
    try:
        with open(r'Data\ChatLog.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except: return []

def ChatLogIntegration():
    json_data = ReadChatLogJson()
    formatted_chatlog = ""
    for entry in json_data:
        if entry["role"] == "user":
            formatted_chatlog += f"User: {entry['content']}\n"
        elif entry["role"] == "assistant":
            formatted_chatlog += f"Assistant: {entry['content']}\n"
    formatted_chatlog = formatted_chatlog.replace("User", Username + " ")
    formatted_chatlog = formatted_chatlog.replace("Assistant", Assistantname + " ")
    with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
        file.write(AnswerModifier(formatted_chatlog))

def ShowChatsOnGUI():
    try:
        File = open(TempDirectoryPath('Database.data'), "r", encoding='utf-8')
        Data = File.read()
        if len(Data) > 0:
            ShowTextToScreen(Data)
        File.close()
    except: pass

def InitialExecution():
    print("Initializing Friday AI...")
    SetAssistantStatus("Initializing...")
    SetMicrophoneStatus("True")
    SetStopStatus("False")
    ShowTextToScreen("")
    ShowDefaultChatIfNoChats() # Initialize files
    ChatLogIntegration()
    print("Initialization Complete.")
    SetAssistantStatus("Ready")

InitialExecution()

# Global TTS Queue for sequential playback
TTS_Queue = Queue()

def TTS_Worker():
    while True:
        try:
            text = TTS_Queue.get()
            if text:
                if GetStopStatus() == "False":
                    TextToSpeech(text)
            TTS_Queue.task_done()
        except Exception as e:
            print(f"Error in TTS_Worker: {e}")
            sleep(1)

# Start the TTS worker thread
threading.Thread(target=TTS_Worker, daemon=True).start()

def MainExecution():
    try:
        Query = SpeechRecognition()
        
        if not Query: 
            SetAssistantStatus("Ready")
            return
        
        # New query starting: Clear existing speech queue and stop current speech
        while not TTS_Queue.empty():
            try: TTS_Queue.get_nowait()
            except: break
        SetStopStatus("True") # Signal current speech to stop
        sleep(0.1)
        SetStopStatus("False")

        print(f"User Query: {Query}")
        
        ShowTextToScreen(f"{Username} : {Query}")
        SetAssistantStatus("Thinking...")
        Decision = FirstLayerDMM(Query)
        print(f"\nDecision : {Decision}\n")

        Answer = ""
        # Process each decision
        for queries in Decision:
            if "generate image" in queries:
                prompt = queries.replace("generate image", "").strip()
                ShowTextToScreen(f"{Assistantname} : Generating images for '{prompt}'...")
                with open(r"Frontend\Files\ImageGeneration.data", "w") as file:
                    file.write(f"{prompt},True")
                try:
                    project_root = os.path.dirname(os.path.abspath(__file__))
                    img_script = os.path.join(project_root, 'backend', 'ImageGeneration.py')
                    subprocess.Popen([sys.executable, img_script], shell=False, cwd=project_root)
                except Exception as e: print(f"Image Error: {e}")
            
            elif any(queries.startswith(func) for func in Functions):
                Automation([queries])
                Answer = "Task Executed."

            elif "realtime" in queries or "general" in queries:
                mode = "Searching..." if "realtime" in queries else "Thinking..."
                SetAssistantStatus(mode)
                
                clean_query = queries.replace("realtime", "").replace("general", "").strip()
                if "realtime" in queries:
                    print(f"DEBUG: Triggering RealtimeSearchEngine for: {clean_query}")
                    AnswerGenerator = RealtimeSearchEngine(QueryModifier(clean_query))
                else:
                    print(f"DEBUG: Triggering ChatBot for: {clean_query}")
                    AnswerGenerator = ChatBot(QueryModifier(clean_query))
                
                full_response = ""
                unspoken_buffer = ""
                
                for chunk in AnswerGenerator:
                    if GetStopStatus() == "True" or keyboard.is_pressed('w'):
                        full_response = ""
                        while not TTS_Queue.empty():
                            try: TTS_Queue.get_nowait()
                            except: break
                        SetStopStatus("True")
                        break
                    
                    new_chars = chunk[len(full_response):]
                    full_response = chunk
                    unspoken_buffer += new_chars
                    
                    # Streaming for GUI smoothness
                    words = new_chars.split(' ')
                    temp_shown = full_response[:-len(new_chars)]
                    for i, word in enumerate(words):
                        space = " " if i > 0 else ""
                        temp_shown += space + word
                        ShowTextToScreen(f"{Assistantname} : {temp_shown}")
                        sleep(0.01) # FAST REPLIES
                    
                    if any(term in unspoken_buffer for term in ['.', '!', '?', '\n']):
                        if len(unspoken_buffer) > 30: # Even faster speech (lowered from 40/120)
                            parts = re.split(r'(?<=[.!?])[\s\n]+', unspoken_buffer, maxsplit=1)
                            if len(parts) > 1:
                                sentence_to_speak = parts[0].strip()
                                if len(sentence_to_speak.split()) > 1:
                                    TTS_Queue.put(sentence_to_speak)
                                unspoken_buffer = parts[1]
                
                if unspoken_buffer.strip() and GetStopStatus() == "False":
                    clean_final = unspoken_buffer.strip().rstrip('.,!?')
                    TTS_Queue.put(clean_final)
                
                Answer = full_response
            
            elif "exit" in queries:
                Answer = "Goodbye!"
                TTS_Queue.put(Answer)

        SetAssistantStatus("Ready")
        return True
    
    except Exception as e:
        print(f"Error in MainExecution: {e}")
        SetAssistantStatus("Ready")
        return False

def FirstThread():
    print("Execution Thread Started.")
    while True:
        MainExecution()

def SecondThread():
    GraphicalUserInterface()

def InterruptionListener():
    while True:
        if keyboard.is_pressed('w'):
            SetStopStatus("True")
            while not TTS_Queue.empty():
                try: TTS_Queue.get_nowait()
                except: break
            sleep(0.1)
        sleep(0.01)

if __name__ == "__main__":
    thread_interrupt = threading.Thread(target=InterruptionListener, daemon=True)
    thread_interrupt.start()
    thread1 = threading.Thread(target=FirstThread, daemon=True)
    thread1.start()
    SecondThread()