from pymongo.database import Database
from bson import ObjectId
from datetime import datetime

from app.policy.roles import Action
from app.policy.engine import Resource
from app.query.builder import build_query

from app.query.mongo_executer import execute_mongo


# -------------------------
# Helpers
# -------------------------
def serialize_value(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if value is None:
        return "-"
    return value


def format_from_registry(resource_def: dict, action_key: str, record: dict) -> str:
    action_def = resource_def.get("actions", {}).get(action_key, {})
    response_def = action_def.get("response")

    if not response_def:
        return "✔ Record retrieved."

    title = response_def.get("title", "Result")
    fields = response_def.get("fields", {})

    lines = [title, "-" * len(title)]

    for field, label in fields.items():
        value = serialize_value(record.get(field))
        lines.append(f"{label}: {value}")

    return "\n".join(lines)


# -------------------------
# Executor (UPDATED)
# -------------------------
def execute_action(
    db: Database,
    registry: dict,
    action: Action,
    resource: Resource,
    params: dict
) -> str:

    resource_key = resource.value
    action_key = action.value

    # -------------------------
    # Validate registry
    # -------------------------
    if resource_key not in registry:
        return "❌ Unsupported resource."

    resource_def = registry[resource_key]
    actions_def = resource_def.get("actions", {})

    if action_key not in actions_def:
        return "❌ This action is not supported for this resource."

    action_def = actions_def[action_key]

    # -------------------------
    # Build abstract query (LLM-friendly)
    # -------------------------
    query = build_query(
        registry=registry,
        # action=action.value,
        resource=resource,
        params=params
    )

    print(query)
    # -------------------------
    # Execute query
    # -------------------------
    result = execute_mongo(db, query)

    if not result:
        return "❌ No records found."

    # -------------------------
    # Format response
    # -------------------------
   
    title = action_def.get(
        "list_title",
        resource_def.get("list_title", f"{resource_key.title()} List")
    )

    response = [title, "-" * len(title)]

    for record in result:
        response.append(
            format_from_registry(
                resource_def=resource_def,
                action_key=action_key,
                
                record=record
            )
        )
        response.append("")

    return "\n".join(response).strip()
