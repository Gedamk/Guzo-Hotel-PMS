from fastapi import APIRouter, Depends, Response
from datetime import date
from ..services.reports_daily import build_daily_report
from ..utils.export_pdf import render_daily_pdf
from ..utils.export_excel import render_daily_excel
import logging
logger = logging.getLogger("guzo.reports")

router = APIRouter()

@router.get("/reports/daily/pdf")
def export_daily_pdf(business_date: date, db=Depends(get_db)):
    data = build_daily_report(db, business_date)
    pdf_bytes = render_daily_pdf(data)
    return Response(pdf_bytes, media_type="application/pdf")


@router.get("/reports/daily/excel")
def export_daily_excel(business_date: date, db=Depends(get_db)):
    data = build_daily_report(db, business_date)
    xls_bytes = render_daily_excel(data)
    return Response(
        xls_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
