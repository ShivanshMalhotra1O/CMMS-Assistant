from pymongo import MongoClient
import os


_client = None


def get_mongo_client():
    global _client
    if _client is None:
        _client = MongoClient(os.getenv("MONGO_URI"))
    return _client


def get_db():
    client = get_mongo_client()
    return client[os.getenv("MONGO_DB_NAME")]


