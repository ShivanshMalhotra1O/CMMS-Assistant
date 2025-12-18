Task_Keywords = {
    # Strong CMMS phrases
    "work order": 0.9,
    "open work order": 0.95,
    "close work order": 0.95,
    "repair work order": 0.95,
    "repair order": 0.9,
    "add asset": 0.9,

    # CMMS domain nouns
    "maintenance": 0.75,
    "repair": 0.75,
    "service": 0.7,
    "task": 0.6,
    "work": 0.55,

    # Action verbs (generic, lower confidence)
    "create": 0.6,
    "update": 0.6,
    "close": 0.65,
    "delete": 0.7,
    "assign": 0.6,
    "schedule": 0.6,

    # Read-style operations (still tasks, but weaker)
    "view": 0.55,
    "list": 0.55,
    "search": 0.55,
    "find": 0.55,
    "get": 0.55,
    "view all": 0.6,
    "list all": 0.6,
    "search all": 0.6,
    "find all": 0.6,
    "get all": 0.6,
}

Analyze_Keywords = {
    # Core analysis actions
    "analyze": 0.65,
    "analysis": 0.65,
    "strategies": 0.7,
    "reports": 0.7,

    # Data artifacts
    "data": 0.6,
    "report": 0.65,
    "chart": 0.7,
    "graph": 0.7,
    "table": 0.7,

    # Performance / metrics (strong indicators)
    "performance": 0.85,
    "efficiency": 0.9,
    "productivity": 0.9,
    "utilization": 0.9,
    "capacity": 0.85,
}
