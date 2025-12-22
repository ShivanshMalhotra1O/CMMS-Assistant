from bson import ObjectId
from datetime import datetime


def serialize(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return value


def format_from_registry(resource_def: dict, action: str, record: dict) -> str:
    response_def = resource_def["actions"][action].get("response")

    if not response_def:
        return "Action completed successfully."

    title = response_def.get("title", "Result")
    fields = response_def.get("fields", {})

    lines = [title, "-" * len(title)]

    for field, label in fields.items():
        value = serialize(record.get(field))
        lines.append(f"{label}: {value}")

    return "\n".join(lines)
