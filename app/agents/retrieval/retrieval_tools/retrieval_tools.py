from langchain.tools import tool
from pymongo import MongoClient
from typing import Optional
import json
from dotenv import load_dotenv
from bson import ObjectId as BSONObjectId
from datetime import datetime, timedelta
from app.db.db_connector import get_db
from app.registry.registry_loader import load_registry

load_dotenv()

registry = load_registry('./app/registry/retrieval_registry.yaml')

db = get_db()


@tool
def get_work_orders(
    asset_name: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    technician_name: Optional[str] = None,
    due_before: Optional[str] = None,
    due_after: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    limit: int = 10
    ) -> list:
        """
        Retrieve work orders from the database with optional filters.

        Args:
            asset_name     : Filter by asset name (e.g. 'BFW BMV 1600'). Optional.
            status         : Filter by work status. One of: Open, In Progress, Closed, Cancelled. Optional.
            priority       : Filter by priority. One of: Low, Medium, High, Critical. Optional.
            category       : Filter by category. One of: Corrective, Preventive, Inspection, Damage, Emergency. Optional.
            technician_name: Filter by assigned technician full name (e.g. 'John Smith'). Optional.
            due_before     : Filter work orders due before this date. Format: YYYY-MM-DD. Optional.
            due_after      : Filter work orders due after this date. Format: YYYY-MM-DD. Optional.
            created_after  : Filter work orders created after this date. Format: YYYY-MM-DD. Optional.
            created_before : Filter work orders created before this date. Format: YYYY-MM-DD. Optional.
            limit          : Max number of results to return. Default 10.
        """

        match = {"deleted": False}

        # Resolve asset name to ObjectId
        if asset_name:
            asset = db["assets"].find_one({"name": asset_name, "deleted": False}, {"_id": 1})
            if not asset:
                return {"error": f"Asset '{asset_name}' not found. Please check the asset name."}
            match["asset"] = asset["_id"]

        # Resolve technician name to ObjectId
        if technician_name:
            name_parts = technician_name.strip().split(" ", 1)
            query = {"deleted": False}
            if len(name_parts) == 2:
                query["firstName"] = name_parts[0]
                query["lastName"] = name_parts[1]
            else:
                query["$or"] = [
                    {"firstName": name_parts[0]},
                    {"lastName": name_parts[0]}
                ]
            technician = db["users"].find_one(query, {"_id": 1})
            if not technician:
                return {"error": f"Technician '{technician_name}' not found."}
            match["people"] = technician["_id"]

        if status:
            match["workStatus"] = status

        if priority:
            match["priority"] = priority

        if category:
            match["category"] = category

        # Date filters for dueDate
        due_filter = {}
        if due_before:
            due_filter["$lt"] = datetime.strptime(due_before, "%Y-%m-%d")
        if due_after:
            due_filter["$gt"] = datetime.strptime(due_after, "%Y-%m-%d")
        if due_filter:
            match["dueDate"] = due_filter

        # Date filters for createdAt
        created_filter = {}
        if created_after:
            created_filter["$gte"] = datetime.strptime(created_after, "%Y-%m-%d")
        if created_before:
            created_filter["$lte"] = datetime.strptime(created_before, "%Y-%m-%d")
        if created_filter:
            match["createdAt"] = created_filter

        # Load pipeline from registry
        pipeline_text = registry['retrieval_operations']['workorder_retrieval']['pipeline']['stages']
        pipeline_text = pipeline_text.replace('"{{limit}}"', str(limit))
        pipeline = json.loads(pipeline_text)
        pipeline[0]["$match"] = match

        results = list(db["workorders"].aggregate(pipeline))

        if not results:
            return {"message": "No work orders found matching the given filters."}

        # Serialize
        for doc in results:
            doc["_id"] = str(doc["_id"])
            if doc.get("dueDate"):
                doc["dueDate"] = doc["dueDate"].isoformat()
            if doc.get("createdAt"):
                doc["createdAt"] = doc["createdAt"].isoformat()
            if doc.get("updatedAt"):
                doc["updatedAt"] = doc["updatedAt"].isoformat()
            if doc.get("technicians"):
                for t in doc["technicians"]:
                    if "id" in t:
                        t["id"] = str(t["id"])

        return results


