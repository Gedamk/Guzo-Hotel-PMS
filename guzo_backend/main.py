# -*- coding: utf-8 -*-
"""
guzo_backend.main – FastAPI app for Guzo Guest Assist backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

from guzo_backend.api.frontdesk_bookings_api import router as frontdesk_bookings_router
from guzo_backend.api.debug_bookings_api import router as debug_router
from guzo_backend.api.frontdesk_assign_room_api import router as frontdesk_assign_room_router
from guzo_backend.api.frontdesk_walkin_api import router as frontdesk_walkin_router
from guzo_backend.api.rooms_housekeeping_api import router as housekeeping_router

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

# -------------------------------------------------
# CORS – allow React frontend to access FastAPI
# -------------------------------------------------
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.56.1:3000",  # React dev server on your network
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

# Front desk live console + debug
# - frontdesk_bookings_router: /frontdesk/bookings, used by React FrontDeskConsole
# - frontdesk_assign_room_router: /frontdesk/assign-room
# - frontdesk_walkin_router: /frontdesk/walkin (new walk-in creation)
app.include_router(frontdesk_bookings_router)          # already has prefix="/frontdesk"
app.include_router(frontdesk_assign_room_router)       # /frontdesk/assign-room
app.include_router(frontdesk_walkin_router)            # /frontdesk/walkin
app.include_router(debug_router)                       # /debug/... for troubleshooting

# Availability + KPI + actions
app.include_router(availability_router)
app.include_router(kpi_router, prefix="/kpi", tags=["kpi"])
app.include_router(bookings_actions_router)

# Reports
app.include_router(reports_router)                     # portfolio, monthly, etc.
app.include_router(reports_daily_router)               # daily PDF/Excel report data
app.include_router(reports_periodic_router)            # weekly / monthly periods
app.include_router(reports_owner_router)               # multi-property owner view

# Rooms status / housekeeping
app.include_router(rooms_status_router)
app.include_router(housekeeping_router)
