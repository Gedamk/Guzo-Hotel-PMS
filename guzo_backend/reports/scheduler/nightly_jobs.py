"""
nightly_jobs.py – entry point to run KPI aggregation.
"""

from datetime import date, timedelta
from guzo_backend.reports.aggregations import aggregate_day


def run_for_yesterday() -> None:
    business_date = date.today() - timedelta(days=1)
    aggregate_day(business_date)


def run_for_today() -> None:
    business_date = date.today()
    aggregate_day(business_date)


if __name__ == "__main__":
    run_for_today()
