from bson import ObjectId
from datetime import datetime


# -------------------------
# Safe nested field resolver
# -------------------------
def get_nested_value(data: dict, path: str):
    if not isinstance(data, dict) or not path:
        return None

    value = data
    for key in path.split("."):
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
        return ", ".join(str(v) for v in value) or "-"

    if isinstance(value, dict):
        return "-"

    return str(value)


# -------------------------
# Registry-driven formatter (FIXED)
# -------------------------
def format_from_registry(resource_def: dict, record: dict) -> str:
    output_def = resource_def.get("output", {}).get("default")

    # 🛡 Safety fallback
    if not isinstance(output_def, dict):
        return "✔ Record retrieved."

    title = output_def.get("title", "Record")
    fields = output_def.get("fields", {})

    lines = [
        title,
        "-" * len(title)
    ]

    for field, label in fields.items():
        raw_value = get_nested_value(record, field)
        value = serialize(raw_value)
        lines.append(f"{label:<15}: {value}")

    # 🔑 CRITICAL: real line breaks between records
    return "\n".join(lines)
