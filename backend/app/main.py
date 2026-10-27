"""RescueRoute AI FastAPI application.

Run from the repository root:
    uvicorn app.main:app --reload --app-dir backend
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import router
from .services.simulation_service import ConflictError, NotFoundError

app = FastAPI(title="RescueRoute AI", version="1.0.0",
              description="Simulated disaster-rescue route planning with BFS, Greedy Best-First and A*.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _err(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"ok": False, "detail": message})


@app.exception_handler(NotFoundError)
async def _not_found(_: Request, exc: NotFoundError):
    return _err(404, str(exc))


@app.exception_handler(ConflictError)
async def _conflict(_: Request, exc: ConflictError):
    return _err(409, str(exc))


@app.exception_handler(ValueError)
async def _bad_value(_: Request, exc: ValueError):
    return _err(400, str(exc))


app.include_router(router)
