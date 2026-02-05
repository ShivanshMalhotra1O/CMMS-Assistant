from langchain.tools import tool
from pymongo import MongoClient
import os
import yaml
import json
from dotenv import load_dotenv
from bson import ObjectId as BSONObjectId
from datetime import datetime, timedelta
from app.db import get_db

load_dotenv()

# Load registry
def load_registry(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

registry = load_registry('./app/test_workspace/test_registry.yaml')

db = get_db()

@tool
def asset_information(asset_name: str) -> dict:
    """Get complete asset information by asset name. Use this when user asks for asset details."""
    
    # Get pipeline from registry
    pipeline_text = registry['workorder_operations']['create_workorder']['context_gathering']['queries'][0]['pipeline']
    
    # Replace template variable
    pipeline_text = pipeline_text.replace("{{asset_name}}", asset_name)
    
    # Parse and execute
    pipeline = json.loads(pipeline_text)
    result = list(db['assets'].aggregate(pipeline))
    
    if not result:
        return {"error": "Asset not found. Please check the asset name."}
    
    # Convert ObjectId to string
    if "_id" in result[0]:
        result[0]["_id"] = str(result[0]["_id"])
    
    return result[0]


@tool
def get_past_work_orders(asset_id: str) -> dict:
    """Get past work orders for an asset"""
    
    # Get pipeline from registry
    pipeline_text = registry['workorder_operations']['create_workorder']['context_gathering']['queries'][1]['pipeline']
    
    # Replace with placeholder string
    pipeline_text = pipeline_text.replace('"{{asset_id}}"', '"__ASSET_ID__"')
    
    # Parse JSON
    pipeline = json.loads(pipeline_text)
    
    # Replace placeholder with ObjectId
    pipeline[0]['$match']['asset'] = BSONObjectId(asset_id)
    
    result = list(db['workorders'].aggregate(pipeline))
    
    if not result:
        return {"error": "No past work orders found."}
    
    # Convert ObjectId to string
    for doc in result:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
    
    return result

@tool
def work_order_counter(companyId: str) -> dict:
    """Get the next work order counter"""  
    
    # Get pipeline from registry
    pipeline_text = registry['workorder_operations']['create_workorder']['context_gathering']['queries'][2]['pipeline']
    
    # Replace with placeholder
    pipeline_text = pipeline_text.replace('"{{companyId}}"', '"__COMPANY_ID__"')
    
    # Parse JSON
    pipeline = json.loads(pipeline_text)
    
    # Replace placeholder with ObjectId
    pipeline[0]['$match']['companyId'] = BSONObjectId(companyId)
    
    result = list(db['counters'].aggregate(pipeline))

    if not result:
        return {"error": "No work order counter found."}
    
    # Convert ObjectId to string for JSON serialization
    if "_id" in result[0]:
        result[0]["_id"] = str(result[0]["_id"])
    
    # Return next counter value (current seq + 1)
    return str(result[0]['seq']+1)

@tool
def get_technician_details(companyId: str) -> dict:
    """Get available technician details for a company"""

    # Get pipeline from registry
    pipeline_text = registry['workorder_operations']['create_workorder']['context_gathering']['queries'][3]['pipeline']

    # Replace with placeholder
    pipeline_text = pipeline_text.replace('"{{companyId}}"', '"__COMPANY_ID__"')

    # Parse JSON
    pipeline = json.loads(pipeline_text)

    # Replace placeholder with ObjectId
    pipeline[0]['$match']['companyId'] = BSONObjectId(companyId)

    result = list(db['users'].aggregate(pipeline))

    if not result:
        return {"error": "No technicians found."}

    # Convert ObjectId to string
    for doc in result:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])

    return result


@tool
def create_work_order(asset_name: str, user_description: str = "", priority: str = "Medium", category: str = "Corrective", assigned_technician: str = None) -> dict:
    """Create a new work order with provided details"""
    
    asset = asset_information.invoke({"asset_name": asset_name})
    if "error" in asset:
        return asset
    
    counter = work_order_counter.invoke({"companyId": str(asset["companyId"])})
    
    # Build work order document
    work_order = {
        "workOrderId": f"WO-{counter}",
        "name": f"Work Order for {asset['name']}",
        "description": user_description or f"Maintenance work for {asset['name']}",
        "asset": BSONObjectId(asset["_id"]),
        "companyId": BSONObjectId(asset["companyId"]),
        "plantId": BSONObjectId(asset.get("plant")),
        "priority": priority,
        "workStatus": "Open",
        "category": category,
        "people": [BSONObjectId(assigned_technician)] if assigned_technician else [],
        "groups": [],
        "spareParts": [],
        "consumablesAndTools": [],
        "taskAndChecklist": [],
        "dueDate": datetime.now() + timedelta(days=7),
        "deleted": False,
        "createdAt": datetime.now(),
        "updatedAt": datetime.now()
    }
    
    # Insert into database
    # result = db["workorders"].insert_one(work_order)
    
    # Convert ObjectIds to strings for return
    # work_order["_id"] = str(result.inserted_id)
    work_order["asset"] = str(work_order["asset"])
    work_order["companyId"] = str(work_order["companyId"])
    work_order["plantId"] = str(work_order["plantId"])
    work_order["people"] = [str(p) for p in work_order["people"]]
    work_order["createdAt"] = work_order["createdAt"].isoformat()
    work_order["updatedAt"] = work_order["updatedAt"].isoformat()
    work_order["dueDate"] = work_order["dueDate"].isoformat()
    
    return work_order
