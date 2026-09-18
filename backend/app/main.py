"""
CompileViz backend entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import regex_routes

app = FastAPI(
    title="CompileViz API",
    description="Backend for CompileViz: An Interactive Web Platform for "
                "Visualizing Compiler Construction Concepts",
    version="0.1.0",
)

# During local development the frontend runs on Vite's default port.
# Add your deployed frontend URL here once it's live (Milestone 16).
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Simple liveness check used by the frontend and by CI."""
    return {"status": "ok", "service": "compileviz-backend"}


app.include_router(regex_routes.router, prefix="/api/regex", tags=["regex"])

# Future routers get included here as each milestone lands, e.g.:
# from app.api import grammar_routes
# app.include_router(grammar_routes.router, prefix="/api/grammar", tags=["grammar"])
