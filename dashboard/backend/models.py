"""
Pydantic models for Dashboard API
"""

from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

class LogMessage(BaseModel):
    timestamp: str
    level: str
    message: str
    node_id: Optional[str] = None
    execution_id: str
    status: Optional[str] = None
    duration_ms: Optional[float] = None

class NodeExecution(BaseModel):
    status: str
    duration_ms: Optional[float] = None
    timestamp: str

class Execution(BaseModel):
    id: str
    start_time: str
    nodes: Dict[str, NodeExecution]
    logs: List[LogMessage]

class GraphNode(BaseModel):
    id: str
    label: str
    position: Dict[str, int]

class GraphEdge(BaseModel):
    source: str
    target: str

class GraphStructure(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
