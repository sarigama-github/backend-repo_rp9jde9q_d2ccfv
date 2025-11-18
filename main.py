import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

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


# Bootstrap sample content (optionally reset existing)
@app.post("/bootstrap", tags=["admin"])
def bootstrap_content(force: bool = Query(False, description="If true, clears existing content and reseeds")):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    lp_coll = db["learningpath"]
    prog_coll = db["progress"]

    existing = list(lp_coll.find({}).limit(1))
    if existing and not force:
        return {"status": "ok", "message": "Already bootstrapped"}

    # If force, clear existing
    if force:
        lp_coll.delete_many({})
        prog_coll.delete_many({})

    # Build a much larger set of goals
    big_nodes: List[PathNode] = []
    entries = [
        ("Arrival", "Meet your guide and learn the rules", "Welcome adventurer! This realm turns lessons into quests.", "easy", "lesson"),
        ("Fork in the Road", "Choose your learning style", "Pick examples, theory, or challenges to proceed.", "easy", "lesson"),
        ("First Spark", "Your first tiny win", "Light the campfire by following the hints.", "easy", "video"),
        ("Puzzle Gate", "Solve a small puzzle", "Crack the runes to open the ancient gate.", "medium", "quiz"),
        ("Syntax Springs", "Read the signs", "Explore gentle syntax streams with playful examples.", "easy", "lesson"),
        ("Looping Lagoon", "Go around with style", "Sail in circles to collect pearls while looping.", "medium", "video"),
        ("Branching Bridge", "Choose wisely", "Cross a bridge that splits based on your decisions.", "medium", "lesson"),
        ("Mapmaker's Post", "Draw your path", "Sketch a small map using coordinates and curves.", "medium", "project"),
        ("Function Falls", "Reusable magic", "Bottle a waterfall: turn flowing steps into a spell.", "medium", "lesson"),
        ("Testy Tunnels", "Check your work", "Shine a lantern on bugs by writing small tests.", "medium", "quiz"),
        ("Object Oasis", "Bundle and carry", "Pack related ideas into neat containers.", "medium", "video"),
        ("Module Market", "Trade and share", "Browse a bazaar of reusable pieces.", "easy", "lesson"),
        ("Async Airships", "Do many things at once", "Launch parallel airships to deliver messages.", "hard", "video"),
        ("Error Escarpment", "Trip safely", "Practice falling and recovering with grace.", "medium", "lesson"),
        ("Data Dunes", "Shape the sand", "Filter, map, and reduce dunes into sculptures.", "medium", "quiz"),
        ("Promise Peaks", "Trust the climb", "Climb with ropes that resolve at the summit.", "medium", "lesson"),
        ("HTTP Harbor", "Talk to distant lands", "Send messages in bottles and read the replies.", "medium", "lesson"),
        ("JSON Jungle", "Tame the trees", "Navigate tangled data vines safely.", "easy", "quiz"),
        ("SVG Savanna", "Draw with math", "Paint graceful paths and shapes on a living canvas.", "medium", "project"),
        ("State Summit", "Remember and react", "Carry state up the mountain and share views.", "hard", "lesson"),
        ("Hook Highlands", "Reusable reactions", "Craft tiny hooks to catch behavior.", "medium", "video"),
        ("Design Desert", "Balance and contrast", "Find oases of whitespace and rhythm.", "medium", "lesson"),
        ("Accessibility Arcade", "Everyone plays", "Win tickets by making controls friendly.", "medium", "quiz"),
        ("Performance Plains", "Ride fast", "Tune your mount and pack only what you need.", "hard", "lesson"),
        ("Security Stronghold", "Guard the gate", "Keep secrets safe and verify travelers.", "hard", "lesson"),
        ("Deployment Dock", "Set sail", "Launch ships with careful checklists.", "medium", "video"),
        ("Observability Overlook", "Read the stars", "Trace, log, and watch the skies.", "medium", "lesson"),
        ("Final Forge", "Craft a relic", "Temper your knowledge into a finished artifact.", "hard", "project"),
    ]

    for i, (title, summary, content, difficulty, typ) in enumerate(entries):
        big_nodes.append(PathNode(
            id=f"n{i+1}",
            title=title,
            summary=summary,
            content=content,
            order=i,
            difficulty=difficulty,
            type=typ,
        ))

    path = LearningPath(
        title="Hero's Journey into Coding",
        description="An interactive story where each stop teaches a concept.",
        theme="gaming",
        nodes=big_nodes,
    )

    create_document("learningpath", path)
    return {"status": "ok", "message": f"Bootstrapped with {len(big_nodes)} goals", "count": len(big_nodes)}


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
