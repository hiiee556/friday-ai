import sys
import os
sys.path.append(os.getcwd())

from backend.Model import FirstLayerDMM
from backend.RealtimeSearchEngin import RealtimeSearchEngine
from backend.Chatbot import ChatBot

def QueryModifier(query):
    # Dummy to simulate, let's just return what GUI.py probably does
    from Frontend.GUI import QueryModifier
    return QueryModifier(query)

query = "price of gold today"
print(f"Query: {query}")
decision = FirstLayerDMM(query)
print(f"Decision: {decision}")

for queries in decision:
    if "realtime " in queries or "general " in queries:
        clean_query = queries.replace("realtime ", "").replace("general ", "")
        
        try:
            modified_query = QueryModifier(clean_query)
        except Exception as e:
            print(f"QueryModifier error: {e}")
            modified_query = clean_query
            
        print(f"Clean Query: {clean_query}")
        print(f"Modified Query: {modified_query}")
        
        if "realtime " in queries:
            print("Using RealtimeSearchEngine...")
            AnswerGenerator = RealtimeSearchEngine(modified_query)
        else:
            print("Using ChatBot...")
            AnswerGenerator = ChatBot(modified_query)
            
        full_response = ""
        for chunk in AnswerGenerator:
            new_chars = chunk[len(full_response):]
            print(new_chars, end="", flush=True)
            full_response = chunk
        print()
