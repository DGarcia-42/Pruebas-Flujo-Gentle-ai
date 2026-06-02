from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.exceptions import TaskNotFoundError
from app.routers import tasks as tasks_router
from app.routers.auth import router as auth_router


def create_app() -> FastAPI:
    application = FastAPI(title="Task Tracker API", version="0.1.0")

    @application.exception_handler(TaskNotFoundError)
    async def task_not_found_handler(request, exc: TaskNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "Task not found"})

    application.include_router(tasks_router.router, prefix="/api")
    application.include_router(auth_router, prefix="/api")

    return application


app = create_app()
