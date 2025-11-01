# -*- coding: utf-8 -*-
"""
ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ­ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ³ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Guzo Data Analytics Engine
Analyzes health_summaries, failed_logs, retry_logs for the dashboard.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = "storage/logs.db"


def load_table(name):
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(f"SELECT * FROM {name}", conn)
        conn.close()
        return df, None
    except Exception as e:
        return pd.DataFrame(), str(e)


def summarize_health():
    df, err = load_table("health_summaries")
    if df.empty:
        return {"status": "no_data", "error": err or "No health records yet."}

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.sort_values("timestamp", ascending=False)

    total = len(df)
    success_rate = (df["booking_sync_ok"].sum() / total) * 100
    latest_time = df["timestamp"].iloc[-1].strftime("%Y-%m-%d %H:%M")

    avg_health = {
        "total_entries": total,
        "success_rate": round(success_rate, 2),
        "avg_retry": round(df["retry_scheduler_ok"].mean() * 100, 2),
        "avg_webhooks": round(df["webhooks_ok"].mean() * 100, 2),
        "avg_endpoint": round(df["health_endpoint_ok"].mean() * 100, 2),
        "last_update": latest_time,
    }

    return avg_health


def summarize_failures():
    fails, err1 = load_table("failed_logs")
    retries, err2 = load_table("retry_logs")

    return {
        "failed_jobs": len(fails),
        "retry_jobs": len(retries),
        "error": err1 or err2 or None
    }


def trend_health(days=7):
    df, _ = load_table("health_summaries")
    if df.empty:
        return pd.DataFrame()

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["date"] = df["timestamp"].dt.date
    df = df[df["date"] >= (datetime.now().date() - timedelta(days=days))]

    trend = df.groupby("date")[["booking_sync_ok", "retry_scheduler_ok", "webhooks_ok"]].mean().reset_index()
    return trend
