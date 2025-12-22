# Policy Engine that decides what to give access or block depending upon the user permissions and context

from enum import Enum
from dataclasses import dataclass # Dataclass is a python class that stores data for us.
from app.models.schemas import UserContext
from app.orchestration.router import Intent
from app.policy.roles import Action, role_can, ROLE_PERMISSIONS


class PolicyDecision(str,Enum):
    ALLOW = "allow"
    BLOCK = "block"
    CLARIFY = "clarify"

@dataclass
class PolicyResult:
    decision: PolicyDecision
    reason: str

def resolve_action(intent: Intent, user_input: str) -> Action:
    text = user_input.lower()

    # --- VIEW actions ---
    if any(word in text for word in ["view", "list", "show", "get", "status"]):
        return Action.VIEW_WORK_ORDER

    # --- CREATE actions ---
    if any(word in text for word in ["create", "open", "add"]):
        return Action.CREATE_WORK_ORDER

    # --- UPDATE actions ---
    if any(word in text for word in ["update", "modify", "change"]):
        return Action.UPDATE_WORK_ORDER

    # --- CLOSE actions ---
    if any(word in text for word in ["close", "complete"]):
        return Action.CLOSE_WORK_ORDER

    # --- ANALYZE ---
    if intent == Intent.ANALYZE:
        return Action.ANALYZE_REPORTS

    # Default safe action
    return Action.CHAT


def evaluate_policy(intent: Intent, user_context: UserContext, user_input: str) -> PolicyResult:
    
    role = user_context.role.lower()
    action = resolve_action(intent, user_input)

    if intent == Intent.CHAT:
        return PolicyResult(
            decision= PolicyDecision.ALLOW,
            reason="Chat allowed"
        )
    
    if not role_can(role, action):
        return PolicyResult(
            decision=PolicyDecision.BLOCK,
            reason="You dont have permission to execute this."
        )
    
    return PolicyResult(
        decision= PolicyDecision.BLOCK,
        reason="Feature not implemented yet"
    )

