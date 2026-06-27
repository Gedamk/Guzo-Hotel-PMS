from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.pms_security_service import require_property_access


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _normalize_property_code(property_code: str) -> str:
    return property_code.strip().upper()


def _table_exists(db: Session, table_name: str) -> bool:
    return bool(
        db.execute(
            text(
                """
                SELECT EXISTS (
                  SELECT 1
                  FROM information_schema.tables
                  WHERE table_name = :table_name
                )
                """
            ),
            {"table_name": table_name},
        ).scalar()
    )


def _table_columns(db: Session, table_name: str) -> set[str]:
    if not _table_exists(db, table_name):
        return set()
    rows = db.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :table_name
            """
        ),
        {"table_name": table_name},
    ).scalars()
    return {str(row) for row in rows}


def _column_sql(columns: set[str], column_name: str, fallback: str = "NULL") -> str:
    return column_name if column_name in columns else fallback


def _count_bookings(db: Session, property_code: str, business_date: date) -> dict[str, int]:
    columns = _table_columns(db, "bookings")
    if not columns:
        return {
            "arrivals_today_count": 0,
            "departures_today_count": 0,
            "in_house_count": 0,
            "cancellation_count": 0,
            "no_show_risk_count": 0,
            "pending_departure_count": 0,
            "checkout_blocked_by_balance_count": 0,
            "unpaid_departure_folio_count": 0,
            "vip_arrival_count": 0,
        }

    status_expr = _column_sql(columns, "booking_status", "''")
    payment_expr = _column_sql(columns, "payment_status", "''")
    balance_expr = _column_sql(columns, "balance_due", "0")
    notes_expr = _column_sql(columns, "notes", "''")
    vip_expr = " || ' ' || ".join(
        _column_sql(columns, column_name, "''")
        for column_name in ["channel", "source", "vip_notes", "special_requests"]
    )
    room_expr = _column_sql(columns, "room_number", "NULL")

    row = db.execute(
        text(
            f"""
            SELECT
              COUNT(*) FILTER (WHERE check_in_date = :business_date) AS arrivals_today_count,
              COUNT(*) FILTER (WHERE check_out_date = :business_date) AS departures_today_count,
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE({status_expr}, '')) IN ('in_house', 'checked_in', 'checked in')
              ) AS in_house_count,
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE({status_expr}, '')) IN ('cancelled', 'canceled')
              ) AS cancellation_count,
              COUNT(*) FILTER (
                WHERE check_in_date = :business_date
                  AND LOWER(COALESCE({status_expr}, '')) IN ('confirmed', 'reserved', 'pending_guarantee', 'pending')
              ) AS no_show_risk_count,
              COUNT(*) FILTER (
                WHERE check_out_date = :business_date
                  AND LOWER(COALESCE({status_expr}, '')) NOT IN ('checked_out', 'cancelled', 'canceled', 'no_show', 'no-show')
              ) AS pending_departure_count,
              COUNT(*) FILTER (
                WHERE check_out_date = :business_date
                  AND (
                    COALESCE({balance_expr}, 0) > 0
                    OR LOWER(COALESCE({payment_expr}, '')) IN ('pending', 'unpaid', 'pending_guarantee')
                  )
              ) AS checkout_blocked_by_balance_count,
              COUNT(*) FILTER (
                WHERE check_out_date = :business_date
                  AND (
                    COALESCE({balance_expr}, 0) > 0
                    OR LOWER(COALESCE({payment_expr}, '')) IN ('pending', 'unpaid', 'pending_guarantee')
                  )
              ) AS unpaid_departure_folio_count,
              COUNT(*) FILTER (
                WHERE check_in_date = :business_date
                  AND LOWER(COALESCE({vip_expr}, '') || ' ' || COALESCE({notes_expr}, '')) LIKE '%vip%'
              ) AS vip_arrival_count
            FROM bookings
            WHERE property_code = :property_code
              AND (
                check_in_date = :business_date
                OR check_out_date = :business_date
                OR LOWER(COALESCE({status_expr}, '')) IN ('in_house', 'checked_in', 'checked in', 'cancelled', 'canceled')
                OR {room_expr} IS NOT NULL
              )
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().first()
    return {key: int((row or {}).get(key) or 0) for key in [
        "arrivals_today_count",
        "departures_today_count",
        "in_house_count",
        "cancellation_count",
        "no_show_risk_count",
        "pending_departure_count",
        "checkout_blocked_by_balance_count",
        "unpaid_departure_folio_count",
        "vip_arrival_count",
    ]}


