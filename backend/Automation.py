from AppOpener import close, open as appopen
from webbrowser import open as webopen
from pywhatkit import search, playonyt
from dotenv import dotenv_values
from bs4 import BeautifulSoup
from rich import print
import groq
import cohere
import webbrowser
import subprocess
import requests
import keyboard
import asyncio
import psutil
import os
import re
import shutil

# Load environment variables
env_vars = dotenv_values(".env")
GroqAPIKey = env_vars.get("GroqAPIKey")
CohereAPIKey = env_vars.get("CohereAPIKey")
Username = env_vars.get("Username", "User")

useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36"

# Initialize clients lazily
_groq_client = None
_co_client = None

def get_groq_client():
    global _groq_client
    if _groq_client is None:
        key = env_vars.get("GroqAPIKey")
        if key:
            _groq_client = groq.Groq(api_key=key)
    return _groq_client

def get_cohere_client():
    global _co_client
    if _co_client is None:
        key = env_vars.get("CohereAPIKey")
        if key:
            _co_client = cohere.Client(api_key=key)
    return _co_client

# System prompt for Content Writer
SystemChatBot = f"You are a content writer assistant for {Username}. Write content like letters, code, essays, emails, poems etc. Be creative and detailed."

messages = []


# ─────────────────────────────────────────────
#  HELPER: detect if a string is a URL / domain
# ─────────────────────────────────────────────
def _is_url(text: str) -> bool:
    """Return True if text looks like a URL or bare domain."""
    text = text.strip().lower()
    if re.match(r'^https?://', text):
        return True
    # bare domain patterns like google.com, sub.domain.org/path
    if re.match(r'^([a-z0-9-]+\.)+[a-z]{2,}(/.*)?$', text):
        return True
    return False


def _ensure_scheme(url: str) -> str:
    """Prepend https:// if no scheme present."""
    url = url.strip()
    if not re.match(r'^https?://', url):
        return "https://" + url
    return url


# ─────────────────────────────────────────────
#  HELPER: find an installed executable on PATH
# ─────────────────────────────────────────────
def _find_executable(name: str):
    """Return full path to an executable if found on PATH, else None."""
    return shutil.which(name) or shutil.which(name + ".exe")


# ── Well-known website shortcuts ──────────────────────────────────────
WEBSITE_SHORTCUTS = {
    # Search & productivity
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "google drive": "https://drive.google.com",
    "google docs": "https://docs.google.com",
    "google sheets": "https://sheets.google.com",
    "google slides": "https://slides.google.com",
    "google maps": "https://maps.google.com",
    "google translate": "https://translate.google.com",
    "google photos": "https://photos.google.com",
    "google meet": "https://meet.google.com",
    "google calendar": "https://calendar.google.com",
    "google classroom": "https://classroom.google.com",
    # Social media
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "twitter": "https://www.twitter.com",
    "x": "https://www.x.com",
    "linkedin": "https://www.linkedin.com",
    "reddit": "https://www.reddit.com",
    "tiktok": "https://www.tiktok.com",
    "pinterest": "https://www.pinterest.com",
    "snapchat": "https://www.snapchat.com",
    "tumblr": "https://www.tumblr.com",
    "quora": "https://www.quora.com",
    "discord": "https://discord.com",
    "telegram": "https://web.telegram.org",
    "whatsapp": "https://web.whatsapp.com",
    "slack": "https://slack.com",
    # Dev & tech
    "github": "https://www.github.com",
    "gitlab": "https://www.gitlab.com",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "npmjs": "https://www.npmjs.com",
    "pypi": "https://pypi.org",
    "replit": "https://replit.com",
    "codepen": "https://codepen.io",
    "leetcode": "https://leetcode.com",
    "hackerrank": "https://www.hackerrank.com",
    "w3schools": "https://www.w3schools.com",
    "mdn": "https://developer.mozilla.org",
    "devdocs": "https://devdocs.io",
    "vercel": "https://vercel.com",
    "netlify": "https://netlify.com",
    "heroku": "https://www.heroku.com",
    "aws": "https://aws.amazon.com",
    "azure": "https://portal.azure.com",
    "gcp": "https://console.cloud.google.com",
    # AI / tools
    "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai",
    "gemini": "https://gemini.google.com",
    "perplexity": "https://www.perplexity.ai",
    "huggingface": "https://huggingface.co",
    "copilot": "https://copilot.microsoft.com",
    # Entertainment
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "amazon prime": "https://www.primevideo.com",
    "prime video": "https://www.primevideo.com",
    "hotstar": "https://www.hotstar.com",
    "disney plus": "https://www.disneyplus.com",
    "disneyplus": "https://www.disneyplus.com",
    "twitch": "https://www.twitch.tv",
    "soundcloud": "https://soundcloud.com",
    "apple music": "https://music.apple.com",
    # Shopping & finance
    "amazon": "https://www.amazon.com",
    "flipkart": "https://www.flipkart.com",
    "ebay": "https://www.ebay.com",
    "paypal": "https://www.paypal.com",
    "binance": "https://www.binance.com",
    "coinbase": "https://www.coinbase.com",
    # News
    "bbc": "https://www.bbc.com",
    "cnn": "https://www.cnn.com",
    "the hindu": "https://www.thehindu.com",
    "times of india": "https://timesofindia.com",
    "ndtv": "https://www.ndtv.com",
    # Misc
    "wikipedia": "https://www.wikipedia.org",
    "archive": "https://web.archive.org",
    "wayback machine": "https://web.archive.org",
    "wolframalpha": "https://www.wolframalpha.com",
    "canva": "https://www.canva.com",
    "figma": "https://www.figma.com",
    "notion": "https://www.notion.so",
    "trello": "https://trello.com",
    "jira": "https://www.atlassian.com/software/jira",
    "zoom": "https://zoom.us",
    "teams": "https://teams.microsoft.com",
}

