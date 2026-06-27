from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


ROOM_BASE_RATES_ETB: dict[str, float] = {
    "standard": 5200.0,
    "deluxe": 6500.0,
    "twin": 5600.0,
    "family": 7200.0,
    "suite": 11000.0,
}

RATE_PLANS: dict[str, dict[str, Any]] = {
    "BAR": {
        "label": "Best Available Rate",
        "multiplier": 1.0,
        "deposit_percent": 0.25,
        "guarantee_required": True,
        "policy": "Flexible cancellation until 18:00 hotel time one day before arrival; first night may apply after cutoff.",
    },
    "CORP": {
        "label": "Corporate Preferred",
        "multiplier": 0.9,
        "deposit_percent": 0.0,
        "guarantee_required": True,
        "policy": "Corporate guarantee required; cancellation follows the approved account agreement.",
    },
    "GRP10": {
        "label": "Group 10+ Rooms",
        "multiplier": 0.85,
        "deposit_percent": 0.3,
        "guarantee_required": True,
        "policy": "Group deposit and rooming-list cutoff required before final confirmation.",
    },
}

SERVICE_CHARGE_PERCENT = 0.10
TAX_PERCENT = 0.15
WEEKEND_SURCHARGE_PERCENT = 0.10
SEASONAL_SURCHARGE_PERCENT = 0.15
HIGH_SEASON_MONTHS = {7, 8, 12}
EXTRA_ADULT_ETB = 800.0
EXTRA_CHILD_ETB = 400.0


def _money(value: float) -> float:
    return round(float(value or 0), 2)


def _normalize_room_key(room_type: str | None) -> str:
    value = str(room_type or "").strip().lower()
    for key in ROOM_BASE_RATES_ETB:
        if key in value:
            return key
    return "standard"


def _nights(check_in: date, check_out: date) -> int:
    return max((check_out - check_in).days, 1)


def _count_weekend_nights(check_in: date, check_out: date) -> int:
    weekend_nights = 0
    current = check_in
    while current < check_out:
        if current.weekday() in {4, 5}:
            weekend_nights += 1
        current += timedelta(days=1)
    return weekend_nights


