import streamlit as st
import asyncio
import uuid
from oauth import handle_callback, ZohoClient
from models import init_db, SessionLocal, User, UserPreference
from agents import create_zoho_graph
from langchain_core.messages import HumanMessage, AIMessage
import json

# Helper function to extract text content from message objects
def extract_text_content(content):
    """Convert message content to plain string."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        # If it's a list of content blocks, extract text
        text_parts = []
        for block in content:
            if isinstance(block, dict) and 'text' in block:
                text_parts.append(block['text'])
            elif isinstance(block, dict) and 'type' in block:
                # For other block types, try to get any text representation
                if block.get('type') == 'text' and 'text' in block:
                    text_parts.append(block['text'])
        return ' '.join(text_parts) if text_parts else json.dumps(content)
    elif isinstance(content, dict):
        return json.dumps(content)
    else:
        return str(content)

st.set_page_config(page_title="Zoho Project Assistant (Mock Mode)", layout="wide")

# Initialize Database
init_db()

# Context window limit - only send last N messages to model to avoid token exhaustion
CONTEXT_WINDOW_SIZE = 6  # Keep only last 6 messages as context (3 user-assistant pairs)

# Auto-login for Mock Mode
if "user_id" not in st.session_state or st.session_state.user_id is None:
    # Automatically create/get a mock user
    st.session_state.user_id = asyncio.run(handle_callback("mock_code"))

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_confirmation" not in st.session_state:
    st.session_state.pending_confirmation = None

# Sidebar
with st.sidebar:
    st.title("Zoho Assistant")
    st.success("Mock Mode Active (No Login Required)")
    # st.info("⚠️ Chat history is NOT saved (session only)")
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# Main Chat Interface
# Chat history is kept only in session state (not persisted)

# Display Chat
for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.write(extract_text_content(msg.content))
    elif isinstance(msg, AIMessage) and msg.content:
        with st.chat_message("assistant"):
            st.write(extract_text_content(msg.content))

# Human-in-the-Loop Confirmation
if st.session_state.pending_confirmation:
    action = st.session_state.pending_confirmation
    with st.chat_message("assistant"):
        st.warning(f"Action Required: Confirm {action['name']}?")
        st.json(action.get('args', {}))
        col1, col2 = st.columns(2)
        if col1.button("Confirm"):
            st.info("Executing...")
            st.session_state.pending_confirmation = None
            st.session_state.messages.append(AIMessage(content=f"Confirmed and executed: {action['name']}"))
            st.rerun()
        if col2.button("Cancel"):
            st.session_state.pending_confirmation = None
            st.session_state.messages.append(AIMessage(content="Action cancelled."))
            st.rerun()

# Chat Input
if prompt := st.chat_input("What can I help you with?"):
    st.session_state.messages.append(HumanMessage(content=prompt))
    st.rerun()

# Process latest message if it's from user
if st.session_state.messages and isinstance(st.session_state.messages[-1], HumanMessage) and not st.session_state.pending_confirmation:
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            graph = create_zoho_graph(st.session_state.user_id, st.session_state.session_id)
            
            # Limit context to last N messages to avoid token exhaustion
            # Full history is displayed, but only recent messages sent to LLM
            context_messages = st.session_state.messages[-CONTEXT_WINDOW_SIZE:] if len(st.session_state.messages) > CONTEXT_WINDOW_SIZE else st.session_state.messages
            
            inputs = {
                "messages": context_messages,  # Only send recent messages to model
                "user_id": st.session_state.user_id, 
                "session_id": st.session_state.session_id,
                "confirmation_required": False,
                "pending_action": {}
            }
            
            try:
                # Stream the response and log to terminal
                async def stream_response():
                    full_response = ""
                    response_msg = None
                    
                    print("\n🔄 Starting stream...", flush=True)
                    
                    async for chunk in graph.astream(inputs):
                        print(f" Chunk: {chunk}", flush=True)  
                        
                        # Extract messages from the chunk
                        for key, value in chunk.items():
                            if "messages" in value:
                                msg = value["messages"][-1]
                                if hasattr(msg, 'content') and msg.content:
                                    content_text = extract_text_content(msg.content)
                                    if content_text:
                                        print(f"✅ Content: {content_text}", flush=True)
                                        full_response = content_text
                                        response_msg = msg
                    
                    print(f"✨ Stream completed. Full response: {full_response}", flush=True)
                    return full_response, response_msg
                
                # Run streaming
                full_response, response_msg = asyncio.run(stream_response())
                
                if full_response and response_msg:
                    st.write(full_response)
                    st.session_state.messages.append(response_msg)
                else:
                    st.write("Processing completed.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
                print(f"❌ Error: {str(e)}", flush=True)