# ─────────────────────────────────────────────────────────────────────────────
#  OpenApp  –  tries every strategy in order; gives up gracefully
# ─────────────────────────────────────────────────────────────────────────────
def OpenApp(app: str, sess=requests.session()):
    """
    Universal app / webpage opener.
    Priority order:
      1. Direct URL / domain  →  browser
      2. Well-known website shortcuts  →  browser
      3. AppOpener (installed apps)
      4. Executable search on PATH
      5. Windows 'start' command  (works for most installed apps & ms-* URIs)
      6. Google search → first result  →  browser (fallback)
    """
    app = app.strip()

    # ── 1. Direct URL / bare domain ──────────────────────────────────────────
    if _is_url(app):
        webopen(_ensure_scheme(app))
        print(f"[OpenApp] Opened URL: {app}")
        return True

    app_lower = app.lower()

    # ── 2. Well-known website shortcuts ──────────────────────────────────────

    if app_lower in WEBSITE_SHORTCUTS:
        webopen(WEBSITE_SHORTCUTS[app_lower])
        print(f"[OpenApp] Opened website: {app}")
        return True

    # ── 3. AppOpener (handles most installed Windows apps) ───────────────────
    try:
        appopen(app, match_closest=True, output=True, throw_error=True)
        print(f"[OpenApp] AppOpener opened: {app}")
        return True
    except Exception:
        pass

    # ── 4. Executable on PATH ─────────────────────────────────────────────────
    candidate_names = [
        app_lower,
        app_lower.replace(" ", ""),
        app_lower.replace(" ", "-"),
        app_lower.replace(" ", "_"),
    ]
    for name in candidate_names:
        exe = _find_executable(name)
        if exe:
            subprocess.Popen([exe])
            print(f"[OpenApp] Launched executable: {exe}")
            return True

    # ── 5. Windows 'start' command ────────────────────────────────────────────
    #    Works for: app names in Start Menu, ms-settings:, ms-paint:, calc, etc.
    try:
        subprocess.Popen(["start", "", app], shell=True)
        print(f"[OpenApp] 'start' launched: {app}")
        return True
    except Exception:
        pass

    # ── 6. Google-search fallback → open first result ─────────────────────────
    print(f"[OpenApp] Falling back to Google search for: {app}")
    try:
        url = f"https://www.google.com/search?q={app}"
        headers = {"User-Agent": useragent}
        response = sess.get(url, headers=headers, timeout=8)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', {'jsname': 'UWckNb'})
            hrefs = [l.get('href') for l in links if l.get('href')]
            if hrefs:
                webopen(hrefs[0])
                print(f"[OpenApp] Opened search result: {hrefs[0]}")
                return True
        # If no direct link found, open the Google search page itself
        webopen(url)
    except Exception as e:
        print(f"[OpenApp] All strategies failed for '{app}': {e}")

    return False


