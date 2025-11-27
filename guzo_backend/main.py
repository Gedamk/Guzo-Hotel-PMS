# -*- coding: utf-8 -*-
"""
guzo_backend.main – FastAPI app for Guzo Guest Assist backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from guzo_backend.api import bookings_list_api

from guzo_backend.api.routes_reports import router as reports_router
from .api_frontdesk import router as frontdesk_router
from .api_bookings import router as bookings_router
from .routers import frontdesk
from .routers import bot_bookings
from .routers import availability
from .routers import bot_availability
from guzo_backend.api import bookings_list_api
from guzo_backend.api import rooms_api
from guzo_backend.api import bookings_list_api  # example
from guzo_backend.api.reports_daily_api import router as reports_daily_router
from guzo_backend.api.reports_periodic_api import router as reports_periodic_router
from guzo_backend.api.health_api import router as health_router  # coming next
from guzo_backend.api.availability_api import router as availability_router
from guzo_backend.api.kpi_api import router as kpi_router
from guzo_backend.api.bookings_actions_api import router as bookings_actions_router
from guzo_backend.api.reports_owner_api import router as reports_owner_router
from guzo_backend.api.reports_daily_api import router as reports_daily_router
from guzo_backend.api.rooms_status_api import router as rooms_status_router
from guzo_backend.api.rooms_housekeeping_api import router as housekeeping_router
from guzo_backend.api.frontdesk_assign_api import router as frontdeskAssignRouter


app = FastAPI(
    title="Guzo Guest Assist Backend",
    version="0.1.0",
)

app.include_router(availability_router)
app.include_router(kpi_router)
app.include_router(frontdesk.router)
app.include_router(bot_bookings.router)
app.include_router(availability.router)
app.include_router(bot_availability.router)
app.include_router(bookings_list_api.router)
app.include_router(bookings_list_api.router)
app.include_router(rooms_api.router)
app.include_router(bookings_list_api.router)  # existing

app.include_router(reports_daily_router)      # ⬅ add this line
app.include_router(reports_periodic_router)
app.include_router(health_router)
app.include_router(kpi_router, prefix="/kpi", tags=["kpi"])


app.include_router(frontdesk_router)
app.include_router(reports_router)
app.include_router(availability_router)
app.include_router(bookings_actions_router)
app.include_router(reports_owner_router)
app.include_router(reports_daily_router)
app.include_router(rooms_status_router)
app.include_router(housekeeping_router)
app.include_router(frontdeskAssignRouter)



# -------------------------------------------------
# CORS – allow React frontend to access FastAPI
# -------------------------------------------------

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.56.1:3000",   # React dev server on your network
]

# CORS etc…
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
# Routers
# -------------------------------------------------
# Reports (portfolio, monthly, etc.)
app.include_router(reports_router)

# Front desk live daily operational bookings
app.include_router(frontdesk_router, prefix="/frontdesk", tags=["frontdesk"])

# Booking updates (status changes: check-in, check-out)
app.include_router(bookings_router)