@tool
def get_assets(
    name: Optional[str] = None,
    status: Optional[str] = None,
    type_of_asset: Optional[str] = None,
    location: Optional[str] = None,
    manufacturer: Optional[str] = None,
    serial_number: Optional[str] = None,
    installed_after: Optional[str] = None,
    installed_before: Optional[str] = None,
    warranty_expiring_before: Optional[str] = None,
    warranty_expiring_after: Optional[str] = None,
    limit: int = 10
    ) -> list:
        """
        Retrieve assets from the database with optional filters.

        Args:
            name                    : Filter by asset name (e.g. 'BFW BMV 1600'). Optional.
            status                  : Filter by status. One of: Running, Idle, Maintenance, Stopped. Optional.
            type_of_asset           : Filter by asset type (e.g. 'cnc', 'pump', 'motor'). Optional.
            location                : Filter by location name (e.g. 'Building A'). Optional.
            manufacturer            : Filter by manufacturer name. Optional.
            serial_number           : Filter by serial number. Optional.
            installed_after         : Filter assets installed after this date. Format: YYYY-MM-DD. Optional.
            installed_before        : Filter assets installed before this date. Format: YYYY-MM-DD. Optional.
            warranty_expiring_before: Filter assets with warranty expiring before this date. Format: YYYY-MM-DD. Optional.
            warranty_expiring_after : Filter assets with warranty expiring after this date. Format: YYYY-MM-DD. Optional.
            limit                   : Max number of results to return. Default 10.
        """

        match = {"deleted": False}

        if name:
            match["name"] = {"$regex": name, "$options": "i"}

        if status:
            match["assetStatus"] = status

        if type_of_asset:
            match["typeOfAsset"] = {"$regex": type_of_asset, "$options": "i"}

        if location:
            match["location"] = {"$regex": location, "$options": "i"}

        if manufacturer:
            match["manufacturer"] = {"$regex": manufacturer, "$options": "i"}

        if serial_number:
            match["serialNumber"] = serial_number

        # Date filters for installationDate
        install_filter = {}
        if installed_after:
            install_filter["$gte"] = datetime.strptime(installed_after, "%Y-%m-%d")
        if installed_before:
            install_filter["$lte"] = datetime.strptime(installed_before, "%Y-%m-%d")
        if install_filter:
            match["installationDate"] = install_filter

        # Date filters for warrantyExpiryDate
        warranty_filter = {}
        if warranty_expiring_before:
            warranty_filter["$lte"] = datetime.strptime(warranty_expiring_before, "%Y-%m-%d")
        if warranty_expiring_after:
            warranty_filter["$gte"] = datetime.strptime(warranty_expiring_after, "%Y-%m-%d")
        if warranty_filter:
            match["warrantyExpiryDate"] = warranty_filter

        # Load pipeline from registry
        pipeline_text = registry['retrieval_operations']['asset_retrieval']['pipeline']['stages']
        pipeline_text = pipeline_text.replace('"{{limit}}"', str(limit))
        pipeline = json.loads(pipeline_text)
        pipeline[0]["$match"] = match

        results = list(db["assets"].aggregate(pipeline))

        if not results:
            return {"message": "No assets found matching the given filters."}

        # Serialize
        for doc in results:
            doc["_id"] = str(doc["_id"])
            if doc.get("installationDate"):
                doc["installationDate"] = doc["installationDate"].isoformat()
            if doc.get("warrantyExpiryDate"):
                doc["warrantyExpiryDate"] = doc["warrantyExpiryDate"].isoformat()
            if doc.get("createdAt"):
                doc["createdAt"] = doc["createdAt"].isoformat()
            if doc.get("updatedAt"):
                doc["updatedAt"] = doc["updatedAt"].isoformat()

        return results