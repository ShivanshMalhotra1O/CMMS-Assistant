from pymongo.database import Database
from bson import ObjectId
from datetime import datetime

from app.policy.roles import Action
from app.policy.engine import Resource


# -------------------------
# Helpers
# -------------------------
def serialize_value(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return value


def format_from_registry(resource_def: dict, action_key: str, record: dict) -> str:
    """
    Generic formatter driven entirely by the registry.
    """

    response_def = (
        resource_def
        .get("actions", {})
        .get(action_key, {})
        .get("response")
    )

    if not response_def:
        return "Action completed successfully."

    title = response_def.get("title", "Result")
    fields = response_def.get("fields", {})

    lines = [title, "-" * len(title)]

    for field, label in fields.items():
        value = serialize_value(record.get(field))
        lines.append(f"{label}: {value}")

    return "\n".join(lines)


# -------------------------
# Executor
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

    # Validate resource
    if resource_key not in registry:
        return "Unsupported resource."

    resource_def = registry[resource_key]
    actions_def = resource_def.get("actions", {})

    # Validate action
    if action_key not in actions_def:
        return "This action is not supported for this resource."

    action_def = actions_def[action_key]

    # Validate required params
    for param in action_def.get("required_params", []):
        if param not in params or not params[param]:
            return f"Missing required parameter: {param}"

    collection = db[resource_def["collection"]]

    # Build query
    query = {}
    if "query" in action_def:
        field = action_def["query"]["field"]
        param_name = action_def["required_params"][0]
        query[field] = params[param_name]

    # -------------------------
    # Execute queries
    # -------------------------
    if action_def["query_type"] == "single":
        record = collection.find_one(query)

        if not record:
            return "Record not found."

        return format_from_registry(
            resource_def=resource_def,
            action_key=action_key,
            record=record
        )

    if action_def["query_type"] == "list":
        records = list(collection.find(query))

        if not records:
            return "No records found."

        title = resource_def.get("list_title", "Results")
        response = f"{title}\n" + "-" * len(title) + "\n"

        for r in records[:10]:  # safety limit
            response += format_from_registry(
                resource_def=resource_def,
                action_key=action_key,
                record=r
            )
            response += "\n\n"

        return response.strip()

    return "Unsupported query type."
