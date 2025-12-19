# This is the file that contains the schemas for the agents, it will be used to validate the data that is sent to the agents.

from datetime import datetime
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

