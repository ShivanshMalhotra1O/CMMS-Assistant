from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from enum import Enum


class QueryType(str, Enum):
    SELECT = "select"


class AbstractQuery(BaseModel):
    type: QueryType = QueryType.SELECT
    table: str
    where: Dict[str, Any] = {}
    limit: Optional[int] = 50
    offset: Optional[int] = 0
    order_by: Optional[List[str]] = None
