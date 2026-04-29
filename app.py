import streamlit as st
import asyncio
import uuid
from oauth import handle_callback, ZohoClient
from models import init_db, SessionLocal, User, ChatHistory, UserPreference
from agents import create_zoho_graph
from langchain_core.messages import HumanMessage, AIMessage
import json

st.set_page_config(page_title="Zoho Project Assistant (Mock Mode)", layout="wide")

# Initialize Database
init_db()

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
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        db = SessionLocal()
        db.query(ChatHistory).filter(ChatHistory.user_id == st.session_state.user_id).delete()
        db.commit()
        st.rerun()

# Main Chat Interface
# Load history from DB if empty
if not st.session_state.messages:
    db = SessionLocal()
    history = db.query(ChatHistory).filter(
        ChatHistory.user_id == st.session_state.user_id
    ).order_by(ChatHistory.timestamp.asc()).all()
    for h in history:
        if h.role == "user":
            st.session_state.messages.append(HumanMessage(content=h.content))
        else:
            st.session_state.messages.append(AIMessage(content=h.content))

# Display Chat
for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.write(msg.content)
    elif isinstance(msg, AIMessage) and msg.content:
        with st.chat_message("assistant"):
            st.write(msg.content)

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
    
    # Save to DB
    db = SessionLocal()
    db.add(ChatHistory(user_id=st.session_state.user_id, session_id=st.session_state.session_id, role="user", content=prompt))
    db.commit()
    st.rerun()

# Process latest message if it's from user
if st.session_state.messages and isinstance(st.session_state.messages[-1], HumanMessage) and not st.session_state.pending_confirmation:
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            graph = create_zoho_graph(st.session_state.user_id, st.session_state.session_id)
            inputs = {
                "messages": st.session_state.messages, 
                "user_id": st.session_state.user_id, 
                "session_id": st.session_state.session_id,
                "confirmation_required": False,
                "pending_action": {}
            }
            
            try:
                result = asyncio.run(graph.ainvoke(inputs))
                
                if result.get("confirmation_required"):
                    st.session_state.pending_confirmation = result["pending_action"]
                    st.session_state.messages.append(result["messages"][-1])
                    st.rerun()
                else:
                    response_msg = result["messages"][-1]
                    if response_msg.content:
                        st.write(response_msg.content)
                        st.session_state.messages.append(response_msg)
                        
                        # Save to DB
                        db = SessionLocal()
                        db.add(ChatHistory(user_id=st.session_state.user_id, session_id=st.session_state.session_id, role="assistant", content=response_msg.content))
                        db.commit()
                    else:
                        st.write("Processing completed.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
