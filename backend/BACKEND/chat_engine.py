import os
from dotenv import load_dotenv
from langchain import OpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError('OPENAI_API_KEY not found in environment variables')

# Initialize the LLM
llm = OpenAI(openai_api_key=OPENAI_API_KEY, temperature=0.7)

# Store per-user memory sessions
session_memory_map = {}

def get_response(session_id: str, user_query: str) -> str:
    if session_id not in session_memory_map:
        memory = ConversationBufferMemory()
        session_memory_map[session_id] = ConversationChain(llm=llm, memory=memory, verbose=True)
    
    conversation = session_memory_map[session_id]
    return conversation.predict(input=user_query)
