import sqlite3
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from fastapi.exceptions import RequestValidationError

app = FastAPI()

conn = sqlite3.connect("tasks.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0
)
""")

cursor.execute("SELECT COUNT(*) FROM tasks")
count = cursor.fetchone()[0]

if count == 0:
    cursor.executemany(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        [
            ("Learn FastAPI", 0),
            ("Build Task API", 0),
            ("Push to GitHub", 0),
        ]
    )

conn.commit()

# Handles invalid request bodies and returns a simple 400 error.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "Title is required and must not be empty"}
    )


class TaskCreate(BaseModel):
    title: str = Field(min_length=1)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    done: bool | None = None


# In-memory task storage.
# Data will reset when the server restarts.
tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": False},
    {"id": 2, "title": "Build Task API", "done": False},
    {"id": 3, "title": "Push to GitHub", "done": False},
]


@app.get("/", description="Returns information about the Task API.")
def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }


@app.get("/health", description="Checks whether the API is running.")
def health():
    return {"status": "ok"}


@app.get(
    "/tasks",
    description="Returns all tasks from the SQLite database."
)
def get_tasks():
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks")
    rows = cursor.fetchall()

    conn.close()

    return [
        {
            "id": row[0],
            "title": row[1],
            "done": bool(row[2])
        }
        for row in rows
    ]


@app.get(
    "/tasks/{task_id}",
    description="Returns a single task by ID from the SQLite database."
)
def get_task(task_id: int):
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,)
    )

    row = cursor.fetchone()

    conn.close()

    if row is None:
        return JSONResponse(
            status_code=404,
            content={"error": "Task not found"}
        )

    return {
        "id": row[0],
        "title": row[1],
        "done": bool(row[2])
    }


@app.post(
    "/tasks",
    status_code=201,
    description="Creates a new task."
)
def create_task(task: TaskCreate):
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (task.title, 0)
    )

    new_id = cursor.lastrowid
    conn.commit()

    cursor.execute(
        "SELECT id, title, done FROM tasks WHERE id = ?",
        (new_id,)
    )
    row = cursor.fetchone()

    conn.close()

    return {
        "id": row[0],
        "title": row[1],
        "done": bool(row[2])
    }


@app.put(
    "/tasks/{task_id}",
    description="Updates an existing task."
)
def update_task(task_id: int, updates: TaskUpdate):

    if updates.title is None and updates.done is None:
        return JSONResponse(
            status_code=400,
            content={"error": "At least title or done is required"}
        )

    for task in tasks:
        if task["id"] == task_id:

            if updates.title is not None:
                task["title"] = updates.title

            if updates.done is not None:
                task["done"] = updates.done

            return task

    return JSONResponse(
        status_code=404,
        content={"error": f"Task {task_id} not found"}
    )


@app.delete(
    "/tasks/{task_id}",
    status_code=204,
    description="Deletes a task."
)
def delete_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            tasks.remove(task)
            return

    return JSONResponse(
        status_code=404,
        content={"error": f"Task {task_id} not found"}
    )


@app.get(
    "/stats",
    description="Returns statistics about the tasks."
)
def get_stats():
    total = len(tasks)
    done = sum(1 for task in tasks if task["done"])
    open_tasks = total - done

    return {
        "total": total,
        "done": done,
        "open": open_tasks
    }


@app.post(
    "/reset",
    description="Resets the task list to the original example tasks."
)
def reset_tasks():
    global tasks

    tasks = [
        {"id": 1, "title": "Learn FastAPI", "done": False},
        {"id": 2, "title": "Build Task API", "done": False},
        {"id": 3, "title": "Push to GitHub", "done": False},
    ]

    return {
        "message": "Tasks reset successfully",
        "tasks": tasks
    }