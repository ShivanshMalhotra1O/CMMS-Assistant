# Policy Engine that decides access based on user permissions and context

from enum import Enum
from dataclasses import dataclass

from app.models.schemas import UserContext
from app.orchestration.router import Intent
from app.policy.roles import Action, role_can


# -------------------------
# DECISIONS
# -------------------------
class PolicyDecision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    CLARIFY = "clarify"


# -------------------------
# RESOURCES
# -------------------------
class Resource(str, Enum):
    NONE = "none"
    WORK_ORDER = "work_order"
    ASSET = "asset"
    PM = "pm"


# -------------------------
# RESULT MODEL
# -------------------------
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

    if any(w in text for w in ["view", "show", "get", "details","list", "all", "open", "pending", "created"]):
        return Action.VIEW

    
    if any(w in text for w in ["create", "add", "open new"]):
        return Action.CREATE

    if any(w in text for w in ["update", "modify", "change", "close"]):
        return Action.UPDATE

    # if any(w in text for w in ["delete", "remove", "cancel"]):
    #     return Action.DELETE

    return Action.CHAT


# -------------------------
# RESOURCE RESOLUTION (fallback only)
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

    # Resolve action & resource
    action = resolve_action(intent, user_input)
    resource = resolve_resource(user_input)

    # Debug logs (safe to remove later)
    print("DEBUG → intent:", intent)
    print("DEBUG → action:", action)
    print("DEBUG → resource:", resource)
    print("DEBUG → role:", role)

    # -------------------------
    # CHAT is always allowed
    # -------------------------
    if action == Action.CHAT:
        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="Chat allowed."
        )

    # -------------------------
    # Resource missing → clarify
    # -------------------------
    if resource == Resource.NONE:
        return PolicyResult(
            decision=PolicyDecision.CLARIFY,
            reason="Please specify what you want to act on."
        )

    # -------------------------
    # Role-based permission
    # -------------------------
    if not role_can(role, action):
        return PolicyResult(
            decision=PolicyDecision.BLOCK,
            reason="You do not have permission to perform this action."
        )

    # -------------------------
    # READ actions allowed
    # -------------------------
    if action in {Action.VIEW}:
        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="Read access allowed."
        )

    # -------------------------
    # WRITE actions (future)
    # -------------------------
    return PolicyResult(
        decision=PolicyDecision.BLOCK,
        reason="This feature is not implemented yet."
    )
