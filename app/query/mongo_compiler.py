from app.query.models import AbstractQuery


def compile_to_mongo(query: AbstractQuery):
    mongo_filter = {}

    for key, value in query.where.items():
        mongo_filter[key] = value

    return {
        "collection": query.table,
        "filter": mongo_filter,
        "limit": query.limit,
        "skip": query.offset or 0
    }
