# This is the file that contains the schemas for the agents, it will be used to validate the data that is sent to the agents.

from pydantic import BaseModel


# ChatBot Agent Schemas
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

