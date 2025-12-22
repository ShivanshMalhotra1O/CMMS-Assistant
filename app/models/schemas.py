# This is the file that contains the schemas for the agents, it will be used to validate the data that is sent to the agents.

from datetime import datetime
from typing import Optional
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
class TaskCommand(BaseModel):
    work_order_id: Optional[str] = None
    asset_id: Optional[str] = None
    action: str | None = None          
    description: Optional[str]
    priority: Optional[str]