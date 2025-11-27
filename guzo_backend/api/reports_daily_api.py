# guzo_backend/api/reports_daily_api.py
#
# FastAPI routes for daily manager / rooms division reports.
#
# Main endpoint:
#   GET /reports/daily-manager?property_code=DRE001&business_date=2025-11-25
#
# Response:
#   PDF file "daily-YYYY-MM-DD.pdf" (downloadable in browser)

import os
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from guzo_backend.reports.daily_manager_pdf import generate_daily_manager_pdf


router = APIRouter(prefix="/reports", tags=["reports-daily"])


@router.get("/daily-manager")
def daily_manager_report(
    property_code: str = Query("DRE001", description="Hotel property code (e.g., DRE001)"),
    business_date: Optional[str] = Query(
        None, description="Business date in YYYY-MM-DD (defaults to today)"
    ),
):
    """
    Generate and return the Daily Manager / Rooms Division PDF.

    - If business_date is omitted, today's date is used.
    - PDF is generated (or overwritten) at project root as daily-YYYY-MM-DD.pdf
    """
    # Parse date
    if business_date is None:
        biz_date = date.today()
    else:
        try:
            biz_date = date.fromisoformat(business_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid business_date format")

    # Generate PDF (catch any errors and expose them clearly)
    try:
        pdf_path = generate_daily_manager_pdf(biz_date, property_code)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating daily PDF: {e}",
        )

    if not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=500,
            detail=f"PDF not found after generation: {pdf_path}",
        )

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=os.path.basename(pdf_path),
    )
