import os
import asyncio
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk.sessions import DatabaseSessionService
from google.adk.runners import Runner
from google.genai import types
from assistant.agent import chat_agent

# Load environment variables
load_dotenv()

# Initialize ADK components with SQLite for persistence and monitoring
session_service = DatabaseSessionService(
    db_url="sqlite:///adk_sessions.db"
)
runner = Runner(
    app_name='assistant',
    agent=chat_agent,
    session_service=session_service
)

# Create FastAPI app
app = FastAPI(title="LitRealms Chat API", description="Chat API powered by Google ADK")

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None  # Optional session ID

class ChatResponse(BaseModel):
    response: str
    session_id: str  # Return session ID to frontend

@app.get("/")
async def root():
    return {"message": "Chat API with Google ADK is running!"}

@app.get("/health")
async def health():
    return {"status": "healthy", "agent": chat_agent.name}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Create user ID (in production, get from auth/request)
        user_id = "user"  # In production, extract from authentication
        
        # Create proper Content object from user message
        message = types.Content(
            role='user',
            parts=[types.Part(text=request.message)]
        )
        
        # ALWAYS have a session_id (generate if not provided)
        session_id = request.session_id or str(uuid.uuid4())
        
        print(f"Processing message with session_id: {session_id}")
        
        # Get or create session (both methods are async)
        session = await session_service.get_session(
            app_name='assistant',
            user_id=user_id,
            session_id=session_id
        )
        if not session:
            session = await session_service.create_session(
                app_name='assistant',
                user_id=user_id,
                session_id=session_id,
                state={}
            )
            print(f"Created new session: {session_id}")
        else:
            print(f"Found existing session: {session_id}")
        
        # Now Runner can find the session
        response_parts = []
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,  # ← ALWAYS required
            new_message=message
        ):
            # Extract response content
            if hasattr(event, 'content') and event.content:
                if hasattr(event.content, 'parts') and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text'):
                            response_parts.append(part.text)
                else:
                    response_parts.append(str(event.content))
        
        print(f"Successfully processed. Returning session_id: {session_id}")
        
        # Combine response parts
        response_text = ''.join(response_parts) if response_parts else "I'm sorry, I couldn't generate a response."
        
        return ChatResponse(response=response_text, session_id=session_id)
    except Exception as e:
        import traceback
        error_msg = str(e)
        full_traceback = traceback.format_exc()
        print(f"Error processing chat: {error_msg}")
        print(f"Traceback: {full_traceback}")
        
        # Include more detailed error info in response
        detail = {
            "error": error_msg,
            "type": type(e).__name__,
            "traceback": full_traceback
        }
        raise HTTPException(status_code=500, detail=detail)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "localhost")
    uvicorn.run(app, host=host, port=port)