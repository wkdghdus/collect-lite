import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    annotations,
    consensus,
    datasets,
    exports,
    metrics,
    projects,
    reviews,
    suggestions,
    tasks,
    users,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="CollectLite API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_latency_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Response-Time-Ms"] = str(round(elapsed * 1000))
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(projects.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(annotations.router, prefix="/api")
app.include_router(suggestions.router, prefix="/api")
app.include_router(consensus.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(exports.router, prefix="/api")
app.include_router(users.router, prefix="/api")
