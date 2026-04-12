"""
WebMain.py — Flask web server that connects the Friday AI frontend
to the existing Friday AI backend (Model, Chatbot, RealtimeSearchEngine,
Automation, TextToSpeech).

Run with:  python3.13 WebMain.py
Then open: http://localhost:8000
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
from dotenv import dotenv_values
from queue import Queue
import threading
import sys
import os
import re
import io
import time
import psutil
import traceback

# ── Force UTF-8 ──────────────────────────────────────────────────────────────
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── Environment ──────────────────────────────────────────────────────────────
env_vars = dotenv_values(".env")
Username      = env_vars.get("Username", "User")
Assistantname = env_vars.get("Assistantname", "Friday")

# ── File-based status helpers (shared with TTS/backend) ──────────────────────
current_dir = os.getcwd()
TempDirPath = os.path.join(current_dir, "Frontend", "Files")

# Ensure directories exist
os.makedirs(TempDirPath, exist_ok=True)
os.makedirs(os.path.join(current_dir, "Data"), exist_ok=True)

def _write(filename, content):
    """Write content to a file in the TempDir."""
    with open(os.path.join(TempDirPath, filename), "w", encoding="utf-8") as f:
        f.write(content)


def _read(filename, default=""):
    """Read content from a file in the TempDir."""
    try:
        with open(os.path.join(TempDirPath, filename), "r", encoding="utf-8") as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        return default


def set_stop_status(s):
    """Update stop status."""
    _write("Stop.data", s)


def get_stop_status():
    """Retrieve stop status."""
    return _read("Stop.data", "False")


def set_assistant_status(s):
    """Update assistant status."""
    _write("Status.data", s)

# ── Initialize data files ────────────────────────────────────────────────────
for fname, default in [("Mic.data", "True"), ("Stop.data", "False"),
                       ("Status.data", "Ready"), ("Responses.data", "")]:
    path = os.path.join(TempDirPath, fname)
    if not os.path.exists(path):
        _write(fname, default)

chatlog = os.path.join(current_dir, "Data", "ChatLog.json")
if not os.path.exists(chatlog):
    with open(chatlog, "w") as f:
        f.write("[]")

# ── Monkey-patch keyboard.is_pressed to prevent crashes in web context ───────
# The backend modules (Chatbot.py, RealtimeSearchEngin.py) call keyboard.is_pressed('w')
# inside their generators. In a web server, this can crash or behave unexpectedly.
# We replace it with a function that checks our interrupt flag instead.
import keyboard as _real_keyboard

_interrupt_flag = threading.Event()
_original_is_pressed = _real_keyboard.is_pressed

def _patched_is_pressed(key):
    """Check our web interrupt flag instead of actual keyboard state."""
    if key == 'w':
        return _interrupt_flag.is_set()
    try:
        return _original_is_pressed(key)
    except Exception:
        return False


_real_keyboard.is_pressed = _patched_is_pressed

# ── NOW import the backend modules (after monkey-patching keyboard) ──────────
from backend.Model import FirstLayerDMM
from backend.RealtimeSearchEngin import RealtimeSearchEngine
from backend.Automation import WEBSITE_SHORTCUTS, _is_url, _ensure_scheme
from backend.Chatbot import ChatBot
from backend.TextToSpeech import TextToSpeech
from backend.ImageGeneration import GenerateImages

# ── Query modifier ───────────────────────────────────────────────────────────
def QueryModifier(Query):
    new_query = Query.lower().strip()
    if not new_query:
        return ""
    query_words = new_query.split()
    question_words = ["how", "what", "who", "where", "when", "why",
                      "which", "whose", "whom", "can you", "what's",
                      "where's", "how's"]
    if any(word + " " in new_query for word in question_words):
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "?"
        else:
            new_query += "?"
    else:
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "."
        else:
            new_query += "."
    return new_query.capitalize()

# ── TTS queue ────────────────────────────────────────────────────────────────
TTS_Queue = Queue()

def tts_worker():
    """Background worker for TTS playback."""
    while True:
        try:
            text = TTS_Queue.get()
            if text and get_stop_status() == "False" and not _interrupt_flag.is_set():
                TextToSpeech(text)
            TTS_Queue.task_done()
        except Exception as e:
            print(f"[tts_worker] Error: {e}")
            time.sleep(0.5)


threading.Thread(target=tts_worker, daemon=True).start()

# Remove lock to prevent "Heavily Processing" errors
# _processing_lock = threading.Lock()

# ── Flask app ────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates")
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.route("/")
def index():
    # no_cache headers so browser always gets fresh HTML
    response = app.make_response(render_template("index.html"))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route("/Data/<path:filename>")
@app.route("/data/<path:filename>")
def serve_data(filename):
    # Ensure we use the correct absolute path to the Data folder
    data_folder = os.path.join(current_dir, "Data")
    return send_from_directory(data_folder, filename)

@app.route("/poll_hotkey")
def get_hotkey():
    try:
        a_pressed = _original_is_pressed('a')
        w_pressed = _original_is_pressed('w')
        # If 'w' is physically pressed off-screen, trigger interrupt globally format
        if w_pressed:
            _interrupt_flag.set()
            set_stop_status("True")
        return jsonify(a_pressed=a_pressed)
    except Exception:
        return jsonify(a_pressed=False)

# ── POST /speak ──────────────────────────────────────────────────────────────
@app.route("/speak", methods=["POST"])
def speak():
    data = request.get_json(force=True)
    user_text = (data.get("text") or "").strip()
    if not user_text:
        return jsonify(reply="I didn't catch that.", duration_ms=1500), 200

    # Clear any previous interrupt and ensure we have a fresh start
    _interrupt_flag.clear()
    set_stop_status("False")

    # Flush any queued TTS from a previous request immediately
    while not TTS_Queue.empty():
        try: TTS_Queue.get_nowait()
        except: break

    try:

        print(f"\n{'─'*50}")
        print(f"[WebMain] User: {user_text}")

        # ── 1. Decision layer ────────────────────────────────────────────
        try:
            Decision = FirstLayerDMM(user_text)
        except Exception as e:
            print(f"[WebMain] Decision error: {e}")
            Decision = ["general " + user_text]

        print(f"[WebMain] Decision: {Decision}")

        full_reply = ""
        action_urls = []

        for task in Decision:
            if _interrupt_flag.is_set():
                break

            # ── Image generation ─────────────────────────────────────────
            if "generate image" in task:
                prompt = task.replace("generate image", "").strip()
                full_reply += f"Here are the images for '{prompt}': "
                try:
                    img_data_path = os.path.join(current_dir, "Frontend", "Files", "ImageGeneration.data")
                    # Clear any old results
                    resp_path = os.path.join(current_dir, "Frontend", "Files", "Responses.data")
                    if os.path.exists(resp_path): os.remove(resp_path)
                    
                    # Direct call is much faster than subprocess
                    GenerateImages(prompt)
                    
                    if os.path.exists(resp_path):
                        with open(resp_path, "r", encoding="utf-8") as rf:
                            resp_content = rf.read().strip()
                        if resp_content.startswith("IMAGE:"):
                            abs_img = resp_content.replace("IMAGE:", "").strip()
                            idx = abs_img.lower().rfind("data\\")
                            if idx == -1: idx = abs_img.lower().rfind("data/")
                            
                            if idx != -1:
                                rel_path = abs_img[idx:].replace("\\", "/") # e.g., "Data/img.jpg"
                                # Add timestamp to bust browser cache
                                ts = int(time.time())
                                full_reply += f" I would be absolutely delighted to show you the images I've generated for '{prompt}'! I've put a lot of effort into making them perfect for you. I truly hope they capture exactly what you were imagining! <br><img src='/{rel_path}?v={ts}' style='max-width:100%; max-height: 450px; border-radius:15px; margin-top:15px; border: 2px solid var(--accent); box-shadow: 0 10px 30px rgba(0,0,0,0.5); display:block;' /> "
                            else:
                                # Fallback if Data folder isn't found in path
                                filename = os.path.basename(abs_img)
                                ts = int(time.time())
                                full_reply += f" I have successfully generated the images for you, {Username}! <br><img src='/Data/{filename}?v={ts}' style='max-width:100%; max-height: 450px; border-radius:15px; margin-top:15px; border: 2px solid var(--accent); box-shadow: 0 10px 30px rgba(0,0,0,0.5); display:block;' /> "
                        else:
                            full_reply += f" I've completed the generation process for '{prompt}', {Username}! I am so excited for you to see the results. "
                    else:
                        full_reply += f" I am so sorry, {Username}, but it seems I hit a small snag while trying to display the images for '{prompt}'. However, I've done my best to ensure they are being processed properly! "
                except Exception as e:
                    full_reply += f" I am so sorry, {Username}, but I ran into a tiny snag while creating your images: {e}. "

            # ── Browser-Oriented Automation ──────────────────────────
            elif any(task.startswith(func) for func in ["open", "play", "google search", "youtube search"]):
                target = ""
                url = ""
                
                if task.startswith("open "):
                    target = task.replace("open ", "").strip()
                    # Check if it's a known website or looks like a URL
                    if target.lower() in WEBSITE_SHORTCUTS:
                        url = WEBSITE_SHORTCUTS[target.lower()]
                    elif _is_url(target):
                        url = _ensure_scheme(target)
                    else:
                        # If it's not a clear website, we treat it as a "search and open"
                        url = f"https://www.google.com/search?q={target}&btnI=1" # "I'm feeling lucky"
                
                elif task.startswith("google search "):
                    target = task.replace("google search ", "").strip()
                    url = f"https://www.google.com/search?q={target}"
                
                elif task.startswith("youtube search "):
                    target = task.replace("youtube search ", "").strip()
                    url = f"https://www.youtube.com/results?search_query={target}"
                
                elif task.startswith("play "):
                    target = task.replace("play ", "").strip()
                    # Use YouTube search for 'play' in web version
                    url = f"https://www.youtube.com/results?search_query={target}"

                if url:
                    action_urls.append(url)
                    full_reply += f" Opening {target or 'requested page'} in your browser. "
                else:
                    full_reply += " I can only open websites and searches in the web version. "

            # ── System tasks (Ignored in Web Version) ────────────────────
            elif any(task.startswith(func) for func in ["close", "system", "reminder"]):
                full_reply += f" (System task '{task.split()[0]}' is disabled in the web version to focus on your browser.) "

            # ── Realtime search or general chat ──────────────────────────
            elif "realtime" in task or "general" in task:
                clean_query = task.replace("realtime", "").replace("general", "").replace("content", "").strip()
                modified_query = QueryModifier(clean_query)

                if "realtime" in task:
                    print(f"[WebMain] → RealtimeSearchEngine: {modified_query}")
                    generator = RealtimeSearchEngine(modified_query)
                else:
                    print(f"[WebMain] → ChatBot: {modified_query}")
                    generator = ChatBot(modified_query)

                # Consume the streaming generator to get the final answer
                answer = ""
                try:
                    for chunk in generator:
                        if _interrupt_flag.is_set():
                            break
                        answer = chunk
                except Exception as e:
                    print(f"[WebMain] Generator error: {e}")
                    traceback.print_exc()
                    if not answer:
                        answer = f"Sorry, I encountered an error: {e}"

                full_reply += answer

            # ── Exit ─────────────────────────────────────────────────────
            elif "exit" in task:
                full_reply += "Goodbye!"

        if not full_reply or len(full_reply.split()) < 25:
            if not full_reply:
                full_reply = f"I am so sorry, {Username}, but I missed that! I would be absolutely delighted if you could repeat it so I can provide you with a detailed and cheerful response worthy of your time! "
            elif "Goodbye" in full_reply:
                full_reply = f"{full_reply} It has been a truly remarkable and wonderful experience assisting you today! I hope you have an exceptionally pleasant, bright, and productive day ahead, and I eagerly look forward to our next interaction whenever you need me. Goodbye for now, and take great care!"
            else:
                # APPEND instead of replace
                expansion = f" I also want to mention that I am always here to support you with the utmost respect and energy, {Username}! My goal is to make sure you have the most detailed and helpful information possible. Is there any other aspect of this or another topic you'd like to explore in depth together?"
                full_reply = full_reply.strip() + expansion

        # ── 2. Queue TTS ─────────────────────────────────────────────────
        is_audio = data.get("is_audio", True)
        if is_audio and not _interrupt_flag.is_set():
            # Pass the WHOLE reply to TTS at once.
            # Strip all punctuation and extra whitespace for truly ZERO-GAP speech.
            tts_text = re.sub(r'<[^>]+>', '', full_reply).strip()
            # Remove all punctuation that causes pauses
            for char in ".,!?;:-":
                tts_text = tts_text.replace(char, "")
            # Collapse extra spaces
            tts_text = re.sub(r'\s+', ' ', tts_text).strip()
            
            if tts_text and len(tts_text.split()) > 1:
                TTS_Queue.put(tts_text)

        duration_ms = max(2000, len(full_reply) * 60)

        print(f"[WebMain] Reply ({len(full_reply)} chars): {full_reply[:200]}")
        print(f"{'─'*50}")
        return jsonify(reply=full_reply, duration_ms=duration_ms, action_urls=action_urls), 200

    except Exception as e:
        print(f"[WebMain] CRITICAL ERROR: {e}")
        traceback.print_exc()
        return jsonify(reply=f"I'm so sorry, but I encountered a small technical hiccup while processing your request. Could you please try asking again?", duration_ms=3000), 200


# ── POST /interrupt ──────────────────────────────────────────────────────────
@app.route("/interrupt", methods=["POST"])
def interrupt():
    """Handle user interrupt requests."""
    print("[WebMain] ⚡ Interrupt received")
    _interrupt_flag.set()
    set_stop_status("True")

    # Flush the TTS queue
    while not TTS_Queue.empty():
        try: TTS_Queue.get_nowait()
        except: break

    # Kill any running PlayAudio.py processes
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if proc.info.get('name') and 'python' in proc.info['name'].lower():
                cmdline = proc.info.get('cmdline') or []
                if any('PlayAudio.py' in part for part in cmdline):
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # We DON'T set StopStatus back to False here anymore. 
    # Let the next speak request or the user reset it.
    return jsonify(status="interrupted"), 200


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{'='*50}")
    print(f"  Friday AI — Web Interface")
    print(f"  Open http://localhost:8000 in Chrome/Edge")
    print(f"{'='*50}\n")
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)
