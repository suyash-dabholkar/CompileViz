"""
CompileViz backend entry point.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import compiler_routes, grammar_routes, regex_routes

app = FastAPI(
    title="CompileViz API",
    description="Backend for CompileViz: An Interactive Web Platform for "
                "Visualizing Compiler Construction Concepts",
    version="0.1.0",
)

# Local dev always works: Vite's default port, on both hostnames browsers
# use interchangeably. The deployed frontend's URL (Vercel, from
# Milestone 16) is added via the ALLOWED_ORIGINS environment variable
# instead of another code change and redeploy, set it as a comma-
# separated list, e.g. "https://compileviz.vercel.app,https://compileviz-git-main-you.vercel.app"
# (Vercel gives every deployment, including preview ones, its own URL,
# so it's worth listing more than just the main production one).
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
extra_origins = os.environ.get("ALLOWED_ORIGINS", "")
origins += [o.strip() for o in extra_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """A friendly root response, mainly so visiting the bare backend
    URL in a browser (which people demoing this WILL do) shows
    something useful instead of a bare 404.
    """
    return {
        "service": "compileviz-backend",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health_check():
    """Simple liveness check used by the frontend and by CI."""
    return {"status": "ok", "service": "compileviz-backend"}


app.include_router(regex_routes.router, prefix="/api/regex", tags=["regex"])
app.include_router(grammar_routes.router, prefix="/api/grammar", tags=["grammar"])
app.include_router(compiler_routes.router, prefix="/api/compiler", tags=["compiler"])

# Future routers get included here as each milestone lands, e.g.:
# from app.api import parser_routes
# app.include_router(parser_routes.router, prefix="/api/compiler", tags=["compiler"])
