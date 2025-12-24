from pymongo.database import Database

from app.policy.roles import Action
from app.policy.engine import Resource
from app.query.builder import build_query
from app.query.mongo_executer import execute_mongo
from app.utils.formatters import format_from_registry  


# -------------------------
# Executor (FINAL)
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
    # Build query plan
    # -------------------------
    query = build_query(
        registry=registry,
        resource=resource,
        params=params
    )

    print("DEBUG → QueryPlan:", query)

    # -------------------------
    # Execute query
    # -------------------------
    result = execute_mongo(
        db=db,
        query=query,
        registry=registry,
        resource=resource_key
    )

    print("DEBUG → Result:", result)

    if not result:
        return "❌ No records found."

    # -------------------------
    # Format response
    # -------------------------
    title = action_def.get(
        "list_title",
        f"{resource_key.replace('_', ' ').title()} List"
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
