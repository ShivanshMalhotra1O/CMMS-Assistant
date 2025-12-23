from app.query.builder import QueryPlan


def execute_mongo(db, query: QueryPlan):
    collection = db[query.collection]

    cursor = collection.find(query.filter)

    if query.sort:
        cursor = cursor.sort(query.sort)

    if query.limit:
        cursor = cursor.limit(query.limit)

    return list(cursor)
