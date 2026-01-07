from pymongo import MongoClient
from typing import List, Any
import os
import json


class MongoExecutor:
    def __init__(self):
        mongo_uri = os.getenv("MONGO_URI")
        db_name = os.getenv("MONGO_DB_NAME")

        if not mongo_uri:
            raise ValueError("MONGO_URI environment variable not set")

        if not db_name:
            raise ValueError("MONGO_DB_NAME environment variable not set")

        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]

    # -------------------------------
    # PIPELINE PARSER (JSON ONLY)
    # -------------------------------
    def parse_pipeline(self, pipeline_text: str) -> List[dict]:
        try:
            pipeline = json.loads(pipeline_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON aggregation pipeline: {e}")

        # ✅ Normalize single-stage dict → list
        if isinstance(pipeline, dict):
            pipeline = [pipeline]

        if not isinstance(pipeline, list):
            raise ValueError("Aggregation pipeline must be a list of stages")

        self._validate_pipeline(pipeline)
        return pipeline

    # -------------------------------
    # PIPELINE VALIDATOR
    # -------------------------------
    def _validate_pipeline(self, pipeline: List[dict]) -> None:
        for idx, stage in enumerate(pipeline):
            if not isinstance(stage, dict):
                raise ValueError(f"Stage {idx} is not an object")

            if len(stage) != 1:
                raise ValueError(
                    f"Stage {idx} must contain exactly one operator, got {len(stage)}"
                )

            operator = next(iter(stage.keys()))

            if not isinstance(operator, str):
                raise ValueError(
                    f"Stage {idx} operator key must be a string, got {type(operator)}"
                )

            if not operator.startswith("$"):
                raise ValueError(
                    f"Stage {idx} has invalid MongoDB operator: {operator}"
                )

    # -------------------------------
    # EXECUTION
    # -------------------------------
    def execute_aggregation(
        self,
        collection_name: str,
        pipeline_text: str,
        limit: int | None = None
    ) -> List[Any]:

        pipeline = self.parse_pipeline(pipeline_text)

        # ✅ Append $limit only if explicitly requested and not already present
        if limit is not None:
            has_limit = any("$limit" in stage for stage in pipeline)
            if not has_limit:
                pipeline.append({"$limit": limit})

        collection = self.db[collection_name]

        try:
            return list(collection.aggregate(pipeline, allowDiskUse=True))
        except Exception as e:
            raise RuntimeError(f"MongoDB execution failed: {e}")