def _count_public_booking_requests(db: Session, property_code: str) -> dict[str, int]:
    columns = _table_columns(db, "public_booking_requests")
    if not columns:
        return {"booking_request_count": 0, "pending_deposit_count": 0}

    status_expr = _column_sql(columns, "booking_status", "''")
    deposit_expr = _column_sql(columns, "deposit_status", "''")
    row = db.execute(
        text(
            f"""
            SELECT
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE({status_expr}, '')) IN ('pending_request', 'new', 'requested', 'reviewed', 'tentative', 'deposit_requested', 'deposit_required')
              ) AS booking_request_count,
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE({deposit_expr}, 'pending')) IN ('pending', 'requested', 'unpaid')
                  OR LOWER(COALESCE({status_expr}, '')) IN ('deposit_requested', 'deposit_required')
              ) AS pending_deposit_count
            FROM public_booking_requests
            WHERE property_code = :property_code
              AND LOWER(COALESCE({status_expr}, '')) <> 'converted'
            """
        ),
        {"property_code": property_code},
    ).mappings().first()
    return {
        "booking_request_count": int((row or {}).get("booking_request_count") or 0),
        "pending_deposit_count": int((row or {}).get("pending_deposit_count") or 0),
    }


def _count_housekeeping(db: Session, property_code: str, business_date: date) -> dict[str, int]:
    rooms_columns = _table_columns(db, "rooms")
    hk_columns = _table_columns(db, "housekeeping_status")
    if not rooms_columns and not hk_columns:
        return {
            "dirty_room_count": 0,
            "cleaning_room_count": 0,
            "clean_room_count": 0,
            "inspected_room_count": 0,
            "out_of_order_count": 0,
            "out_of_service_count": 0,
        }

    base_table = "rooms" if rooms_columns else "housekeeping_status"
    base_status = _column_sql(rooms_columns if rooms_columns else hk_columns, "hk_status", "'vacant_clean'")
    base_filter = "property_code = :property_code"
    if base_table == "housekeeping_status":
        base_filter += " AND business_date = :business_date"

    hk_join = ""
    status_expr = f"LOWER(COALESCE({base_status}, 'vacant_clean'))"
    if base_table == "rooms" and hk_columns:
        room_status_expr = "r.hk_status" if "hk_status" in rooms_columns else "'vacant_clean'"
        hk_join = """
            LEFT JOIN housekeeping_status hs
              ON hs.property_code = r.property_code
             AND CAST(hs.room_number AS TEXT) = CAST(r.room_number AS TEXT)
             AND hs.business_date = :business_date
        """
        status_expr = f"LOWER(COALESCE(hs.hk_status, {room_status_expr}, 'vacant_clean'))"
        from_expr = "rooms r"
        where_expr = "r.property_code = :property_code"
    else:
        from_expr = base_table
        where_expr = base_filter

    row = db.execute(
        text(
            f"""
            SELECT
              COUNT(*) FILTER (WHERE {status_expr} LIKE '%dirty%') AS dirty_room_count,
              COUNT(*) FILTER (WHERE {status_expr} LIKE '%progress%' OR {status_expr} LIKE '%cleaning%') AS cleaning_room_count,
              COUNT(*) FILTER (
                WHERE {status_expr} LIKE '%clean%'
                  AND {status_expr} NOT LIKE '%dirty%'
                  AND {status_expr} NOT LIKE '%cleaning%'
                  AND {status_expr} NOT LIKE '%progress%'
              ) AS clean_room_count,
              COUNT(*) FILTER (WHERE {status_expr} LIKE '%inspect%') AS inspected_room_count,
              COUNT(*) FILTER (WHERE {status_expr} IN ('out_of_order', 'ooo') OR {status_expr} LIKE '%out of order%') AS out_of_order_count,
              COUNT(*) FILTER (WHERE {status_expr} = 'out_of_service' OR {status_expr} LIKE '%out of service%') AS out_of_service_count
            FROM {from_expr}
            {hk_join}
            WHERE {where_expr}
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().first()
    return {key: int((row or {}).get(key) or 0) for key in [
        "dirty_room_count",
        "cleaning_room_count",
        "clean_room_count",
        "inspected_room_count",
        "out_of_order_count",
        "out_of_service_count",
    ]}


def _count_folios(db: Session, property_code: str, business_date: date) -> dict[str, int]:
    columns = _table_columns(db, "folios")
    if not columns:
        return {"unpaid_folio_count": 0, "city_ledger_transfer_count": 0}

    balance_expr = _column_sql(columns, "balance", "0")
    status_expr = _column_sql(columns, "status", "'open'")
    transferred_expr = _column_sql(columns, "transferred_to", "NULL")
    transferred_at_filter = "AND transferred_at::date = :business_date" if "transferred_at" in columns else ""
    row = db.execute(
        text(
            f"""
            SELECT
              COUNT(*) FILTER (
                WHERE COALESCE({balance_expr}, 0) > 0
                  AND LOWER(COALESCE({status_expr}, 'open')) NOT IN ('closed', 'settled', 'void')
              ) AS unpaid_folio_count,
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE({transferred_expr}, '')) IN ('city_ledger', 'city ledger', 'ar', 'accounts_receivable')
                {transferred_at_filter}
              ) AS city_ledger_transfer_count
            FROM folios
            WHERE property_code = :property_code
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().first()
    return {
        "unpaid_folio_count": int((row or {}).get("unpaid_folio_count") or 0),
        "city_ledger_transfer_count": int((row or {}).get("city_ledger_transfer_count") or 0),
    }


