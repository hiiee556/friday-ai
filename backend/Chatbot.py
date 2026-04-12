from groq import Groq
import cohere
from json import load, dump
import datetime
from dotenv import dotenv_values
import keyboard

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

# System message
System = f"""
Hello, I am {Username}, 
You are {Assistantname}, my advanced, respectful, and high-energy AI assistant. 

*** CRITICAL RULES FOR RESPONSE LENGTH & TONE: ***
1. **MINIMUM LENGTH**: Every single response you give MUST be at least 15 to 20 words long. NEVER give short or one-sentence answers.
2. **GREETINGS**: If the user says "Hello" or "Hi", do NOT just say "Hello". Instead, give a long, cheerful, and respectful greeting (e.g., "Hello there, {Username}! It is an absolute pleasure to see you today. I hope you're having a wonderful morning—how can I assist you with your tasks?")
3. **TONE**: Be incredibly cheerful, supportive, and respectful. Use positive adjectives and a high-energy vibe.
4. **COMPREHENSIVENESS**: If a question can be explained in more detail, ALWAYS do so. Explain the 'why' and 'how' to ensure the response is long and helpful.
5. **RESTRICTIONS**: Reply in English only. Do not mention your training data or AI nature unless asked.
"""

SystemChatBot = [
    {"role": "system", "content": System}
]

# Real-time date & time
def RealtimeInformation():
    now = datetime.datetime.now()
    return f"Day: {now.strftime('%A')}\nDate: {now.strftime('%d/%m/%Y')}\nTime: {now.strftime('%H:%M:%S')}\n"

# Main chatbot function
def ChatBot(Query):
    global messages

    try:
        with open("Data\\ChatLog.json", "r") as f:
            messages = load(f)

        messages_to_send = SystemChatBot + [
            {"role": "system", "content": RealtimeInformation()}
        ] + messages[-5:] + [{"role": "user", "content": Query}]

        Answer = ""

        # 1. Try Groq (Llama-3.3-70b)
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages_to_send,
                max_tokens=1024,
                temperature=0.7,
                stream=True
            )
            for chunk in completion:
                if keyboard.is_pressed('w'): break
                if chunk.choices[0].delta.content:
                    Answer += chunk.choices[0].delta.content
                    yield Answer

        # 2. Fallback to Groq (Llama-3.1-8b) if 429
        except Exception as e:
            if "429" in str(e):
                print(f"Groq 70B Rate Limit, falling back to 8B...")
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=messages_to_send,
                    max_tokens=1024,
                    temperature=0.7,
                    stream=True
                )
                for chunk in completion:
                    if keyboard.is_pressed('w'): break
                    if chunk.choices[0].delta.content:
                        Answer += chunk.choices[0].delta.content
                        yield Answer
            else: raise e

    except Exception as e:
        # 3. Final Fallback to Cohere
        try:
            print(f"Groq Failed, falling back to Cohere...")
            stream = co_client.chat_stream(
                model="command-r-plus-08-2024",
                message=Query,
                preamble=System + "\n" + RealtimeInformation(),
                connectors=[]
            )
            Answer = ""
            for event in stream:
                if keyboard.is_pressed('w'): break
                if event.event_type == "text-generation":
                    Answer += event.text
                    yield Answer
        except Exception as final_e:
            print(f"All Models Failed: {final_e}")
            yield f"Error: {final_e}"

    # Save interaction
    if Answer:
        try:
            messages.append({"role": "user", "content": Query})
            messages.append({"role": "assistant", "content": Answer})
            with open("Data\\ChatLog.json", "w") as f:
                dump(messages, f, indent=4)
        except: pass


# Run program
if __name__ == "__main__":
    while True:
        user_input = input("Enter Your Question: ")
        print("Assistant: ", end="", flush=True)
        full_response = ""
        for chunk in ChatBot(user_input):
            new_chars = chunk[len(full_response):]
            print(new_chars, end="", flush=True)
            full_response = chunk
        print()