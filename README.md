# AI-Powered Zoho Project Assistant

A conversational AI chatbot that connects to Zoho Projects via its REST API, built with Streamlit and LangGraph.

## Features
- **User-Based OAuth 2.0**: Individual authentication with Zoho accounts.
- **Multi-Agent Architecture**: Separate agents for queries and actions coordinated via LangGraph.
- **8 Core Tools**: List projects, tasks, members, create/update/delete tasks, and more.
- **Human-in-the-Loop**: All write operations require explicit user confirmation.
- **Memory**: Persistent chat history and user preferences using SQLite.

## Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd zoho_assistant
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Create a `.env` file based on `.env.example`:
   - `ZOHO_CLIENT_ID`: Your Zoho Client ID
   - `ZOHO_CLIENT_SECRET`: Your Zoho Client Secret
   - `ZOHO_REDIRECT_URI`: Usually `http://localhost:8501`
   - `OPENAI_API_KEY`: Your OpenAI API key

4. **Run the Application**:
   ```bash
   streamlit run app.py
   ```

## Architecture Overview
- **`app.py`**: Streamlit frontend and main event loop.
- **`agents.py`**: LangGraph definition for the multi-agent system.
- **`tools.py`**: Implementation of the 8 Zoho API tools.
- **`oauth.py`**: Zoho OAuth 2.0 flow and API client.
- **`models.py`**: Database models for users, history, and preferences.

## Limitations
- This is a demonstration project.
- Long-term memory is currently limited to last project ID and chat history.
- Multi-portal support is not implemented (uses the first available portal).
