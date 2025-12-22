"""
This module defines role-based permissions for the system.

- Intent represents what the user wants to do (derived from natural language).
- Action represents what the system is capable of doing (system-level operations).

Roles are mapped to allowed Actions, not Intents.

The Policy Engine is responsible for:
1. Interpreting user intent
2. Mapping intent to one or more system Actions
3. Verifying whether the user's role is allowed to perform those Actions
4. Allowing or blocking the request accordingly
"""

from enum import Enum

class Action(str, Enum):
    CHAT = 'chat'
    VIEW = 'view'
    CREATE = "create"
    UPDATE = "update"
    ANALYZE = "analyze"

ROLE_PERMISSIONS = {
    "viewer": {
        Action.CHAT,
        Action.VIEW,
    },

    "technician": {
        Action.CHAT,
        Action.VIEW,
        Action.CREATE,
        Action.UPDATE,
    },

    "manager": {
        Action.CHAT,
        Action.VIEW,
        Action.CREATE,
        Action.UPDATE,
        Action.ANALYZE,
    },

    "admin": {
        Action.CHAT,
        Action.VIEW,
        Action.CREATE,
        Action.UPDATE,
        Action.ANALYZE,
    },
}


def role_can(role: str, action : Action) -> bool:
    role = role.lower()
    return action in ROLE_PERMISSIONS.get(role,set())  # It will get all the actions that are associated with the role, if there is no action then it will return an empty set.
