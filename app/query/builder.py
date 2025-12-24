from dataclasses import dataclass
from typing import Dict, Any
from app.policy.engine import Resource


@dataclass
class QueryPlan:
    collection: str
    filter: Dict[str, Any]
    sort: list
    limit: int
    joins: list | None = None


def build_query(registry, resource: Resource, params: dict) -> QueryPlan:
    resource_def = registry[resource.value]
    action_def = resource_def["actions"]["view"]

    query_filter = {}
    joins = []

    # -------------------------
    # Filters
    # -------------------------
    for param, field in action_def.get("filters", {}).items():
        if param in params and params[param] is not None:
            query_filter[field] = params[param]

    # -------------------------
    # Sort & Limit (fallback-safe)
    # -------------------------
    fallback = action_def.get("fallback", {})
    sort_key = params.get("sort") or fallback.get("sort")
    limit = params.get("limit") or action_def["limits"]["default"]

    sort = None
    if sort_key:
        sort_def = action_def["sorts"].get(sort_key)
        if sort_def:
            order = -1 if sort_def["order"] == "desc" else 1
            sort = [(sort_def["field"], order)]

    # -------------------------
    # JOIN DETECTION 
    # -------------------------
    free_text = params.get("free_text", "").lower()

    relations = resource_def.get("relations", {})
    for rel_name, rel_def in relations.items():
        for exposed_field in rel_def.get("exposable_fields", {}).keys():
            if exposed_field.lower() in free_text:
                joins.append(rel_name)
                break
    
                

    return QueryPlan(
        collection=resource_def["collection"],
        filter=query_filter,
        sort=sort,
        limit=limit,
        joins=joins or None
    )
