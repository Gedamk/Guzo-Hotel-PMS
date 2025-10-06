from fastapi import FastAPI
from backend.routers import bookings

app = FastAPI(
    title="Guzo Booking Bot API",
    description="A modern hospitality booking and guest support API",
    version="1.0.0",
)

@app.get("/")
def read_root():
    return {"message": "🚀 Guzo Booking Bot API is running!"}

# Register routers
app.include_router(bookings.router, prefix="/bookings", tags=["Bookings"])
