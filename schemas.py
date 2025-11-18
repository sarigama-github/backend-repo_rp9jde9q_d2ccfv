"""
Database Schemas for Story Learning Game

Each Pydantic model represents a MongoDB collection. The collection name
is the lowercase of the class name.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class PathNode(BaseModel):
    id: str = Field(..., description="Unique id for the node")
    title: str = Field(..., description="Short title shown on the map")
    summary: str = Field(..., description="One-line summary")
    content: str = Field(..., description="Story content / lesson text")
    order: int = Field(..., ge=0, description="Order in the path")
    difficulty: Optional[str] = Field(None, description="Easy/Medium/Hard")
    type: Optional[str] = Field(None, description="lesson | video | quiz | project")


class LearningPath(BaseModel):
    title: str = Field(..., description="Path title")
    description: str = Field(..., description="Path description shown under the hero")
    theme: str = Field("adventure", description="Theme keyword for visuals")
    nodes: List[PathNode] = Field(default_factory=list, description="Ordered list of nodes")


class Progress(BaseModel):
    user_id: str = Field(..., description="User identifier (e.g., 'guest')")
    path_title: str = Field(..., description="Title of the path this progress belongs to")
    completed_node_ids: List[str] = Field(default_factory=list, description="IDs of completed nodes")
