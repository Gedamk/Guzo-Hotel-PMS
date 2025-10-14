# -*- coding: utf-8 -*-
"""
Test script for reporting.py
- Generates charts
- Builds a PDF
- Exports CSV
"""

# test_report_safe.py

from guzo_booking_bot import reporting

dummy_data = {
    "property_name": "Guzo Hotel",
    "total_bookings": 42,
    "total_bookings_last_week": 38,   # Ã°ÂÂÂ¥ shows trend Ã¢Â¬ÂÃ¯Â¸Â
    "occupancy_rate": 68,
    "occupancy_rate_last_week": 72,   # Ã°ÂÂÂ» shows trend Ã¢Â¬ÂÃ¯Â¸Â
    "revenue_total": 120000,
    "revenue_total_last_week": 110000,  # Ã°ÂÂÂ¼ shows trend Ã¢Â¬ÂÃ¯Â¸Â
    "cancellations": 3,
    "cancellations_last_week": 2,     # Ã°ÂÂÂ» shows cancellations worsening
    "repeat_guests": 7,
    "repeat_guests_last_week": 5,     # Ã°ÂÂÂ¼ more loyal guests
    "top_channel": "Direct",
    "yoy_revenue_pct": 12,
    "occupancy_series": [("Mon", 45), ("Tue", 60), ("Wed", 80)],
    "revenue_by_channel": {"Direct": 5000, "OTA": 3000, "Walk-in": 1200}
}

def main():
    print("Running Reporting Tests with Trends...")

    # 1. Generate charts
    charts = reporting.make_charts(dummy_data, "reports/charts")
    print("Charts generated:", charts)

    # 2. Build PDF
    reporting.build_pdf(dummy_data, charts, "reports/weekly_test_trends.pdf")
    print("PDF created at reports/weekly_test_trends.pdf")

    # 3. Export CSV
    reporting.export_csv(dummy_data, "reports/weekly_test_trends.csv")
    print("CSV created at reports/weekly_test_trends.csv")

    print("Ã¢ÂÂ All reporting tests completed!")

if __name__ == "__main__":
    main()

