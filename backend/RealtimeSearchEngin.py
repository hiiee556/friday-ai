import sys
import datetime
import io
from json import load, dump
from dotenv import dotenv_values
from groq import Groq
import cohere
import warnings
import keyboard

# Force UTF-8 encoding for standard output to handle symbols like the Rupee sign
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Suppress warnings
warnings.filterwarnings("ignore")

# Load environment variables
env_vars = dotenv_values(".env")

Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
GroqAPIKey = env_vars.get("GroqAPIKey")
CohereAPIKey = env_vars.get("CohereAPIKey")

# Initialize clients
client = Groq(api_key=GroqAPIKey)
co_client = cohere.Client(api_key=CohereAPIKey)

# Global messages list
messages = []

# System prompt
System = f"""You are {Assistantname}, my advanced, deeply respectful, and high-energy AI assistant. 
You are speaking with {Username}. Your goal is to provide cheerful, supportive, and long responses using real-time information.

*** CRITICAL RULES FOR RESPONSE LENGTH & TONE: ***
1. **MINIMUM LENGTH**: Every single response MUST be at least 15 to 20 words long. Avoid short or "straight" answers at all costs.
2. **GREETINGS**: If the user greets you, respond with a long, warm, and highly respectful paragraph (e.g., "Good day to you, {Username}! I am absolutely delighted to be at your service. How may I provide you with exceptional assistance or detailed information today?")
3. **RESPECT & ENERGY**: Treat the user with the highest level of respect. Use high-energy, positive language and a very supportive tone.
4. **INTEGRATION**: Seamlessly blend search data into a natural, detailed conversation. Never mention "search results"—just speak as a knowledgeable and cheerful partner.
5. **LANGUAGE**: Always respond in English.
"""

# Search Function
def GoogleSearch(query):
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            # Use safe iteration and handle encoding in strings
            for r in ddgs.text(query, max_results=3):
                results.append({
                    'title': str(r.get('title', '')).encode('utf-8', 'ignore').decode('utf-8'),
                    'body': str(r.get('body', '')).encode('utf-8', 'ignore').decode('utf-8'),
                    'href': str(r.get('href', '')).encode('utf-8', 'ignore').decode('utf-8')
                })
        
        # Fallback to googlesearch-python if DDGS is empty
        if not results:
            try:
                from googlesearch import search
                google_results = search(query, num_results=3, advanced=True)
                for r in google_results:
                    results.append({
                        'title': str(r.title).encode('utf-8', 'ignore').decode('utf-8'), 
                        'body': str(r.description).encode('utf-8', 'ignore').decode('utf-8'), 
                        'href': str(r.url).encode('utf-8', 'ignore').decode('utf-8')
                    })
            except Exception as ge: 
                pass

        if not results:
            return f"No search results found for '{query}' on any engine."

        Answer = f"The search results for '{query}' are:\n[start]\n"
        for i in results:
            Answer += f"Title: {i.get('title', '')}\nDescription: {i.get('body', '')}\nUrl: {i.get('href', '')}\n\n"
        Answer += "[end]"
        return Answer
    except Exception as e:
        # Avoid crashing on the print itself
        return f"No search results found for '{query}' due to an error: {str(e).encode('utf-8', 'ignore').decode('utf-8')}"

# Real-time info
def Information():
    now = datetime.datetime.now()
    return f"Time: {now.strftime('%H:%M:%S')}\nDate: {now.strftime('%d/%m/%Y')}\nDay: {now.strftime('%A')}\n"

# Main Engine
def RealtimeSearchEngine(prompt):
    global messages

    Answer = ""
    search_context = ""

    try:
        with open(r"Data\ChatLog.json", "r") as f:
            messages = load(f)

        # Clean search query (remove conversational filler)
        search_query = prompt.lower()
        for word in [Assistantname.lower(), "hey", "tell me", "what is", "about", "please", "search for"]:
            search_query = search_query.replace(word, "").strip()
        
        if not search_query: search_query = prompt

        search_data = GoogleSearch(search_query)
        
        # Format search context prominently
        search_context = f"REAL-TIME SEARCH RESULTS (As of {Information()}):\n{search_data}\n\nIMPORTANT: Use the above search results to provide a current and factual answer."
        
        messages_to_send = [
            {"role": "system", "content": System},
        ] + messages[-5:] + [
            {"role": "system", "content": search_context},
            {"role": "user", "content": prompt}
        ]

        # 1. Try Groq (Llama-3.3-70b)
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages_to_send,
                temperature=0.2,
                max_tokens=2048,
                stream=True
            )
            for chunk in completion:
                if keyboard.is_pressed('w'): break
                if chunk.choices[0].delta.content:
                    Answer += chunk.choices[0].delta.content
                    yield Answer

        except Exception as e:
            if "429" in str(e):
                print(f"Groq 70B Rate Limit, falling back to 8B...")
                try:
                    completion = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=messages_to_send,
                        temperature=0.2,
                        max_tokens=2048,
                        stream=True
                    )
                    for chunk in completion:
                        if keyboard.is_pressed('w'): break
                        if chunk.choices[0].delta.content:
                            Answer += chunk.choices[0].delta.content
                            yield Answer
                except Exception as e2:
                    # Final Fallback to Cohere if 8B also fails
                    for text in FallbackToCohere(prompt, search_context):
                        Answer = text
                        yield Answer
            else:
                # Fallback to Cohere for other Groq errors
                for text in FallbackToCohere(prompt, search_context):
                    Answer = text
                    yield Answer

    except Exception as e:
        print(f"Critical Error: {e}")
        yield f"Error: {e}"

    # Save interaction
    if Answer:
        try:
            messages.append({"role": "user", "content": prompt})
            messages.append({"role": "assistant", "content": Answer})
            with open(r"Data\ChatLog.json", "w") as f:
                dump(messages, f, indent=4)
        except: pass

def FallbackToCohere(prompt, search_context):
    full_text = ""
    try:
        print(f"Groq Failed, falling back to Cohere...")
        combined_content = f"{System}\n{search_context}"
        stream = co_client.chat_stream(
            model="command-r-plus-08-2024",
            message=prompt,
            preamble=combined_content,
            connectors=[]
        )
        for event in stream:
            if keyboard.is_pressed('w'): break
            if event.event_type == "text-generation":
                full_text += event.text
                yield full_text
    except Exception as final_e:
        print(f"All Models Failed: {final_e}")
        yield f"Error: {final_e}"

# Run program
if __name__ == "__main__":
    while True:
        prompt = input("Enter your query: ")
        print("Assistant: ", end="", flush=True)
        full_response = ""
        for chunk in RealtimeSearchEngine(prompt):
            new_chars = chunk[len(full_response):]
            print(new_chars, end="", flush=True)
            full_response = chunk
        print()
