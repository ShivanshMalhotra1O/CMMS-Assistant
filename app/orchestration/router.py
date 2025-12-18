# Here we define the router for the orchestration layer which will use the intents to route the request to the appropriate agent.

from enum import Enum
from typing import List
from app.core.intent_keywords import Task_Keywords,Analyze_Keywords


class Intent(str, Enum):
    CHAT = "chat"
    EXECUTE_TASK = "execute_task"
    ANALYZE = "analyze"


def route_intent(user_input: str) -> Intent:
  
    text = user_input.lower()

    for keyword in Task_Keywords:
        if keyword in text:
            return Intent.EXECUTE_TASK
    
    for keyword in Analyze_Keywords:
        if keyword in text:
            return Intent.ANALYZE
    
    return Intent.CHAT