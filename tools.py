from langchain_core.tools import tool
from oauth import ZohoClient
import json


class ZohoTools:
    def __init__(self, user_id, mock=True):
        self.client = ZohoClient(user_id, mock=mock)

    def get_query_tools(self):
        return [
            make_list_projects(self.client),
            make_list_tasks(self.client),
            make_get_task_details(self.client),
            make_list_project_members(self.client),
            make_get_task_utilisation(self.client),
        ]

    def get_action_tools(self):
        return [
            make_create_task(self.client),
            make_update_task(self.client),
            make_delete_task(self.client),
        ]


# --- Factory functions that return bound @tool functions ---

def make_list_projects(client: ZohoClient):
    @tool
    async def list_projects() -> dict:
        """Fetch all projects for the authenticated user."""
        return await client.request("GET", "projects/")
    return list_projects


def make_list_tasks(client: ZohoClient):
    @tool
    async def list_tasks(project_id: str, status: str = None, assignee: str = None) -> dict:
        """List tasks for a project with optional filters. project_id is the string ID of the project."""
        params = {}
        if status:
            params["status"] = status
        if assignee:
            params["assignee"] = assignee
        return await client.request("GET", f"projects/{project_id}/tasks/", params=params)
    return list_tasks


def make_get_task_details(client: ZohoClient):
    @tool
    async def get_task_details(project_id: str, task_id: str) -> dict:
        """Fetch full details of a single task by ID."""
        return await client.request("GET", f"projects/{project_id}/tasks/{task_id}/")
    return get_task_details


def make_list_project_members(client: ZohoClient):
    @tool
    async def list_project_members(project_id: str) -> dict:
        """Get all members of a project with their roles."""
        return await client.request("GET", f"projects/{project_id}/users/")
    return list_project_members


def make_get_task_utilisation(client: ZohoClient):
    @tool
    async def get_task_utilisation(project_id: str) -> dict:
        """Summarise task load per member across a project."""
        tasks_resp = await client.request("GET", f"projects/{project_id}/tasks/")
        tasks = tasks_resp.get("tasks", [])
        summary = {}
        for task in tasks:
            owners = task.get("details", {}).get("owners", [])
            assignee = owners[0].get("name", "Unassigned") if owners else "Unassigned"
            summary[assignee] = summary.get(assignee, 0) + 1
        return summary
    return get_task_utilisation


def make_create_task(client: ZohoClient):
    @tool
    async def create_task(project_id: str, name: str, person_id: str = None, end_date: str = None, priority: str = None) -> dict:
        """Create a new task in a given project. REQUIRES CONFIRMATION."""
        data = {"name": name}
        if person_id:
            data["person_id"] = person_id
        if end_date:
            data["end_date"] = end_date
        if priority:
            data["priority"] = priority
        return await client.request("POST", f"projects/{project_id}/tasks/", json_data=data)
    return create_task


def make_update_task(client: ZohoClient):
    @tool
    async def update_task(project_id: str, task_id: str, name: str = None, status: str = None, person_id: str = None) -> dict:
        """Update task details. REQUIRES CONFIRMATION."""
        data = {}
        if name:
            data["name"] = name
        if status:
            data["status"] = status
        if person_id:
            data["person_id"] = person_id
        return await client.request("POST", f"projects/{project_id}/tasks/{task_id}/", json_data=data)
    return update_task


def make_delete_task(client: ZohoClient):
    @tool
    async def delete_task(project_id: str, task_id: str) -> dict:
        """Delete a task. REQUIRES CONFIRMATION."""
        return await client.request("DELETE", f"projects/{project_id}/tasks/{task_id}/")
    return delete_task