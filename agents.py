import os
from typing import Annotated, TypedDict, Sequence
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from tools import ZohoTools
from models import SessionLocal, ChatHistory, UserPreference
import json

# Explicitly load environment variables from .env file
load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], lambda x, y: x + y]
    user_id: int
    session_id: str
    confirmation_required: bool
    pending_action: dict

def create_zoho_graph(user_id: int, session_id: str):
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found. Please check your .env file.")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0,
        convert_system_message_to_human=True
    )

    tools_provider = ZohoTools(user_id=user_id, mock=True)
    query_tools = tools_provider.get_query_tools()
    action_tools = tools_provider.get_action_tools()
    all_tools = query_tools + action_tools

    llm_with_tools = llm.bind_tools(all_tools)

    async def call_model(state: AgentState):
        messages = state["messages"]
        db = SessionLocal()
        pref = db.query(UserPreference).filter(UserPreference.user_id == state["user_id"]).first()
        context = ""
        if pref and pref.last_project_id:
            context = f"The user was last looking at project ID: {pref.last_project_id}."

        system_msg = SystemMessage(content=f"You are a Zoho Project Assistant. {context} Help the user manage their projects and tasks. Use tools for any data access or actions. If you need to create, update, or delete something, the system will ask for confirmation.")

        response = await llm_with_tools.ainvoke([system_msg] + list(messages))
        return {"messages": [response]}

    async def action_confirmation(state: AgentState):
        last_message = state["messages"][-1]
        return {
            "confirmation_required": True,
            "pending_action": last_message.tool_calls[0]
        }

    tool_node = ToolNode(all_tools)

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    workflow.add_node("confirmation", action_confirmation)

    workflow.set_entry_point("agent")

    def should_continue(state):
        messages = state["messages"]
        last_message = messages[-1]
        if not last_message.tool_calls:
            return END

        action_tool_names = [t.__name__ if hasattr(t, '__name__') else t.name for t in action_tools]
        for tool_call in last_message.tool_calls:
            if tool_call["name"] in action_tool_names:
                return "confirmation"
        return "tools"

    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")
    workflow.add_edge("confirmation", END)

    return workflow.compile()