# ─────────────────────────────────────────────
#  CloseApp  –  unchanged logic, kept intact
# ─────────────────────────────────────────────
def CloseApp(app):
    app = app.lower().strip()
    try:
        try:
            close(app, match_closest=True, output=False, throw_error=True)
            print(f"AppOpener: Closed '{app}'")
            return True
        except:
            pass

        app_closed = False
        mappings = {
            "chrome": ["chrome.exe"],
            "edge": ["msedge.exe"],
            "browser": ["chrome.exe", "msedge.exe", "firefox.exe"],
            "notepad": ["notepad.exe"],
            "calculator": ["Calculator.exe", "CalculatorApp.exe"],
            "spotify": ["Spotify.exe"],
            "discord": ["Discord.exe"],
        }

        target_procs = mappings.get(app, [app if app.endswith(".exe") else f"{app}.exe"])

        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name'].lower()
                if any(t.lower() in proc_name for t in target_procs) or app in proc_name:
                    try:
                        proc.terminate()
                        proc.wait(timeout=1)
                    except psutil.TimeoutExpired:
                        pass
                    if proc.is_running():
                        proc.kill()
                    app_closed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if app_closed:
            print(f"Psutil: Closed process matching '{app}'")
        return app_closed

    except Exception as e:
        print(f"Critical Error in CloseApp for '{app}': {e}")
        return False


# ─────────────────────────────────────────────
#  Remaining functions – unchanged
# ─────────────────────────────────────────────
def GoogleSearch(Topic):
    search(Topic)
    return True


def Content(Topic):
    def OpenNotepad(File):
        subprocess.Popen(['notepad.exe', File])

    def ContentWriterAI(prompt):
        try:
            client = get_groq_client()
            if not client:
                return FallbackToCohere(prompt)

            groq_messages = [{"role": "system", "content": SystemChatBot}]
            for msg in messages:
                groq_messages.append(msg)
            groq_messages.append({"role": "user", "content": prompt})

            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=groq_messages,
                max_tokens=2048,
                temperature=0.7
            )
            Answer = completion.choices[0].message.content.strip()

        except Exception as e:
            if "429" in str(e):
                try:
                    print(f"Automation Groq 70B Rate Limit, trying 8B...")
                    completion = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=groq_messages,
                        max_tokens=2048,
                        temperature=0.7
                    )
                    Answer = completion.choices[0].message.content.strip()
                except Exception:
                    Answer = FallbackToCohere(prompt)
            else:
                Answer = FallbackToCohere(prompt)

        messages.append({"role": "user", "content": prompt})
        messages.append({"role": "assistant", "content": Answer})
        return Answer

    def FallbackToCohere(prompt):
        try:
            print(f"Automation Groq Failed, using Cohere...")
            co_client = get_cohere_client()
            if not co_client:
                return "I couldn't write the content because AI services are unavailable."

            co_history = [{"role": "SYSTEM", "message": SystemChatBot}]
            for msg in messages:
                role = "USER" if msg["role"] == "user" else "CHATBOT"
                co_history.append({"role": role, "message": msg["content"]})

            response = co_client.chat(
                model="command-r-plus-08-2024",
                message=prompt,
                chat_history=co_history,
                temperature=0.7
            )
            return response.text.strip()
        except Exception as co_err:
            print(f"Automation Fallback failed: {co_err}")
            return "I encountered an error while writing the content."

    Topic = Topic.replace("Content ", "")
    ContentByAI = ContentWriterAI(Topic)

    # Sanitize Topic for filename: remove characters illegal on Windows (\ / : * ? " < > |)
    clean_topic = re.sub(r'[\\/:*?"<>|]', '', Topic).lower().replace(' ', '')
    if not clean_topic:
        clean_topic = "generated_content"
        
    filename = f"Data\\{clean_topic}.txt"
    try:
        with open(filename, "w", encoding="utf-8") as file:
            file.write(ContentByAI)
        OpenNotepad(filename)
    except Exception as e:
        print(f"[Content] Error writing file: {e}")
        return False
    return True


def YouTubeSearch(Topic):
    webbrowser.open(f"https://www.youtube.com/results?search_query={Topic}")
    return True


def PlayYoutube(query):
    playonyt(query)
    return True