def ensure_rate_configuration_tables(db: Session, property_code: str = "DRE001") -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS rate_plans (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                code VARCHAR(20) NOT NULL,
                name VARCHAR(150) NOT NULL,
                multiplier NUMERIC(8, 4) DEFAULT 1,
                requires_manager_approval BOOLEAN DEFAULT FALSE,
                cancellation_policy TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                UNIQUE(property_code, code)
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_rate_plans_property_code_code
            ON rate_plans (property_code, code)
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS room_type_rates (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                room_type VARCHAR(100) NOT NULL,
                base_rate_etb NUMERIC(12, 2) NOT NULL,
                currency VARCHAR(10) DEFAULT 'ETB',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                UNIQUE(property_code, room_type)
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_room_type_rates_property_code_room_type
            ON room_type_rates (property_code, room_type)
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS tax_service_rules (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                rule_name VARCHAR(120) NOT NULL,
                tax_percent NUMERIC(8, 4) DEFAULT 0.15,
                service_charge_percent NUMERIC(8, 4) DEFAULT 0.10,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                UNIQUE(property_code, rule_name)
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_tax_service_rules_property_code_rule_name
            ON tax_service_rules (property_code, rule_name)
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS season_rules (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                rule_name VARCHAR(120) NOT NULL,
                start_month INTEGER NOT NULL,
                end_month INTEGER NOT NULL,
                surcharge_percent NUMERIC(8, 4) DEFAULT 0.15,
                weekend_surcharge_percent NUMERIC(8, 4) DEFAULT 0.10,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS deposit_policies (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                rate_code VARCHAR(20) NOT NULL,
                deposit_percent NUMERIC(8, 4) DEFAULT 0.25,
                guarantee_required BOOLEAN DEFAULT TRUE,
                policy_text TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                UNIQUE(property_code, rate_code)
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_deposit_policies_property_code_rate_code
            ON deposit_policies (property_code, rate_code)
            """
        )
    )
    _seed_rate_configuration_defaults(db, property_code)


def _seed_rate_configuration_defaults(db: Session, property_code: str) -> None:
    property_code = str(property_code or "DRE001").upper()
    for code, plan in RATE_PLANS.items():
        db.execute(
            text(
                """
                INSERT INTO rate_plans (
                    property_code, code, name, multiplier, requires_manager_approval, cancellation_policy, is_active
                )
                VALUES (
                    :property_code, :code, :name, :multiplier, :requires_manager_approval, :policy, TRUE
                )
                ON CONFLICT (property_code, code) DO NOTHING
                """
            ),
            {
                "property_code": property_code,
                "code": code,
                "name": plan["label"],
                "multiplier": plan["multiplier"],
                "requires_manager_approval": code == "GRP10",
                "policy": plan["policy"],
            },
        )
        db.execute(
            text(
                """
                INSERT INTO deposit_policies (
                    property_code, rate_code, deposit_percent, guarantee_required, policy_text, is_active
                )
                VALUES (
                    :property_code, :rate_code, :deposit_percent, :guarantee_required, :policy_text, TRUE
                )
                ON CONFLICT (property_code, rate_code) DO NOTHING
                """
            ),
            {
                "property_code": property_code,
                "rate_code": code,
                "deposit_percent": plan["deposit_percent"],
                "guarantee_required": plan["guarantee_required"],
                "policy_text": plan["policy"],
            },
        )

    for room_key, base_rate in ROOM_BASE_RATES_ETB.items():
        db.execute(
            text(
                """
                INSERT INTO room_type_rates (property_code, room_type, base_rate_etb, currency, is_active)
                VALUES (:property_code, :room_type, :base_rate_etb, 'ETB', TRUE)
                ON CONFLICT (property_code, room_type) DO NOTHING
                """
            ),
            {"property_code": property_code, "room_type": room_key.title(), "base_rate_etb": base_rate},
        )

    db.execute(
        text(
            """
            INSERT INTO tax_service_rules (
                property_code, rule_name, tax_percent, service_charge_percent, is_active
            )
            VALUES (
                :property_code, 'Default Tax / Service', :tax_percent, :service_charge_percent, TRUE
            )
            ON CONFLICT (property_code, rule_name) DO NOTHING
            """
        ),
        {
            "property_code": property_code,
            "tax_percent": TAX_PERCENT,
            "service_charge_percent": SERVICE_CHARGE_PERCENT,
        },
    )
    db.execute(
        text(
            """
            INSERT INTO season_rules (
                property_code, rule_name, start_month, end_month, surcharge_percent, weekend_surcharge_percent, is_active
            )
            SELECT
                :property_code, 'High Season', 7, 12, :seasonal_percent, :weekend_percent, TRUE
            WHERE NOT EXISTS (
                SELECT 1
                FROM season_rules
                WHERE property_code = :property_code
                  AND rule_name = 'High Season'
            )
            """
        ),
        {
            "property_code": property_code,
            "seasonal_percent": SEASONAL_SURCHARGE_PERCENT,
            "weekend_percent": WEEKEND_SURCHARGE_PERCENT,
        },
    )


def get_rate_configuration(db: Session, property_code: str) -> dict[str, Any]:
    property_code = str(property_code or "DRE001").upper()
    ensure_rate_configuration_tables(db, property_code)
    return {
        "property_code": property_code,
        "rate_plans": [
            dict(row)
            for row in db.execute(
                text(
                    """
                    SELECT id, code, name, multiplier, requires_manager_approval, cancellation_policy, is_active
                    FROM rate_plans
                    WHERE property_code = :property_code
                    ORDER BY code
                    """
                ),
                {"property_code": property_code},
            ).mappings().all()
        ],
        "room_type_rates": [
            dict(row)
            for row in db.execute(
                text(
                    """
                    SELECT id, room_type, base_rate_etb, currency, is_active
                    FROM room_type_rates
                    WHERE property_code = :property_code
                    ORDER BY room_type
                    """
                ),
                {"property_code": property_code},
            ).mappings().all()
        ],
        "tax_service_rules": [
            dict(row)
            for row in db.execute(
                text(
                    """
                    SELECT id, rule_name, tax_percent, service_charge_percent, is_active
                    FROM tax_service_rules
                    WHERE property_code = :property_code
                    ORDER BY is_active DESC, rule_name
                    """
                ),
                {"property_code": property_code},
            ).mappings().all()
        ],
        "season_rules": [
            dict(row)
            for row in db.execute(
                text(
                    """
                    SELECT id, rule_name, start_month, end_month, surcharge_percent, weekend_surcharge_percent, is_active
                    FROM season_rules
                    WHERE property_code = :property_code
                    ORDER BY is_active DESC, start_month
                    """
                ),
                {"property_code": property_code},
            ).mappings().all()
        ],
        "deposit_policies": [
            dict(row)
            for row in db.execute(
                text(
                    """
                    SELECT id, rate_code, deposit_percent, guarantee_required, policy_text, is_active
                    FROM deposit_policies
                    WHERE property_code = :property_code
                    ORDER BY rate_code
                    """
                ),
                {"property_code": property_code},
            ).mappings().all()
        ],
    }


def _matching_month_rule(rules: list[dict[str, Any]], month: int) -> dict[str, Any] | None:
    for rule in rules:
        if not rule.get("is_active", True):
            continue
        start = int(rule.get("start_month") or 1)
        end = int(rule.get("end_month") or 12)
        if start <= end and start <= month <= end:
            return rule
        if start > end and (month >= start or month <= end):
            return rule
    return None


def _configuration_for_quote(db: Session | None, property_code: str) -> dict[str, Any] | None:
    if db is None:
        return None
    return get_rate_configuration(db, property_code)


def quote_stay(
    *,
    property_code: str,
    check_in: date,
    check_out: date,
    room_type: str | None,
    rooms: int = 1,
    adults: int = 1,
    children: int = 0,
    rate_code: str = "BAR",
    db: Session | None = None,
) -> dict[str, Any]:
    """Return the PMS rate/tax/deposit quote used by Booking Hub conversions."""
    if check_out <= check_in:
        raise ValueError("check_out must be after check_in")

    room_count = max(int(rooms or 1), 1)
    adult_count = max(int(adults or 1), 1)
    child_count = max(int(children or 0), 0)
    config = _configuration_for_quote(db, property_code)
    room_key = _normalize_room_key(room_type)
    plan_code = str(rate_code or "BAR").upper()
    plan = RATE_PLANS.get(plan_code, RATE_PLANS["BAR"]).copy()
    deposit_rule = {
        "deposit_percent": plan["deposit_percent"],
        "guarantee_required": plan["guarantee_required"],
        "policy_text": plan["policy"],
    }
    base_rate = ROOM_BASE_RATES_ETB[room_key]
    service_percent = SERVICE_CHARGE_PERCENT
    tax_percent = TAX_PERCENT
    weekend_percent = WEEKEND_SURCHARGE_PERCENT
    seasonal_percent = SEASONAL_SURCHARGE_PERCENT if check_in.month in HIGH_SEASON_MONTHS else 0
    applied_rules = ["fallback_defaults"]

    if config:
        applied_rules = ["admin_rate_configuration"]
        room_rows = [row for row in config["room_type_rates"] if row.get("is_active", True)]
        for row in room_rows:
            if _normalize_room_key(row.get("room_type")) == room_key:
                base_rate = float(row["base_rate_etb"] or base_rate)
                applied_rules.append(f"room_rate:{row['room_type']}")
                break

        for row in config["rate_plans"]:
            if str(row.get("code") or "").upper() == plan_code and row.get("is_active", True):
                plan = {
                    "label": row["name"],
                    "multiplier": float(row["multiplier"] or 1),
                    "deposit_percent": plan["deposit_percent"],
                    "guarantee_required": plan["guarantee_required"],
                    "policy": row.get("cancellation_policy") or plan["policy"],
                }
                applied_rules.append(f"rate_plan:{plan_code}")
                break

        tax_rule = next((row for row in config["tax_service_rules"] if row.get("is_active", True)), None)
        if tax_rule:
            tax_percent = float(tax_rule["tax_percent"] or 0)
            service_percent = float(tax_rule["service_charge_percent"] or 0)
            applied_rules.append(f"tax_service:{tax_rule['rule_name']}")

        season_rule = _matching_month_rule(config["season_rules"], check_in.month)
        if season_rule:
            seasonal_percent = float(season_rule["surcharge_percent"] or 0)
            weekend_percent = float(season_rule["weekend_surcharge_percent"] or 0)
            applied_rules.append(f"season:{season_rule['rule_name']}")

        for row in config["deposit_policies"]:
            if str(row.get("rate_code") or "").upper() == plan_code and row.get("is_active", True):
                deposit_rule = {
                    "deposit_percent": float(row["deposit_percent"] or 0),
                    "guarantee_required": bool(row["guarantee_required"]),
                    "policy_text": row.get("policy_text") or plan["policy"],
                }
                applied_rules.append(f"deposit_policy:{plan_code}")
                break

    stay_nights = _nights(check_in, check_out)
    weekend_nights = _count_weekend_nights(check_in, check_out)

    plan_rate = base_rate * float(plan["multiplier"])
    seasonal_multiplier = 1 + seasonal_percent
    nightly_rate = _money(plan_rate * seasonal_multiplier)
    room_subtotal = nightly_rate * stay_nights * room_count
    weekend_surcharge = _money(nightly_rate * weekend_percent * weekend_nights * room_count)

    included_adults = room_count * 2
    included_children = room_count * 2
    extra_adults = max(adult_count - included_adults, 0)
    extra_children = max(child_count - included_children, 0)
    extra_guest_charge = _money(
        (extra_adults * EXTRA_ADULT_ETB + extra_children * EXTRA_CHILD_ETB) * stay_nights
    )

    taxable_base = _money(room_subtotal + weekend_surcharge + extra_guest_charge)
    service_charge = _money(taxable_base * service_percent)
    tax = _money((taxable_base + service_charge) * tax_percent)
    total = _money(taxable_base + service_charge + tax)
    deposit_percent = float(deposit_rule["deposit_percent"])
    deposit_required = _money(total * deposit_percent)

    return {
        "property_code": str(property_code or "").upper(),
        "currency": "ETB",
        "room_type": room_type or "Standard Room",
        "rate_code": plan_code if plan_code in RATE_PLANS else "BAR",
        "rate_label": plan["label"],
        "nights": stay_nights,
        "rooms": room_count,
        "adults": adult_count,
        "children": child_count,
        "base_rate_etb": _money(base_rate),
        "nightly_rate_etb": nightly_rate,
        "room_subtotal_etb": _money(room_subtotal),
        "weekend_nights": weekend_nights,
        "weekend_surcharge_etb": weekend_surcharge,
        "extra_adult_count": extra_adults,
        "extra_child_count": extra_children,
        "extra_guest_charge_etb": extra_guest_charge,
        "service_charge_percent": service_percent,
        "service_charge_etb": service_charge,
        "tax_percent": tax_percent,
        "tax_etb": tax,
        "net_revenue_etb": taxable_base,
        "gross_revenue_etb": total,
        "total_etb": total,
        "deposit_percent": deposit_percent,
        "deposit_required_etb": deposit_required,
        "guarantee_required": bool(deposit_rule["guarantee_required"]),
        "cancellation_policy": deposit_rule["policy_text"] or plan["policy"],
        "applied_rules": applied_rules,
        "quote_notes": [
            "BAR/corporate/group rate code applied",
            "Weekend and high-season rules evaluated",
            "Tax and service charge included in gross total",
            "Deposit amount calculated from PMS policy",
        ],
    }
