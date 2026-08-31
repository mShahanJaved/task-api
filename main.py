import sqlite3
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from fastapi.exceptions import RequestValidationError

app = FastAPI()

DB_NAME = "tasks.db"


def get_connection():
    """Creates a new SQLite connection with row access by column name."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates the tasks table, index, and seed data if needed."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_title
        ON tasks(title)
    """)

    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]

    if count == 0:
        try:
            cursor.execute("BEGIN")

            cursor.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                [
                    ("Learn FastAPI", 0),
                    ("Build Task API", 0),
                    ("Push to GitHub", 0),
                ]
            )

            conn.commit()

        except Exception:
            conn.rollback()
            raise

    conn.close()


init_db()


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


def row_to_task(row: sqlite3.Row) -> dict:
    """Converts a sqlite3.Row into a task dictionary."""
    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"])
    }


# Root Endpoint
@app.get("/", description="Returns information about the Task API.")
def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }


# To Check Health of the API
@app.get("/health", description="Checks whether the API is running.")
def health():
    return {"status": "ok"}


@app.get("/tasks", description="Returns tasks, with optional filtering and search.")
def get_tasks(
    done: bool | None = None,
    search: str | None = None
):
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT id, title, done FROM tasks"
    conditions = []
    params = []

    # SQL status filtering
    if done is not None:
        conditions.append("done = ?")
        params.append(1 if done else 0)

    # SQL title searching
    if search:
        conditions.append("title LIKE ?")
        params.append(f"%{search}%")

    # Add WHERE only when filters are provided
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # SQL sorting
    query += " ORDER BY title"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    conn.close()

    return [row_to_task(row) for row in rows]


# To Get a Single Task
@app.get(
    "/tasks/{task_id}",
    description="Returns a single task by ID from the SQLite database."
)
def get_task(task_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, title, done FROM tasks WHERE id = ?",
        (task_id,)
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"}
        )

    return row_to_task(row)


# To Add Tasks
@app.post(
    "/tasks",
    status_code=201,
    description="Creates a new task."
)
def create_task(task: TaskCreate):
    conn = get_connection()
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

    return row_to_task(row)


# To Update Tasks
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

    conn = get_connection()
    cursor = conn.cursor()

    # First get the existing task
    cursor.execute(
        "SELECT id, title, done FROM tasks WHERE id = ?",
        (task_id,)
    )
    row = cursor.fetchone()

    if row is None:
        conn.close()
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"}
        )

    # Keep existing values when a field isn't provided
    title = updates.title if updates.title is not None else row["title"]
    done = int(updates.done) if updates.done is not None else row["done"]

    cursor.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (title, done, task_id)
    )
    conn.commit()

    # Get updated task
    cursor.execute(
        "SELECT id, title, done FROM tasks WHERE id = ?",
        (task_id,)
    )
    updated_row = cursor.fetchone()
    conn.close()

    return row_to_task(updated_row)


# To Delete Tasks
@app.delete(
    "/tasks/{task_id}",
    status_code=204,
    description="Deletes a task."
)
def delete_task(task_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    # Check whether task exists
    cursor.execute(
        "SELECT id FROM tasks WHERE id = ?",
        (task_id,)
    )
    row = cursor.fetchone()

    if row is None:
        conn.close()
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"}
        )

    cursor.execute(
        "DELETE FROM tasks WHERE id = ?",
        (task_id,)
    )
    conn.commit()
    conn.close()

    return None


# To Get Statistics
@app.get(
    "/stats",
    description="Returns statistics about the tasks."
)
def get_stats():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM tasks")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS done FROM tasks WHERE done = 1")
    done = cursor.fetchone()["done"]

    conn.close()

    return {
        "total": total,
        "done": done,
        "open": total - done
    }


# To Reset Tasks
@app.post(
    "/reset",
    description="Resets the tasks table to the original example tasks."
)
def reset_tasks():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM tasks")
    cursor.execute(
        "DELETE FROM sqlite_sequence WHERE name = 'tasks'"
    )

    cursor.executemany(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        [
            ("Learn FastAPI", 0),
            ("Build Task API", 0),
            ("Push to GitHub", 0),
        ]
    )
    conn.commit()

    cursor.execute("SELECT id, title, done FROM tasks ORDER BY id")
    rows = cursor.fetchall()
    conn.close()

    return {
        "message": "Tasks reset successfully",
        "tasks": [row_to_task(row) for row in rows]
    }