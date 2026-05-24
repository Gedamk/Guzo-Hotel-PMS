# -*- coding: utf-8 -*-
"""
guzo_backend.main – FastAPI app for Guzo Guest Assist backend
"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from guzo_backend.modules.food_costing.routes import router as food_costing_router
# -------------------------------------------------
# Environment
# -------------------------------------------------
# Load the project root .env before importing routers. Several routers create
# database engines at import time, so DB credentials must be available first.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # .../guzo_backend
PROJECT_ROOT = os.path.dirname(BASE_DIR)               # .../Guzo
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(dotenv_path=ENV_PATH, override=True)

# -------------------------------------------------
# Telegram / Bot routers (existing project pieces)
# -------------------------------------------------
from .routers import frontdesk as telegram_frontdesk
from .routers import bot_bookings as telegram_bot_bookings
from .routers import availability as telegram_availability
from .routers import bot_availability as telegram_bot_availability

# -------------------------------------------------
# Core API modules
# -------------------------------------------------
from .api_bookings import router as bookings_router  # general bookings API

from guzo_backend.api import bookings_list_api
from guzo_backend.api import rooms_api

from guzo_backend.api.routes_reports import router as reports_router
from guzo_backend.api.reports_daily_api import router as reports_daily_router
from guzo_backend.api.reports_periodic_api import router as reports_periodic_router
from guzo_backend.api.reports_owner_api import router as reports_owner_router

from guzo_backend.api.health_api import router as health_router
from guzo_backend.api.availability_api import router as availability_router
from guzo_backend.api.kpi_api import router as kpi_router
from guzo_backend.api.bookings_actions_api import router as bookings_actions_router
from guzo_backend.api.rooms_status_api import router as rooms_status_router
from guzo_backend.api.rooms_housekeeping_api import router as housekeeping_router
from guzo_backend.api.finance_api import router as finance_router
from guzo_backend.api.checkout_api import router as checkout_router
from guzo_backend.api.night_audit_api import router as night_audit_router
from guzo_backend.api.telegram_booking_api import router as telegram_integration_router
from guzo_backend.api.chat_api import router as chat_router

from guzo_backend.api.debug_bookings_api import router as debug_router
from guzo_backend.api.frontdesk_assign_room_api import router as frontdesk_assign_room_router
from guzo_backend.api.frontdesk_walkin_api import router as frontdesk_walkin_router

# IMPORTANT:
# We DO NOT import or include the old frontdesk_assign_api / frontdesk_assign_router
# anywhere. Only the new frontdesk_assign_room_api is used.


# -------------------------------------------------
# FastAPI app
# -------------------------------------------------
app = FastAPI(
    title="Guzo Guest Assist Backend",
    version="1.0.0",
)

# CORS – allow React frontend to access FastAPI
# -------------------------------------------------
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5176",
    "http://localhost:5177",
    "http://127.0.0.1:5177",
    "http://localhost:5178",
    "http://127.0.0.1:5178",
    "http://192.168.56.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# Health endpoint
# -------------------------------------------------
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "guzo-backend",
        "version": "v1",
    }


# -------------------------------------------------
# Attach routers
# -------------------------------------------------

# Telegram / bot routers (existing project)
app.include_router(telegram_frontdesk.router)
app.include_router(telegram_bot_bookings.router)
app.include_router(telegram_availability.router)
app.include_router(telegram_bot_availability.router)

# Core booking + rooms APIs
app.include_router(bookings_router)                    # /bookings, etc.
app.include_router(bookings_list_api.router)           # reporting-style bookings list
app.include_router(rooms_api.router)                   # rooms master data
app.include_router(food_costing_router)
# Front desk live console + debug
# - frontdesk_assign_room_router: /frontdesk/assign-room
# - frontdesk_walkin_router: /frontdesk/walkin (new walk-in creation)
app.include_router(frontdesk_assign_room_router)       # /frontdesk/assign-room
app.include_router(frontdesk_walkin_router)            # /frontdesk/walkin
app.include_router(debug_router)                       # /debug/... for troubleshooting

# Availability + KPI + actions
app.include_router(availability_router)
app.include_router(kpi_router)
app.include_router(kpi_router, prefix="/kpi", tags=["kpi"])  # backwards-compatible /kpi/kpi/daily
app.include_router(bookings_actions_router)
app.include_router(finance_router)
app.include_router(checkout_router)
app.include_router(night_audit_router)
app.include_router(telegram_integration_router)
app.include_router(chat_router)

# Reports
app.include_router(reports_router)                     # portfolio, monthly, etc.
app.include_router(reports_daily_router)               # daily PDF/Excel report data
app.include_router(reports_periodic_router)            # weekly / monthly periods
app.include_router(reports_owner_router)               # multi-property owner view

# Rooms status / housekeeping
app.include_router(rooms_status_router)
app.include_router(housekeeping_router)

# -------------------------------------------------------------------
# Optional React production build serving
# -------------------------------------------------------------------
# During development, React runs separately from:
#   ~/Desktop/Guzo/guzo_pms_frontend
#   npm run dev
#
# So FastAPI should NOT crash if dashboard_ui/build/static does not exist.
# -------------------------------------------------------------------

REACT_BUILD_DIR = os.path.join(PROJECT_ROOT, "dashboard_ui", "build")
REACT_STATIC_DIR = os.path.join(REACT_BUILD_DIR, "static")
REACT_INDEX_FILE = os.path.join(REACT_BUILD_DIR, "index.html")

if os.path.isdir(REACT_STATIC_DIR):
    app.mount(
        "/static",
        StaticFiles(directory=REACT_STATIC_DIR),
        name="static",
    )

if os.path.isfile(REACT_INDEX_FILE):
    @app.get("/", include_in_schema=False)
    async def serve_react_app():
        return FileResponse(REACT_INDEX_FILE)
else:
    @app.get("/", include_in_schema=False)
    async def api_root():
        return {
            "status": "ok",
            "service": "guzo-backend",
            "message": "Backend API is running. Start the React frontend separately with npm run dev.",
            "frontend_dev_url": "http://localhost:5173",
            "health_url": "/health",
        }
