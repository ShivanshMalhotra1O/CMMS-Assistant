from app.query.builder import QueryPlan


def execute_mongo(db, query: QueryPlan, registry: dict, resource: str):
    collection = db[query.collection]

    # -------------------------
    # Aggregation path (JOIN)
    # -------------------------
    if query.joins:
        resource_def = registry[resource]
        relations = resource_def.get("relations", {})

        pipeline = []

        # WHERE
        if query.filter:
            pipeline.append({"$match": query.filter})

        # JOINS
        for join_name in query.joins:
            if join_name not in relations:
                continue  # safety

            rel = relations[join_name]
            foreign_collection = registry[rel["resource"]]["collection"]

            pipeline.append({
                "$lookup": {
                    "from": foreign_collection,
                    "localField": rel["local_field"],
                    "foreignField": rel["foreign_field"],
                    "as": join_name
                }
            })

            pipeline.append({
                "$unwind": {
                    "path": f"${join_name}",
                    "preserveNullAndEmptyArrays": True
                }
            })

        # SORT
        if query.sort:
            pipeline.append({"$sort": dict(query.sort)})

        # LIMIT
        if query.limit:
            pipeline.append({"$limit": query.limit})

        return list(collection.aggregate(pipeline))

    # -------------------------
    # Simple find() fallback
    # -------------------------
    cursor = collection.find(query.filter)

    if query.sort:
        cursor = cursor.sort(query.sort)

    if query.limit:
        cursor = cursor.limit(query.limit)

    return list(cursor)
