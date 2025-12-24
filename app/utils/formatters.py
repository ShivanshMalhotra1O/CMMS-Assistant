from bson import ObjectId
from datetime import datetime


# -------------------------
# Safe nested field resolver
# -------------------------
def get_nested_value(data: dict, path: str):
    if not isinstance(data, dict) or not path:
        return None

    keys = path.split(".")
    value = data

    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None

    return value


# -------------------------
# Serializer (UI safe)
# -------------------------
def serialize(value):
    if value is None:
        return "-"

    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")

    if isinstance(value, list):
        # join list values cleanly
        return ", ".join(str(serialize(v)) for v in value) or "-"

    if isinstance(value, dict):
        # never dump raw dicts to UI
        return "-"

    return str(value)


# -------------------------
# Registry-driven formatter
# -------------------------
def format_from_registry(resource_def: dict, action_key: str, record: dict) -> str:
    if not isinstance(record, dict):
        return "⚠ Invalid record format."

    action_def = resource_def.get("actions", {}).get(action_key, {})
    response_def = action_def.get("response")

    if not response_def:
        return "✔ Record retrieved."

    title = response_def.get("title", "Result")
    fields = response_def.get("fields", {})

    lines = [title, "-" * len(title)]

    for field, label in fields.items():
        raw_value = get_nested_value(record, field)
        value = serialize(raw_value)
        lines.append(f"{label}: {value}")

    return "\n".join(lines)