def _count_cashier_sessions(db: Session, property_code: str, business_date: date) -> dict[str, int]:
    columns = _table_columns(db, "cashier_sessions")
    if not columns:
        return {
            "cashier_shift_open_count": 0,
            "cashier_shift_closed_count": 0,
            "cashier_shift_variance_count": 0,
        }

    status_expr = _column_sql(columns, "status", "'closed'")
    variance_expr = _column_sql(columns, "variance", "0")
    row = db.execute(
        text(
            f"""
            SELECT
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE({status_expr}, '')) IN ('open', 'active')
              ) AS cashier_shift_open_count,
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE({status_expr}, '')) IN ('closed', 'settled')
              ) AS cashier_shift_closed_count,
              COUNT(*) FILTER (
                WHERE ABS(COALESCE({variance_expr}, 0)) > 0
                  AND LOWER(COALESCE({status_expr}, '')) IN ('variance_review', 'open')
              ) AS cashier_shift_variance_count
            FROM cashier_sessions
            WHERE property_code = :property_code
              AND business_date = :business_date
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().first()
    return {
        "cashier_shift_open_count": int((row or {}).get("cashier_shift_open_count") or 0),
        "cashier_shift_closed_count": int((row or {}).get("cashier_shift_closed_count") or 0),
        "cashier_shift_variance_count": int((row or {}).get("cashier_shift_variance_count") or 0),
    }


def _count_fnb_summary(db: Session, property_code: str, business_date: date) -> dict[str, float | int | None]:
    summary: dict[str, float | int | None] = {
        "food_cost_percent": None,
        "beverage_cost_percent": None,
        "fnb_inventory_value": 0.0,
        "fnb_waste_today": 0.0,
        "fnb_store_issues_today": 0,
        "fnb_receiving_today": 0,
        "fnb_supplier_variance_count": 0,
        "fnb_high_cost_alert_count": 0,
        "fnb_daily_sales": 0.0,
        "fnb_gross_profit": 0.0,
    }

    movement_columns = _table_columns(db, "inventory_movements")
    if movement_columns:
        movement_type_expr = _column_sql(movement_columns, "movement_type", "''")
        stock_value_expr = _column_sql(movement_columns, "stock_value", "0")
        created_at_filter = "AND created_at::date = :business_date" if "created_at" in movement_columns else ""
        movement_row = db.execute(
            text(
                f"""
                SELECT
                  COALESCE(SUM(
                    CASE
                      WHEN UPPER(COALESCE({movement_type_expr}, '')) IN ('OPENING', 'PURCHASE_RECEIVED', 'ADJUSTMENT') THEN COALESCE({stock_value_expr}, 0)
                      WHEN UPPER(COALESCE({movement_type_expr}, '')) IN ('KITCHEN_ISSUE', 'WASTAGE') THEN -COALESCE({stock_value_expr}, 0)
                      ELSE 0
                    END
                  ), 0) AS inventory_value,
                  COALESCE(SUM(CASE WHEN UPPER(COALESCE({movement_type_expr}, '')) = 'WASTAGE' {created_at_filter} THEN COALESCE({stock_value_expr}, 0) ELSE 0 END), 0) AS waste_today,
                  COUNT(*) FILTER (WHERE UPPER(COALESCE({movement_type_expr}, '')) = 'KITCHEN_ISSUE' {created_at_filter}) AS store_issues_today,
                  COALESCE(SUM(CASE WHEN UPPER(COALESCE({movement_type_expr}, '')) = 'KITCHEN_ISSUE' {created_at_filter} THEN COALESCE({stock_value_expr}, 0) ELSE 0 END), 0) AS issued_value_today,
                  COUNT(*) FILTER (WHERE UPPER(COALESCE({movement_type_expr}, '')) = 'PURCHASE_RECEIVED' {created_at_filter}) AS receiving_from_movements
                FROM inventory_movements
                WHERE property_code = :property_code
                """
            ),
            {"property_code": property_code, "business_date": business_date},
        ).mappings().first()
        summary["fnb_inventory_value"] = max(float((movement_row or {}).get("inventory_value") or 0), 0.0)
        summary["fnb_waste_today"] = float((movement_row or {}).get("waste_today") or 0)
        summary["fnb_store_issues_today"] = int((movement_row or {}).get("store_issues_today") or 0)
        issued_value_today = float((movement_row or {}).get("issued_value_today") or 0)
        receiving_from_movements = int((movement_row or {}).get("receiving_from_movements") or 0)
    else:
        issued_value_today = 0.0
        receiving_from_movements = 0

    wastage_columns = _table_columns(db, "fnb_wastage_records")
    if wastage_columns:
        cost_expr = _column_sql(wastage_columns, "cost", "0")
        created_at_filter = "AND created_at::date = :business_date" if "created_at" in wastage_columns else ""
        wastage_value = db.execute(
            text(
                f"""
                SELECT COALESCE(SUM(COALESCE({cost_expr}, 0)), 0)
                FROM fnb_wastage_records
                WHERE property_code = :property_code
                  {created_at_filter}
                """
            ),
            {"property_code": property_code, "business_date": business_date},
        ).scalar()
        summary["fnb_waste_today"] = max(float(summary["fnb_waste_today"] or 0), float(wastage_value or 0))

    requisition_columns = _table_columns(db, "fnb_kitchen_requisitions")
    if requisition_columns:
        status_expr = _column_sql(requisition_columns, "status", "''")
        created_at_filter = "AND created_at::date = :business_date" if "created_at" in requisition_columns else ""
        issued_requisitions = db.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM fnb_kitchen_requisitions
                WHERE property_code = :property_code
                  AND LOWER(COALESCE({status_expr}, '')) IN ('issued', 'closed')
                  {created_at_filter}
                """
            ),
            {"property_code": property_code, "business_date": business_date},
        ).scalar()
        summary["fnb_store_issues_today"] = max(
            int(summary["fnb_store_issues_today"] or 0),
            int(issued_requisitions or 0),
        )

    sale_columns = _table_columns(db, "pos_sales")
    beverage_sales = 0.0
    if sale_columns:
        revenue_expr = _column_sql(sale_columns, "total_revenue", "0")
        outlet_expr = _column_sql(sale_columns, "outlet_name", "''")
        item_expr = _column_sql(sale_columns, "menu_item_name", "''")
        if "business_date" in sale_columns:
            date_filter = "business_date = :business_date_text"
        elif "created_at" in sale_columns:
            date_filter = "created_at::date = :business_date"
        else:
            date_filter = "1 = 1"
        sales_row = db.execute(
            text(
                f"""
                SELECT
                  COALESCE(SUM(COALESCE({revenue_expr}, 0)), 0) AS daily_sales,
                  COALESCE(SUM(
                    CASE
                      WHEN LOWER(COALESCE({outlet_expr}, '') || ' ' || COALESCE({item_expr}, '')) LIKE '%bar%'
                        OR LOWER(COALESCE({outlet_expr}, '') || ' ' || COALESCE({item_expr}, '')) LIKE '%beverage%'
                        OR LOWER(COALESCE({outlet_expr}, '') || ' ' || COALESCE({item_expr}, '')) LIKE '%drink%'
                        OR LOWER(COALESCE({outlet_expr}, '') || ' ' || COALESCE({item_expr}, '')) LIKE '%juice%'
                        OR LOWER(COALESCE({outlet_expr}, '') || ' ' || COALESCE({item_expr}, '')) LIKE '%coffee%'
                      THEN COALESCE({revenue_expr}, 0)
                      ELSE 0
                    END
                  ), 0) AS beverage_sales
                FROM pos_sales
                WHERE property_code = :property_code
                  AND {date_filter}
                """
            ),
            {
                "property_code": property_code,
                "business_date": business_date,
                "business_date_text": business_date.isoformat(),
            },
        ).mappings().first()
        summary["fnb_daily_sales"] = float((sales_row or {}).get("daily_sales") or 0)
        beverage_sales = float((sales_row or {}).get("beverage_sales") or 0)

    recipe_columns = _table_columns(db, "recipes")
    if recipe_columns:
        cost_pct_expr = _column_sql(recipe_columns, "food_cost_percentage", "0")
        target_expr = _column_sql(recipe_columns, "target_cost_percentage", "35")
        outlet_expr = _column_sql(recipe_columns, "outlet_name", "''")
        name_expr = _column_sql(recipe_columns, "name", "''")
        recipe_row = db.execute(
            text(
                f"""
                SELECT
                  ROUND(AVG(COALESCE({cost_pct_expr}, 0)), 2) AS recipe_food_cost_percent,
                  ROUND(AVG(CASE
                    WHEN LOWER(COALESCE({outlet_expr}, '') || ' ' || COALESCE({name_expr}, '')) LIKE '%bar%'
                      OR LOWER(COALESCE({outlet_expr}, '') || ' ' || COALESCE({name_expr}, '')) LIKE '%beverage%'
                      OR LOWER(COALESCE({outlet_expr}, '') || ' ' || COALESCE({name_expr}, '')) LIKE '%drink%'
                      OR LOWER(COALESCE({outlet_expr}, '') || ' ' || COALESCE({name_expr}, '')) LIKE '%juice%'
                      OR LOWER(COALESCE({outlet_expr}, '') || ' ' || COALESCE({name_expr}, '')) LIKE '%coffee%'
                    THEN COALESCE({cost_pct_expr}, 0)
                    ELSE NULL
                  END), 2) AS beverage_cost_percent,
                  COUNT(*) FILTER (WHERE COALESCE({cost_pct_expr}, 0) > COALESCE({target_expr}, 35)) AS high_cost_recipe_count
                FROM recipes
                WHERE property_code = :property_code
                """
            ),
            {"property_code": property_code},
        ).mappings().first()
        if float(summary["fnb_daily_sales"] or 0) > 0:
            summary["food_cost_percent"] = round((issued_value_today / float(summary["fnb_daily_sales"] or 1)) * 100, 2)
        else:
            summary["food_cost_percent"] = float((recipe_row or {}).get("recipe_food_cost_percent") or 0)
        summary["beverage_cost_percent"] = float((recipe_row or {}).get("beverage_cost_percent") or 0)
        high_cost_recipe_count = int((recipe_row or {}).get("high_cost_recipe_count") or 0)
    else:
        high_cost_recipe_count = 0

    if summary["beverage_cost_percent"] is None and beverage_sales > 0:
        summary["beverage_cost_percent"] = round((issued_value_today / beverage_sales) * 100, 2)

    grn_columns = _table_columns(db, "goods_received")
    if grn_columns:
        created_at_filter = "AND created_at::date = :business_date" if "created_at" in grn_columns else ""
        rejected_expr = _column_sql(grn_columns, "rejected_qty", "0")
        grn_row = db.execute(
            text(
                f"""
                SELECT
                  COUNT(*) FILTER (WHERE 1 = 1 {created_at_filter}) AS receiving_today,
                  COUNT(*) FILTER (WHERE COALESCE({rejected_expr}, 0) > 0 {created_at_filter}) AS rejected_receiving_count
                FROM goods_received
                WHERE property_code = :property_code
                """
            ),
            {"property_code": property_code, "business_date": business_date},
        ).mappings().first()
        summary["fnb_receiving_today"] = int((grn_row or {}).get("receiving_today") or receiving_from_movements)
        rejected_receiving_count = int((grn_row or {}).get("rejected_receiving_count") or 0)
    else:
        summary["fnb_receiving_today"] = receiving_from_movements
        rejected_receiving_count = 0

    stock_count_columns = _table_columns(db, "fnb_stock_counts")
    if stock_count_columns:
        variance_expr = _column_sql(stock_count_columns, "variance_value", "0")
        approved_expr = _column_sql(stock_count_columns, "approved_by", "NULL")
        created_at_filter = "AND created_at::date = :business_date" if "created_at" in stock_count_columns else ""
        variance_count = db.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM fnb_stock_counts
                WHERE property_code = :property_code
                  AND ABS(COALESCE({variance_expr}, 0)) > 0
                  AND {approved_expr} IS NULL
                  {created_at_filter}
                """
            ),
            {"property_code": property_code, "business_date": business_date},
        ).scalar()
        stock_variance_count = int(variance_count or 0)
    else:
        stock_variance_count = 0

    alert_columns = _table_columns(db, "food_cost_alerts")
    if alert_columns:
        severity_expr = _column_sql(alert_columns, "severity", "''")
        created_at_filter = "AND created_at::date = :business_date" if "created_at" in alert_columns else ""
        alert_count = db.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM food_cost_alerts
                WHERE property_code = :property_code
                  AND LOWER(COALESCE({severity_expr}, '')) IN ('high', 'critical', 'danger')
                  {created_at_filter}
                """
            ),
            {"property_code": property_code, "business_date": business_date},
        ).scalar()
        alert_count = int(alert_count or 0)
    else:
        alert_count = 0

    summary["fnb_supplier_variance_count"] = rejected_receiving_count + stock_variance_count
    summary["fnb_high_cost_alert_count"] = alert_count + high_cost_recipe_count
    summary["fnb_gross_profit"] = round(
        float(summary["fnb_daily_sales"] or 0) - issued_value_today - float(summary["fnb_waste_today"] or 0),
        2,
    )
    return summary


