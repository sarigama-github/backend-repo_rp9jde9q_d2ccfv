import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from database import db, create_document, get_documents
from schemas import LearningPath, PathNode, Progress

app = FastAPI(title="Story Learning Game API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Story Learning Game Backend Running"}


# Bootstrap a default path if DB empty
@app.post("/bootstrap", tags=["admin"])
def bootstrap_content():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    existing = list(db["learningpath"].find({}).limit(1))
    if existing:
        return {"status": "ok", "message": "Already bootstrapped"}

    nodes = [
        PathNode(
            id="n1",
            title="Arrival",
            summary="Meet your guide and learn the rules",
            content="Welcome adventurer! This realm turns lessons into quests.",
            order=0,
            difficulty="easy",
        ),
        PathNode(
            id="n2",
            title="Fork in the Road",
            summary="Choose your learning style",
            content="Pick examples, theory, or challenges to proceed.",
            order=1,
            difficulty="easy",
        ),
        PathNode(
            id="n3",
            title="The Puzzle Gate",
            summary="Apply what you learned",
            content="Solve a small puzzle to open the gate.",
            order=2,
            difficulty="medium",
        ),
    ]

    path = LearningPath(
        title="Hero's Journey into Coding",
        description="An interactive story where each stop teaches a concept.",
        theme="gaming",
        nodes=nodes,
    )

    create_document("learningpath", path)
    return {"status": "ok", "message": "Bootstrapped default content"}


@app.get("/paths", response_model=List[LearningPath])
def list_paths():
    docs = get_documents("learningpath")
    # Convert Mongo docs to Pydantic-friendly dicts
    normalized = []
    for d in docs:
        d.pop("_id", None)
        normalized.append(LearningPath(**d))
    return normalized


class ProgressIn(BaseModel):
    user_id: str
    path_title: str
    node_id: str


@app.post("/progress/toggle")
def toggle_progress(p: ProgressIn):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    coll = db["progress"]
    doc = coll.find_one({"user_id": p.user_id, "path_title": p.path_title})
    if not doc:
        progress = Progress(user_id=p.user_id, path_title=p.path_title, completed_node_ids=[p.node_id])
        create_document("progress", progress)
        return {"status": "ok", "completed_node_ids": progress.completed_node_ids}

    completed = set(doc.get("completed_node_ids", []))
    if p.node_id in completed:
        completed.remove(p.node_id)
    else:
        completed.add(p.node_id)

    coll.update_one({"_id": doc["_id"]}, {"$set": {"completed_node_ids": list(completed)}})
    return {"status": "ok", "completed_node_ids": list(completed)}


@app.get("/progress/{user_id}/{path_title}")
def get_progress(user_id: str, path_title: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    doc = db["progress"].find_one({"user_id": user_id, "path_title": path_title})
    if not doc:
        return {"completed_node_ids": []}
    return {"completed_node_ids": doc.get("completed_node_ids", [])}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
