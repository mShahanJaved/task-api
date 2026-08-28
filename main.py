from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from fastapi.exceptions import RequestValidationError

app = FastAPI()

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

tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": False},
    {"id": 2, "title": "Build Task API", "done": False},
    {"id": 3, "title": "Push to GitHub", "done": False},
]

@app.get("/tasks", description="Returns all tasks.")
def get_tasks():
    return tasks

@app.get("/tasks/{task_id}", description="Returns a single task by ID.")
def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task

    return JSONResponse(
        status_code=404,
        content={"error": f"Task {task_id} not found"}
    )

@app.post("/tasks", status_code=201, description="Creates a new task.")
def create_task(task: TaskCreate):
    new_id = max([t["id"] for t in tasks], default=0) + 1

    new_task = {
        "id": new_id,
        "title": task.title,
        "done": False
    }

    tasks.append(new_task)

    return new_task

@app.put("/tasks/{task_id}", description="Updates an existing task.")
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

@app.delete("/tasks/{task_id}", status_code=204, description="Deletes a task.")
def delete_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            tasks.remove(task)
            return

    return JSONResponse(
        status_code=404,
        content={"error": f"Task {task_id} not found"}
    )