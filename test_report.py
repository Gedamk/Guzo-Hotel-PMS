# -*- coding: utf-8 -*-
"""
Test script for Guzo Booking System Reporting
"""

import json
import os
from guzo_booking_bot import reporting  # Ã¢ÂÂ import the module

# Paths
DATA_PATH = "guzo_booking_bot/data/dummy_data.json"
REPORTS_DIR = "reports"
PDF_PATH = os.path.join(REPORTS_DIR, "weekly_report_test.pdf")
CSV_PATH = os.path.join(REPORTS_DIR, "weekly_kpis.csv")

def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("[INFO] Loaded dummy dataset for:", data["property_name"])

    charts = reporting.make_charts(data, os.path.join(REPORTS_DIR, "charts"))
    print(f"[OK] Charts generated: {charts}")

    reporting.build_pdf(data, charts, PDF_PATH)
    print(f"[OK] PDF report generated: {PDF_PATH}")

    reporting.export_csv(data, CSV_PATH)
    print(f"[OK] CSV log updated: {CSV_PATH}")

    print("Ã¢ÂÂ Test reporting workflow complete.")

if __name__ == "__main__":
    main()
