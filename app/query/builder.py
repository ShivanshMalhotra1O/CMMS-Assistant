from dataclasses import dataclass
from typing import Dict, Any
from app.policy.engine import Resource


@dataclass
class QueryPlan:
    collection: str
    filter: Dict[str, Any]
    sort: list
    limit: int


def build_query(
    registry: dict,
    resource: Resource,
    params: dict
) -> QueryPlan:

    resource_def = registry[resource.value]
    action_def = resource_def["actions"]["view"]

    # -------------------------
    # WHERE
    # -------------------------
    query_filter: Dict[str, Any] = {}

    for param, field in action_def.get("filters", {}).items():
        if param in params and params[param] is not None:
            query_filter[field] = params[param]

    # -------------------------
    # SORT
    # -------------------------
    sort_def = action_def.get("sorts", {})
    fallback = action_def.get("fallback", {})

    sort_key = params.get("sort")
    sort_rule = sort_def.get(sort_key) if sort_key else None

    if not sort_rule:
        sort_rule = sort_def.get(fallback.get("sort"))

    sort = []
    if sort_rule:
        order = -1 if sort_rule["order"] == "desc" else 1
        sort = [(sort_rule["field"], order)]

    # -------------------------
    # LIMIT
    # -------------------------
    limits_def = action_def.get("limits", {})
    default_limit = limits_def.get("default", 10)
    max_limit = limits_def.get("max", default_limit)

    requested_limit = params.get("limit")
    limit = min(requested_limit, max_limit) if requested_limit else default_limit

    return QueryPlan(
        collection=resource_def["collection"],
        filter=query_filter,
        sort=sort,
        limit=limit
    )
