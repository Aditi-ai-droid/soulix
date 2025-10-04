import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel

# Import your modules
from chat_engine import get_response
from crisis import contains_crisis_keywords, SAFETY_MESSAGE
from logger import log_chat
from doc_engine import query_documents

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for request
class ChatRequest(BaseModel):
    session_id: str
    message: str

# Test route
@app.get("/")
def read_root():
    return {"message": "Hello World"}

# Chat endpoint
@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    user_input = request.message
    session_id = request.session_id
    
    # Check crisis keywords
    if contains_crisis_keywords(user_input):
        log_chat(session_id=session_id, query=user_input, response=SAFETY_MESSAGE, is_crisis=True)
        return {"response": SAFETY_MESSAGE}
    
    # Query documents if needed
    doc_result = query_documents(user_input)
    
    # Get AI response
    response = get_response(session_id=session_id, user_query=user_input)
    
    # Log the chat
    log_chat(session_id=session_id, query=user_input, response=response, is_crisis=False)
    
    return {"response": response}