def System(command):
    def mute():
        keyboard.press_and_release("volume mute")

    def unmute():
        keyboard.press_and_release("volume mute")

    def volume_up():
        keyboard.press_and_release("volume up")

    def volume_down():
        keyboard.press_and_release("volume down")

    def wifi_on():
        subprocess.run('netsh interface set interface "Wi-Fi" admin=enabled', shell=True)

    def wifi_off():
        subprocess.run('netsh interface set interface "Wi-Fi" admin=disabled', shell=True)

    def airplane_on():
        subprocess.run('start ms-settings:network-airplanemode', shell=True)

    def airplane_off():
        subprocess.run('start ms-settings:network-airplanemode', shell=True)

    def battery_saver_on():
        subprocess.run('powercfg /setdcvalueindex SCHEME_CURRENT SUB_ENERGYSAVER ES_ON_OFF 1', shell=True)
        subprocess.run('powercfg /setactive SCHEME_CURRENT', shell=True)
        subprocess.run('start ms-settings:batterysaver', shell=True)

    def battery_saver_off():
        subprocess.run('powercfg /setdcvalueindex SCHEME_CURRENT SUB_ENERGYSAVER ES_ON_OFF 0', shell=True)
        subprocess.run('powercfg /setactive SCHEME_CURRENT', shell=True)
        subprocess.run('start ms-settings:batterysaver', shell=True)

    def night_light_on():
        subprocess.run('start ms-settings:nightlight', shell=True)

    def night_light_off():
        subprocess.run('start ms-settings:nightlight', shell=True)

    cmd = command.lower().strip()
    if cmd == "mute":
        mute()
    elif cmd == "unmute":
        unmute()
    elif cmd in ("volume up", "volumeup"):
        volume_up()
    elif cmd in ("volume down", "volumedown"):
        volume_down()
    elif "wifi on" in cmd:
        wifi_on()
    elif "wifi off" in cmd:
        wifi_off()
    elif "airplane mode on" in cmd:
        airplane_on()
    elif "airplane mode off" in cmd:
        airplane_off()
    elif "battery saver on" in cmd:
        battery_saver_on()
    elif "battery saver off" in cmd:
        battery_saver_off()
    elif "night light on" in cmd:
        night_light_on()
    elif "night light off" in cmd:
        night_light_off()

    return True


# ─────────────────────────────────────────────
#  TranslateAndExecute  –  now passes raw input
#  directly to OpenApp so URLs work too
# ─────────────────────────────────────────────
def TranslateAndExecute(commands: list[str]) -> str:
    results = []
    for command in commands:
        command = command.strip()
        if not command: continue
        
        print(f"[Automation] Executing: {command}")
        try:
            if command.startswith("open "):
                target = command.removeprefix("open ").strip()
                if target and target not in ("it", "file"):
                    success = OpenApp(target)
                    results.append(f"Opened {target}" if success else f"Failed to open {target}")

            elif command.startswith("close "):
                app_name = command.removeprefix("close ").strip()
                if app_name:
                    success = CloseApp(app_name)
                    results.append(f"Closed {app_name}" if success else f"App {app_name} not found or couldn't be closed")

            elif command.startswith("play "):
                query = command.removeprefix("play ").strip()
                PlayYoutube(query)
                results.append(f"Playing {query} on YouTube")

            elif command.startswith("content "):
                topic = command.removeprefix("content ").strip()
                success = Content(topic)
                results.append(f"Generated content for {topic}" if success else f"Failed to generate content for {topic}")

            elif command.startswith("google search "):
                topic = command.removeprefix("google search ").strip()
                GoogleSearch(topic)
                results.append(f"Searching Google for {topic}")

            elif command.startswith("youtube search "):
                topic = command.removeprefix("youtube search ").strip()
                YouTubeSearch(topic)
                results.append(f"Searching YouTube for {topic}")

            elif command.startswith("system "):
                cmd = command.removeprefix("system ").strip()
                System(cmd)
                results.append(f"System command {cmd} executed")

            elif command.startswith(("general ", "realtime ", "generate ")):
                pass  # Handled elsewhere

            # ── Extra: raw URL passed as a command ──────────────────────────────
            elif _is_url(command):
                OpenApp(command)
                results.append(f"Opened URL: {command}")

            else:
                print(f"[Automation] No handler for: {command}")
                results.append(f"Unknown task: {command}")
        except Exception as e:
            err_msg = f"Error executing '{command}': {e}"
            print(f"[Automation] {err_msg}")
            results.append(err_msg)
            
    return ". ".join(results)


def Automation(commands: list[str]) -> str:
    try:
        return TranslateAndExecute(commands)
    except Exception as e:
        return f"Automation error: {e}"
