import os
import httpx
import datetime
from dotenv import load_dotenv
from models import SessionLocal, User

load_dotenv()

CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ZOHO_REDIRECT_URI")
ACCOUNTS_URL = os.getenv("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.com")
BASE_URL = os.getenv("ZOHO_BASE_URL", "https://projectsapi.zoho.com/restapi")

class ZohoClient:
    def __init__(self, user_id, mock=True):
        self.user_id = user_id
        self.db = SessionLocal()
        self.user = self.db.query(User).filter(User.id == user_id).first()
        self.portal_id = "mock_portal_123"
        self.mock = mock

    async def get_valid_token(self):
        if self.mock:
            return "mock_token"
        if not self.user:
            return None
        if self.user.token_expiry < datetime.datetime.utcnow():
            await self.refresh_access_token()
        return self.user.access_token

    async def refresh_access_token(self):
        if self.mock: return
        # ... real refresh logic ...
        pass

    async def request(self, method, endpoint, params=None, json_data=None):
        if self.mock:
            return await self.mock_request(method, endpoint, params, json_data)
        
        token = await self.get_valid_token()
        headers = {"Authorization": f"Zoho-oauthtoken {token}"}
        if not self.portal_id:
            self.portal_id = await self.get_portal_id()
        url = f"{BASE_URL}/portal/{self.portal_id}/{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers, params=params, json=json_data)
            return response.json()

    async def mock_request(self, method, endpoint, params=None, json_data=None):
        """Mocked responses for testing without a real Zoho account."""
        if "projects/" in endpoint and method == "GET" and endpoint.endswith("projects/"):
            return {"projects": [{"id_string": "p1", "name": "API Integration Project"}, {"id_string": "p2", "name": "Mobile App Development"}]}
        
        if "tasks/" in endpoint and method == "GET":
            return {"tasks": [
                {"id_string": "t1", "name": "Design Database Schema", "details": {"owners": [{"name": "Alice"}]}},
                {"id_string": "t2", "name": "Implement OAuth Flow", "details": {"owners": [{"name": "Bob"}]}},
                {"id_string": "t3", "name": "Setup Streamlit UI", "details": {"owners": [{"name": "Alice"}]}}
            ]}
        
        if "users/" in endpoint:
            return {"users": [{"id": "u1", "name": "Alice", "role": "Admin"}, {"id": "u2", "name": "Bob", "role": "Developer"}]}
        
        if method == "POST":
            return {"status": "success", "message": "Operation completed (Mock)"}
        
        if method == "DELETE":
            return {"status": "success", "message": "Deleted (Mock)"}

        return {"data": "Mock data for " + endpoint}

    async def get_portal_id(self):
        if self.mock: return "mock_portal"
        # ... real logic ...
        return "portal_id"

def get_auth_url():
    return "#mock-login"

async def handle_callback(code):
    # For mock, we just create a mock user
    db = SessionLocal()
    user = db.query(User).filter(User.zoho_user_id == "mock_user").first()
    if not user:
        user = User(zoho_user_id="mock_user", access_token="mock", refresh_token="mock", token_expiry=datetime.datetime.utcnow() + datetime.timedelta(days=1))
        db.add(user)
        db.commit()
        db.refresh(user)
    return user.id
