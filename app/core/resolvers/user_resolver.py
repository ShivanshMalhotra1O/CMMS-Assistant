from bson import ObjectId

def resolve_user(db, name_or_email: str):
    return db.users.find_one({
        "$or": [
            {"firstName": {"$regex": f"^{name_or_email}$", "$options": "i"}},
            {"lastName": {"$regex": f"^{name_or_email}$", "$options": "i"}},
            {"email": {"$regex": name_or_email, "$options": "i"}}
        ]
    }, {"_id": 1})