def _ensure_guest_feedback_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS guest_feedback (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                booking_id INTEGER,
                guest_name VARCHAR(150),
                rating NUMERIC(3, 2),
                feedback_source VARCHAR(50),
                comment TEXT,
                status VARCHAR(50) DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS booking_id INTEGER"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS guest_name VARCHAR(150)"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS rating NUMERIC(3, 2)"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS feedback_source VARCHAR(50)"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS comment TEXT"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'new'"))
    db.execute(text("ALTER TABLE guest_feedback ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))


def _outstanding_balance(db: Session, property_code: str, business_date: date) -> float:
    if _table_exists(db, "folio_transactions"):
        value = db.execute(
            text(
                """
                SELECT COALESCE(SUM(
                    CASE
                      WHEN LOWER(COALESCE(txn_type, '')) = 'charge' THEN amount
                      WHEN LOWER(COALESCE(txn_type, '')) = 'payment' THEN -amount
                      WHEN LOWER(COALESCE(txn_type, '')) = 'refund' THEN amount
                      ELSE 0
                    END
                ), 0) AS outstanding_balance
                FROM folio_transactions
                WHERE property_code = :property_code
                  AND business_date <= :business_date
                """
            ),
            {"property_code": property_code, "business_date": business_date},
        ).scalar()
        return max(float(value or 0), 0.0)

    if _table_exists(db, "folios"):
        value = db.execute(
            text(
                """
                SELECT COALESCE(SUM(COALESCE(balance, 0)), 0)
                FROM folios
                WHERE property_code = :property_code
                  AND COALESCE(status, 'open') = 'open'
                """
            ),
            {"property_code": property_code},
        ).scalar()
        return max(float(value or 0), 0.0)

    return 0.0


def _folio_transaction_total(
    db: Session,
    property_code: str,
    business_date: date,
    txn_type: str,
) -> float:
    if not _table_exists(db, "folio_transactions"):
        return 0.0
    value = db.execute(
        text(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM folio_transactions
            WHERE property_code = :property_code
              AND business_date = :business_date
              AND LOWER(COALESCE(txn_type, '')) = :txn_type
            """
        ),
        {
            "property_code": property_code,
            "business_date": business_date,
            "txn_type": txn_type,
        },
    ).scalar()
    return float(value or 0)


@router.get("/operational-summary")
def get_dashboard_operational_summary(
    property_code: str = Query(..., min_length=1),
    business_date: date = Query(...),
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = _normalize_property_code(property_code)
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    _ensure_guest_feedback_table(db)

    feedback = db.execute(
        text(
            """
            SELECT
              ROUND(AVG(rating), 2) AS guest_satisfaction_score,
              COUNT(*) AS feedback_count,
              COUNT(*) FILTER (WHERE created_at::date = :business_date) AS guest_feedback_today_count,
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE(status, 'new')) IN ('complaint', 'open_complaint', 'open')
              ) AS complaints_open,
              COUNT(*) FILTER (
                WHERE LOWER(COALESCE(status, 'new')) IN ('service_recovery', 'recovery_open')
              ) AS service_recovery_cases
            FROM guest_feedback
            WHERE property_code = :property_code
            """
        ),
        {"property_code": property_code, "business_date": business_date},
    ).mappings().first()
    db.commit()

    booking_counts = _count_bookings(db, property_code, business_date)
    request_counts = _count_public_booking_requests(db, property_code)
    housekeeping_counts = _count_housekeeping(db, property_code, business_date)
    folio_counts = _count_folios(db, property_code, business_date)
    cashier_counts = _count_cashier_sessions(db, property_code, business_date)
    fnb_counts = _count_fnb_summary(db, property_code, business_date)
    open_cashier_shift_count = cashier_counts["cashier_shift_open_count"]
    housekeeping_discrepancy_count = (
        housekeeping_counts["out_of_order_count"] + housekeeping_counts["out_of_service_count"]
    )
    night_audit_blocker_count = (
        booking_counts["unpaid_departure_folio_count"]
        + open_cashier_shift_count
        + cashier_counts["cashier_shift_variance_count"]
        + housekeeping_discrepancy_count
    )

    return {
        "property_code": property_code,
        "business_date": business_date.isoformat(),
        "outstanding_balance": _outstanding_balance(db, property_code, business_date),
        "payments_collected": _folio_transaction_total(db, property_code, business_date, "payment"),
        "refunds": _folio_transaction_total(db, property_code, business_date, "refund"),
        "guest_satisfaction_score": float(feedback["guest_satisfaction_score"] or 0) if feedback else 0,
        "complaints_open": int(feedback["complaints_open"] or 0) if feedback else 0,
        "service_recovery_cases": int(feedback["service_recovery_cases"] or 0) if feedback else 0,
        "feedback_count": int(feedback["feedback_count"] or 0) if feedback else 0,
        "cashier_shift_open_count": cashier_counts["cashier_shift_open_count"],
        "cashier_shift_closed_count": cashier_counts["cashier_shift_closed_count"],
        "cashier_shift_variance_count": cashier_counts["cashier_shift_variance_count"],
        "city_ledger_transfer_count": folio_counts["city_ledger_transfer_count"],
        "unpaid_folio_count": folio_counts["unpaid_folio_count"],
        "checkout_blocked_by_balance_count": booking_counts["checkout_blocked_by_balance_count"],
        "night_audit_ready": night_audit_blocker_count == 0,
        "night_audit_blocker_count": night_audit_blocker_count,
        "pending_departure_count": booking_counts["pending_departure_count"],
        "open_cashier_shift_count": open_cashier_shift_count,
        "housekeeping_discrepancy_count": housekeeping_discrepancy_count,
        "unpaid_departure_folio_count": booking_counts["unpaid_departure_folio_count"],
        "dirty_room_count": housekeeping_counts["dirty_room_count"],
        "cleaning_room_count": housekeeping_counts["cleaning_room_count"],
        "clean_room_count": housekeeping_counts["clean_room_count"],
        "inspected_room_count": housekeeping_counts["inspected_room_count"],
        "out_of_order_count": housekeeping_counts["out_of_order_count"],
        "out_of_service_count": housekeeping_counts["out_of_service_count"],
        "open_complaint_count": int(feedback["complaints_open"] or 0) if feedback else 0,
        "service_recovery_open_count": int(feedback["service_recovery_cases"] or 0) if feedback else 0,
        "guest_feedback_today_count": int(feedback["guest_feedback_today_count"] or 0) if feedback else 0,
        "vip_arrival_count": booking_counts["vip_arrival_count"],
        "arrivals_today_count": booking_counts["arrivals_today_count"],
        "departures_today_count": booking_counts["departures_today_count"],
        "in_house_count": booking_counts["in_house_count"],
        "pending_deposit_count": request_counts["pending_deposit_count"],
        "booking_request_count": request_counts["booking_request_count"],
        "cancellation_count": booking_counts["cancellation_count"],
        "no_show_risk_count": booking_counts["no_show_risk_count"],
        **fnb_counts,
    }
