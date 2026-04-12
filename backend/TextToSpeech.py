import os
import asyncio
import edge_tts
import time
import subprocess
import sys
import psutil
import keyboard
import threading
from dotenv import dotenv_values

# Load environment variables
env_vars = dotenv_values(".env")
AssistantVoice = env_vars.get("AssistantVoice", "en-US-AriaNeural").strip()

# Define paths
current_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(current_dir)
data_dir = os.path.join(base_dir, "Data")

# Ensure Data directory exists
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

def GetStopStatus():
    try:
        data_path = os.path.join(base_dir, "Frontend", "Files", "Stop.data")
        if not os.path.exists(data_path):
            return "False"
        with open(data_path, "r", encoding='utf-8') as file:
            return file.read().strip()
    except: return "False"

def SetStopStatus(Status):
    try:
        data_path = os.path.join(base_dir, "Frontend", "Files", "Stop.data")
        with open(data_path, "w", encoding='utf-8') as file:
            file.write(str(Status))
    except: pass

# Double-buffering logic
file_toggle = 0
tts_lock = threading.Lock()

async def SaveAudio(text, file_path):
    try:
        communicate = edge_tts.Communicate(text, AssistantVoice, rate="+22%", pitch="+0Hz")
        await communicate.save(file_path)
        return True
    except Exception as e:
        print(f"EdgeTTS Save Error: {e}")
        return False

def TextToSpeech(Text):
    global file_toggle
    if not Text or len(str(Text).strip()) < 2: 
        return
    
    with tts_lock:
        file_toggle = 1 - file_toggle
        current_file = os.path.join(data_dir, f"speech_{file_toggle}.mp3")
        
        # Clean text: remove markdown symbols and extra spaces
        clean_text = Text.replace("*", "").replace("#", "").replace("`", "").replace("assistant", "").replace("friday", "").strip()
        
        try:
            # Generate Audio using a fresh event loop
            success = asyncio.run(SaveAudio(clean_text, current_file))
            if not success:
                return
        except Exception as e:
            print(f"TTS Generation Exception: {e}")
            return

    # Play Audio
    if os.path.exists(current_file) and os.path.getsize(current_file) > 10:
        try:
            player_script = os.path.join(current_dir, "PlayAudio.py")
            
            # Start player process
            p = subprocess.Popen(
                [sys.executable, player_script, current_file],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True
            )
            
            # Wait and check for interruption
            while p.poll() is None:
                if GetStopStatus() == "True":
                    p.terminate()
                    # Clean up all dangling players
                    for proc in psutil.process_iter(['name', 'cmdline']):
                        try:
                            if 'python' in proc.info['name'].lower():
                                cmdline = proc.info.get('cmdline')
                                if cmdline and any('PlayAudio.py' in part for part in cmdline):
                                    proc.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    break
                time.sleep(0.05)
            
            # Reset is now handled by WebMain.py

        except Exception as e:
            print(f"TTS Playback Exception: {e}")
    else:
        print(f"TTS Error: Audio file {current_file} not found or empty.")

if __name__ == "__main__":
    while True:
        txt = input("Enter text: ")
        if txt.lower() == 'exit': break
        TextToSpeech(txt)