# -*- coding: utf-8 -*-
"""
guzo_api.main – FastAPI backend for Guzo Guest Assist
-----------------------------------------------------
Exposes JSON APIs for:
 - Daily Manager reports
 - Monthly Owner reports
 - Portfolio Owner reports

This sits on top of the existing guzo_backend reporting modules.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from guzo_api.routers import reports

app = FastAPI(
    title="Guzo API",
    description="Backend API for Guzo Guest Assist dashboards (daily, monthly, portfolio).",
    version="1.0.0",
)

# CORS – allow local frontends (Streamlit, Next.js) during development
origins = [
    "http://localhost:3000",  # Next.js dev
    "http://127.0.0.1:3000",
    "http://localhost:8501",  # Streamlit
    "http://127.0.0.1:8501",
    "http://localhost:8502",
    "http://127.0.0.1:8502",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health_check():
    """Simple health endpoint to verify the API is running."""
    return {"status": "ok", "service": "guzo_api"}


# Include routers
app.include_router(reports.router)
