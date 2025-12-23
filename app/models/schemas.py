# This is the file that contains the schemas for the agents, it will be used to validate the data that is sent to the agents.

from datetime import datetime
from typing import Optional , Literal , Dict
from pydantic import BaseModel


class UserContext(BaseModel):
    username: str
    role: str
    department: str
    timestamp: datetime

# ChatBot Agent Schemas
class ChatRequest(BaseModel):
    message: str
    user: UserContext

class ChatResponse(BaseModel):
    response: str

# Tasker Agent Schemas
class TaskerFilters(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    date: Optional[str] = None
    free_text: Optional[str] = None
    sort: str | None = None
    limit: int | None = None


class TaskCommand(BaseModel):
    resource: Literal["work_order", "asset", "pm"]
    action: Literal["view", "list", "create", "update"]
    confidence: Literal["high", "medium", "low"]
    filters: TaskerFilters