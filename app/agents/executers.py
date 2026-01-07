from pymongo.database import Database
from typing import Any
from app.query.mongo_executor import MongoExecutor
from bson import ObjectId
from datetime import datetime


class ActionExecutor:
    """
    Main execution orchestrator for CMMS system
    Handles the complete workflow from validation to formatted output
    """
    
    def __init__(self):
        self.mongo_executor = MongoExecutor()
    
    def _format_value(self, key: str, value: Any) -> str:
        """Format a value for display"""
        if key == "_id" or isinstance(value, ObjectId):
            return str(value)
        elif isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")
        elif isinstance(value, bool):
            return "✓ Yes" if value else "✗ No"
        elif value is None or value == "":
            return "-"
        elif isinstance(value, list):
            if not value:
                return "None"
            return ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            return str(value)
        else:
            return str(value)
    
    def _format_key(self, key: str) -> str:
        """Format a field key for display"""
        # Handle special cases
        replacements = {
            "_id": "ID",
            "workOrderId": "Work Order ID",
            "workStatus": "Status",
            "companyId": "Company ID",
            "plantId": "Plant ID",
            "assetStatus": "Status",
            "createdAt": "Created",
            "updatedAt": "Updated",
            "dueDate": "Due Date",
        }
        
        if key in replacements:
            return replacements[key]
        
        # Convert camelCase or snake_case to Title Case
        result = key.replace("_", " ")
        # Split on capital letters for camelCase
        import re
        result = re.sub(r'([A-Z])', r' \1', result)
        return result.strip().title()
    
    def execute_action(
        self,
        db: Database,
        registry: dict,
        collection_name: str,
        pipeline_text: str,
        resource_key: str = None,
        action_key: str = None,
        limit: int = 20
    ) -> str:
        """
        Execute a MongoDB aggregation pipeline and format results
        
        Args:
            db: MongoDB database instance (kept for backward compatibility)
            registry: Registry dictionary (collections from registry.yaml)
            collection_name: MongoDB collection name (e.g., "workorders", "assets")
            pipeline_text: JSON string of MongoDB aggregation pipeline
            resource_key: Not used when working with registry.yaml only
            action_key: Not used when working with registry.yaml only
            limit: Maximum number of results to return
            
        Returns:
            Formatted string response
        """
        
        print(f"DEBUG → ActionExecutor called with:")
        print(f"  collection_name: {collection_name}")
        print(f"  pipeline_text: {pipeline_text}")
        
        # Execute query using MongoExecutor
        try:
            print(f"DEBUG → Executing aggregation on collection '{collection_name}'")
            result = self.mongo_executor.execute_aggregation(
                collection_name=collection_name,
                pipeline_text=pipeline_text,
                limit=limit
            )
            
            print(f"DEBUG → Result count: {len(result)}")
            if result:
                print(f"DEBUG → First result keys: {list(result[0].keys()) if len(result) > 0 else 'N/A'}")
            
        except Exception as e:
            print(f"DEBUG → Execution error: {type(e).__name__}: {str(e)}")
            return f"❌ Execution failed: {str(e)}"

        if not result:
            return "❌ No records found."

        # Format response
        try:
            print(f"DEBUG → Formatting {len(result)} results")
            
            # Define which fields to show based on collection
            field_priority = {
                "workorders": ["workOrderId", "name", "description", "workStatus", "priority", "dueDate", "createdAt"],
                "assets": ["name", "description", "assetStatus", "typeOfAsset", "manufacturer", "serialNumber"],
                "preventiveMaintenance": ["preventiveMaintenanceId", "name", "description", "lastMaintenanceDate", "nextGenerationDate"],
            }
            
            priority_fields = field_priority.get(collection_name, [])
            
            response = []
            response.append(f"📊 Found {len(result)} {collection_name.replace('_', ' ').title()}\n")
            
            for idx, record in enumerate(result, 1):
                response.append(f"\n🔹 Record {idx}")
                response.append("─" * 50)
                
                # Show priority fields first
                shown_fields = set()
                for field in priority_fields:
                    if field in record:
                        formatted_key = self._format_key(field)
                        formatted_value = self._format_value(field, record[field])
                        response.append(f"{formatted_key:.<25} {formatted_value}")
                        shown_fields.add(field)
                
                # Show remaining fields (except internal ones)
                for key, value in record.items():
                    if key not in shown_fields and not key.startswith("__") and key not in ["deleted", "companyId", "plantId"]:
                        formatted_key = self._format_key(key)
                        formatted_value = self._format_value(key, value)
                        response.append(f"{formatted_key:.<25} {formatted_value}")
                
                response.append("")
            
            final_response = "\n".join(response)
            print(f"DEBUG → Formatted response length: {len(final_response)} chars")
            return final_response
        
        except Exception as e:
            print(f"DEBUG → Formatting error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            # Fallback: return simple format
            response = [f"Found {len(result)} records:\n"]
            for idx, record in enumerate(result, 1):
                response.append(f"\nRecord {idx}: {record.get('name', record.get('workOrderId', 'N/A'))}")
            return "\n".join(response)