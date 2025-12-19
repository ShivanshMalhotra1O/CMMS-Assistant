# Policy Engine that decides what to give access or block depending upon the user permissions and context

from enum import Enum
from dataclasses import dataclass # Dataclass is a python class that stores data for us.
from app.models.schemas import UserContext
from app.orchestration.router import Intent


class PolicyDecision(str,Enum):
    ALLOW = "allow"
    BLOCK = "block"
    CLARIFY = "clarify"

@dataclass
class PolicyResult:
    decision: PolicyDecision
    reason: str

def evaluate_policy(intent: Intent, user_context: UserContext, user_input: str) -> PolicyResult:
    
    role = user_context.role.lower()

    if intent == Intent.CHAT:
        return PolicyResult(
            decision= PolicyDecision.ALLOW,
            reason="Chat allowed"
        )
    
    if intent == Intent.EXECUTE_TASK:
        if role not in ['manager','admin','technician']:
            return PolicyResult(
                decision=PolicyDecision.BLOCK,
                reason="You dont have permission to execute this."
            )
        
        return PolicyResult(
            decision= PolicyDecision.BLOCK,
            reason="Feature not implemented yet"
        )

    if intent == Intent.ANALYZE:
        if role not in ['manager','admin','technician']:
            return PolicyResult(
                decision=PolicyDecision.BLOCK,
                reason="You dont have permission to execute this."
            )
        
        return PolicyResult(
            decision= PolicyDecision.BLOCK,
            reason="Feature not implemented yet"
        )
    
    return PolicyResult(
        decision=PolicyDecision.BLOCK,
        reason="Unhandled intent",
    )