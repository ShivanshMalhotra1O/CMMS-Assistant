# Policy Engine that decides what to give access or block depending upon the user permissions and context

from enum import Enum
from dataclasses import dataclass

from app.models.schemas import UserContext
from app.orchestration.router import Intent
from app.policy.roles import Action
from app.policy.roles import role_can


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    CLARIFY = "clarify"

class Resource(str, Enum):
    NONE = "none"

    WORK_ORDER = "work_order"
    ASSET = "asset"
    PM = "pm"


@dataclass
class PolicyResult:
    decision: PolicyDecision
    reason: str


# -------------------------
# ACTION RESOLUTION
# -------------------------
def resolve_action(intent: Intent, user_input: str) -> Action:
    text = user_input.lower()

    if intent == Intent.CHAT:
        return Action.CHAT

    if any(word in text for word in ["view", "list", "show", "get", "status"]):
        return Action.VIEW

    if any(word in text for word in ["create", "open", "add"]):
        return Action.CREATE

    if any(word in text for word in ["update", "modify", "change", "close"]):
        return Action.UPDATE

    if any(word in text for word in ["delete", "remove", "cancel"]):
        return Action.DELETE

    if intent == Intent.ANALYZE:
        return Action.ANALYZE

    return Action.CHAT


# -------------------------
# RESOURCE RESOLUTION
# -------------------------
def resolve_resource(user_input: str) -> Resource:
    text = user_input.lower()

    if any(w in text for w in ["work order", "wo", "job"]):
        return Resource.WORK_ORDER

    if any(w in text for w in ["asset", "equipment", "machine"]):
        return Resource.ASSET

    if any(w in text for w in ["pm", "preventive", "maintenance plan"]):
        return Resource.PM

    return Resource.NONE


# -------------------------
# POLICY EVALUATION
# -------------------------
def evaluate_policy(
    intent: Intent,
    user_context: UserContext,
    user_input: str
) -> PolicyResult:

    role = user_context.role.lower()
    action = resolve_action(intent, user_input)
    resource = resolve_resource(user_input)

    # Debug logs
    print("DEBUG → intent:", intent)
    print("DEBUG → action:", action)
    print("DEBUG → resource:", resource)
    print("DEBUG → role:", role)

    # Chat is always allowed
    if action == Action.CHAT:
        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="Chat allowed"
        )

    # If no resource is detected, ask user to clarify
    if resource == Resource.NONE:
        return PolicyResult(
            decision=PolicyDecision.CLARIFY,
            reason="Please specify what you want to act on."
        )

    # Role-based permission check (action-level for now)
    if not role_can(role, action):
        return PolicyResult(
            decision=PolicyDecision.BLOCK,
            reason="You do not have permission to perform this action."
        )

    # READ actions are allowed (for supported resources)
    if action == Action.VIEW:
        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="Read access allowed."
        )

    # WRITE / DELETE / ANALYZE not implemented yet
    return PolicyResult(
        decision=PolicyDecision.BLOCK,
        reason="Feature not implemented yet."
    )
