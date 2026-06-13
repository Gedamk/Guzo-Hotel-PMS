from decimal import Decimal
from datetime import date
from typing import Any
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.services.business_date_lock_service import assert_business_date_editable
from guzo_backend.services.pms_security_service import record_pms_audit_log
from guzo_backend.modules.food_costing.models import (
    Ingredient,
    Supplier,
    Recipe,
    RecipeIngredient,
    FoodCostAlert,
    PurchaseOrder,
    GoodsReceived,
    InventoryMovement,
    PosSale,
    KitchenRequisition,
    WastageRecord,
    StockCount,
)

from guzo_backend.modules.food_costing.schemas import (
    IngredientCreate,
    RecipeCreate,
    RecipeIngredientCreate,
)


PROPERTY_BASE_CURRENCIES = {"DRE001": "ETB"}
FIVE_STAR_FNB_DEPARTMENTS = [
    "Main Kitchen",
    "Ethiopian Traditional Kitchen",
    "Pastry/Bakery",
    "Garde Manger",
    "Juice Bar",
    "Bar",
    "Coffee Shop",
    "Banquet Kitchen",
    "Staff Cafeteria",
]
ETHIOPIAN_FNB_ITEMS = [
    "Teff flour",
    "Injera",
    "Berbere",
    "Shiro",
    "Niter kibbeh",
    "Doro wot ingredients",
    "Tibs ingredients",
    "Kitfo ingredients",
    "Coffee beans",
    "Bottled water",
    "Soft drinks",
]
SUPPORTED_FNB_UNITS = ["kg", "gram", "liter", "ml", "bottle", "crate", "pack", "piece", "pcs"]
FIVE_STAR_ALACARTE_RECIPES = [
    {
        "name": "Grilled Beef Tenderloin with Pepper Sauce",
        "department": "Main Kitchen",
        "selling_price": 1850,
        "ingredients": [
            ("Beef tenderloin", "gram", 1.90, 250),
            ("Potato", "gram", 0.12, 180),
            ("Carrot", "gram", 0.09, 80),
            ("Green beans", "gram", 0.16, 60),
            ("Butter", "gram", 0.65, 25),
            ("Black pepper", "gram", 0.50, 5),
            ("Cream", "ml", 0.35, 50),
            ("Beef stock", "ml", 0.12, 80),
            ("Garlic", "gram", 0.18, 8),
            ("Salt", "gram", 0.02, 3),
        ],
    },
    {
        "name": "Pan-Seared Nile Perch with Lemon Butter Sauce",
        "department": "Main Kitchen",
        "selling_price": 1650,
        "ingredients": [
            ("Nile perch fillet", "gram", 1.75, 220),
            ("Rice", "gram", 0.10, 160),
            ("Broccoli", "gram", 0.18, 80),
            ("Lemon", "gram", 0.12, 30),
            ("Butter", "gram", 0.65, 30),
            ("Garlic", "gram", 0.18, 6),
            ("Olive oil", "ml", 0.55, 15),
            ("Fresh herbs", "gram", 0.40, 5),
            ("Salt", "gram", 0.02, 3),
            ("Black pepper", "gram", 0.50, 3),
        ],
    },
    {
        "name": "Doro Wot Fine Dining Plate",
        "department": "Ethiopian Traditional Kitchen",
        "selling_price": 1400,
        "ingredients": [
            ("Chicken portion", "gram", 0.90, 250),
            ("Onion", "gram", 0.06, 180),
            ("Berbere", "gram", 0.35, 25),
            ("Niter kibbeh", "gram", 0.50, 35),
            ("Garlic", "gram", 0.18, 10),
            ("Ginger", "gram", 0.18, 8),
            ("Egg", "piece", 25.00, 1),
            ("Injera", "piece", 20.00, 1),
            ("Salt", "gram", 0.02, 3),
            ("Cardamom", "gram", 0.80, 2),
        ],
    },
    {
        "name": "Kitfo Royal Plate",
        "department": "Ethiopian Traditional Kitchen",
        "selling_price": 1750,
        "ingredients": [
            ("Lean beef mince", "gram", 1.70, 250),
            ("Mitmita", "gram", 0.60, 8),
            ("Niter kibbeh", "gram", 0.50, 35),
            ("Ayib cheese", "gram", 0.35, 80),
            ("Gomen", "gram", 0.12, 100),
            ("Kocho or injera", "piece", 20.00, 1),
            ("Salt", "gram", 0.02, 3),
            ("Cardamom", "gram", 0.80, 2),
        ],
    },
    {
        "name": "Chicken Alfredo Pasta",
        "department": "Main Kitchen",
        "selling_price": 1250,
        "ingredients": [
            ("Pasta", "gram", 0.18, 180),
            ("Chicken breast", "gram", 0.75, 180),
            ("Cream", "ml", 0.35, 120),
            ("Parmesan cheese", "gram", 0.90, 30),
            ("Butter", "gram", 0.65, 25),
            ("Garlic", "gram", 0.18, 8),
            ("Mushroom", "gram", 0.25, 70),
            ("Olive oil", "ml", 0.55, 15),
            ("Salt", "gram", 0.02, 3),
            ("Black pepper", "gram", 0.50, 3),
        ],
    },
]
FNB_REPORT_ACTIONS = {
    "submit": ("submitted", "prepared_by", "prepared_at", "fnb_report_submitted"),
    "finance_review": ("finance_reviewed", "finance_reviewed_by", "finance_reviewed_at", "fnb_report_finance_reviewed"),
    "fnb_approve": ("fnb_manager_approved", "fnb_approved_by", "fnb_approved_at", "fnb_report_fnb_approved"),
    "gm_lock": ("locked", "gm_approved_by", "gm_approved_at", "fnb_report_gm_locked"),
    "override": ("draft", None, None, "fnb_report_override"),
}


def _as_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def calculate_food_cost_percentage(total_cost: Any, selling_price: Any) -> Decimal:
    selling_price_decimal = _as_decimal(selling_price)
    if selling_price_decimal <= 0:
        return Decimal("0.00")
    return _money((_as_decimal(total_cost) / selling_price_decimal) * Decimal("100"))


def calculate_buffet_cost_per_guest(total_cost: Any, guest_count: Any) -> Decimal:
    guest_count_decimal = _as_decimal(guest_count)
    if guest_count_decimal <= 0:
        return Decimal("0.00")
    return _money(_as_decimal(total_cost) / guest_count_decimal)


def calculate_beverage_cost_per_serving(bottle_cost: Any, bottle_size: Any, serving_size: Any) -> dict[str, Decimal]:
    serving_size_decimal = _as_decimal(serving_size)
    expected_servings = Decimal("0")
    if serving_size_decimal > 0:
        expected_servings = _as_decimal(bottle_size) / serving_size_decimal
    cost_per_serving = Decimal("0.00")
    if expected_servings > 0:
        cost_per_serving = _money(_as_decimal(bottle_cost) / expected_servings)
    return {
        "expected_servings": expected_servings.quantize(Decimal("0.001")) if expected_servings else Decimal("0.000"),
        "cost_per_serving": cost_per_serving,
    }


def calculate_variance(expected_usage: Any, actual_usage: Any, unit_cost: Any = 0) -> dict[str, Decimal]:
    # Hotel variance is actual usage minus expected usage; positive means over-consumption.
    difference = _as_decimal(actual_usage) - _as_decimal(expected_usage)
    return {
        "difference": difference,
        "variance_value": _money(difference * _as_decimal(unit_cost)),
    }


def _ingredient_for_name(db: Session, property_code: str, ingredient_name: str) -> Ingredient | None:
    return (
        db.query(Ingredient)
        .filter(
            Ingredient.property_code == property_code,
            Ingredient.name == ingredient_name,
        )
        .first()
    )


def current_stock_quantity(db: Session, property_code: str, ingredient_name: str) -> Decimal:
    movements = (
        db.query(InventoryMovement)
        .filter(
            InventoryMovement.property_code == property_code,
            InventoryMovement.ingredient_name == ingredient_name,
        )
        .all()
    )
    balance = Decimal("0")
    for movement in movements:
        quantity = _as_decimal(movement.quantity)
        movement_type = str(movement.movement_type or "").upper()
        if movement_type in {"OPENING", "PURCHASE_RECEIVED", "ADJUSTMENT_IN"}:
            balance += quantity
        elif movement_type in {"KITCHEN_ISSUE", "WASTAGE"}:
            balance -= quantity
        elif movement_type == "ADJUSTMENT":
            balance += quantity
    return balance


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


def _active_tax_service_rule(db: Session, property_code: str) -> dict[str, Decimal | str | None]:
    if not _table_exists(db, "tax_service_rules"):
        return {
            "source": "not_configured",
            "rule_name": None,
            "tax_percent": Decimal("0"),
            "service_charge_percent": Decimal("0"),
        }
    row = db.execute(
        text(
            """
            SELECT rule_name, tax_percent, service_charge_percent
            FROM tax_service_rules
            WHERE property_code = :property_code
              AND COALESCE(is_active, TRUE) = TRUE
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"property_code": property_code},
    ).mappings().first()
    if not row:
        return {
            "source": "not_configured",
            "rule_name": None,
            "tax_percent": Decimal("0"),
            "service_charge_percent": Decimal("0"),
        }
    return {
        "source": "tax_service_rules",
        "rule_name": row["rule_name"],
        "tax_percent": _as_decimal(row["tax_percent"]),
        "service_charge_percent": _as_decimal(row["service_charge_percent"]),
    }


def _get_booking_for_room_charge(db: Session, property_code: str, booking_id: int) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            SELECT id, guest_name, COALESCE(currency, 'ETB') AS currency
            FROM bookings
            WHERE property_code = :property_code
              AND id = :booking_id
            LIMIT 1
            """
        ),
        {"property_code": property_code, "booking_id": booking_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found for F&B room charge.")
    return dict(row)


def _get_or_create_folio(db: Session, property_code: str, booking_id: int) -> int:
    booking = _get_booking_for_room_charge(db, property_code, booking_id)
    row = db.execute(
        text(
            """
            SELECT id
            FROM folios
            WHERE property_code = :property_code
              AND booking_id = :booking_id
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"property_code": property_code, "booking_id": booking_id},
    ).first()
    if row:
        return int(row.id)

    created = db.execute(
        text(
            """
            INSERT INTO folios(property_code, booking_id, guest_name, currency, status)
            VALUES(:property_code, :booking_id, :guest_name, :currency, 'open')
            RETURNING id
            """
        ),
        {
            "property_code": property_code,
            "booking_id": booking_id,
            "guest_name": booking.get("guest_name") or "Guest",
            "currency": booking.get("currency") or PROPERTY_BASE_CURRENCIES.get(property_code, "ETB"),
        },
    ).first()
    return int(created.id)


def _refresh_folio_totals(db: Session, folio_id: int) -> None:
    row = db.execute(
        text(
            """
            SELECT
              COALESCE(SUM(CASE WHEN txn_type = 'charge' THEN amount ELSE 0 END), 0) AS total_charges,
              COALESCE(SUM(CASE WHEN txn_type = 'payment' THEN amount WHEN txn_type = 'refund' THEN -amount ELSE 0 END), 0) AS total_payments
            FROM folio_transactions
            WHERE folio_id = :folio_id
            """
        ),
        {"folio_id": folio_id},
    ).mappings().first()
    total_charges = _as_decimal(row["total_charges"] if row else 0)
    total_payments = _as_decimal(row["total_payments"] if row else 0)
    db.execute(
        text(
            """
            UPDATE folios
            SET total_charges = :total_charges,
                total_payments = :total_payments,
                balance = :balance
            WHERE id = :folio_id
            """
        ),
        {
            "folio_id": folio_id,
            "total_charges": total_charges,
            "total_payments": total_payments,
            "balance": total_charges - total_payments,
        },
    )


def ensure_fnb_report_approval_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS fnb_report_approvals (
                id SERIAL PRIMARY KEY,
                property_code VARCHAR(20) NOT NULL,
                report_period VARCHAR(20) NOT NULL,
                report_start_date DATE NOT NULL,
                report_end_date DATE NOT NULL,
                status VARCHAR(40) DEFAULT 'draft',
                prepared_by VARCHAR(150),
                prepared_at TIMESTAMP,
                finance_reviewed_by VARCHAR(150),
                finance_reviewed_at TIMESTAMP,
                fnb_approved_by VARCHAR(150),
                fnb_approved_at TIMESTAMP,
                gm_approved_by VARCHAR(150),
                gm_approved_at TIMESTAMP,
                locked_at TIMESTAMP,
                override_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                UNIQUE(property_code, report_period, report_start_date, report_end_date)
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_fnb_report_approvals_property_status
            ON fnb_report_approvals(property_code, status)
            """
        )
    )


def _report_approval_row(db: Session, property_code: str, report_period: str, start_date, end_date):
    ensure_fnb_report_approval_table(db)
    row = db.execute(
        text(
            """
            INSERT INTO fnb_report_approvals (
                property_code, report_period, report_start_date, report_end_date, status
            )
            VALUES (:property_code, :report_period, :start_date, :end_date, 'draft')
            ON CONFLICT (property_code, report_period, report_start_date, report_end_date)
            DO NOTHING
            RETURNING id
            """
        ),
        {
            "property_code": property_code,
            "report_period": report_period,
            "start_date": start_date,
            "end_date": end_date,
        },
    ).first()
    if row:
        db.flush()
    return db.execute(
        text(
            """
            SELECT *
            FROM fnb_report_approvals
            WHERE property_code = :property_code
              AND report_period = :report_period
              AND report_start_date = :start_date
              AND report_end_date = :end_date
            LIMIT 1
            """
        ),
        {
            "property_code": property_code,
            "report_period": report_period,
            "start_date": start_date,
            "end_date": end_date,
        },
    ).mappings().first()


def get_report_approval(db: Session, property_code: str, report_period: str, start_date, end_date):
    row = _report_approval_row(db, property_code, report_period, start_date, end_date)
    db.commit()
    return dict(row)


def update_report_approval(db: Session, data, actor_email: str):
    action = data.action.strip().lower()
    if action not in FNB_REPORT_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported F&B report approval action: {data.action}")
    row = _report_approval_row(
        db,
        data.property_code,
        data.report_period,
        data.report_start_date,
        data.report_end_date,
    )
    old_status = row["status"]
    if old_status == "locked" and action != "override":
        raise HTTPException(status_code=409, detail="F&B report is locked and cannot be changed without Admin override.")

    next_status, user_column, at_column, audit_action = FNB_REPORT_ACTIONS[action]
    values = {
        "id": row["id"],
        "status": next_status,
        "actor": actor_email,
        "override_reason": data.override_reason,
    }
    assignments = ["status = :status", "updated_at = CURRENT_TIMESTAMP"]
    if user_column and at_column:
        assignments.extend([f"{user_column} = :actor", f"{at_column} = CURRENT_TIMESTAMP"])
    if action == "gm_lock":
        assignments.append("locked_at = CURRENT_TIMESTAMP")
    if action == "override":
        assignments.extend(["locked_at = NULL", "override_reason = :override_reason"])

    db.execute(
        text(
            f"""
            UPDATE fnb_report_approvals
            SET {", ".join(assignments)}
            WHERE id = :id
            """
        ),
        values,
    )
    record_pms_audit_log(
        db,
        property_code=data.property_code,
        user_email=actor_email,
        module="food_costing",
        action=audit_action,
        record_type="fnb_report_approval",
        record_id=row["id"],
        old_value={"status": old_status},
        new_value={
            "status": next_status,
            "report_period": data.report_period,
            "report_start_date": str(data.report_start_date),
            "report_end_date": str(data.report_end_date),
            "override_reason": data.override_reason,
        },
    )
    db.commit()
    return get_report_approval(
        db,
        data.property_code,
        data.report_period,
        data.report_start_date,
        data.report_end_date,
    )


# =====================================================
# INGREDIENTS
# =====================================================

def create_ingredient(db: Session, data: IngredientCreate):
    payload = data.model_dump()
    payload["last_purchase_price"] = payload.get("last_purchase_price") or payload["purchase_price"]
    payload["average_cost"] = payload.get("average_cost") or payload["cost_per_unit"]
    ingredient = Ingredient(**payload)

    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)

    return ingredient


def create_supplier(db: Session, data):
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def list_suppliers(db: Session, property_code: str):
    return (
        db.query(Supplier)
        .filter(Supplier.property_code == property_code)
        .order_by(Supplier.supplier_name.asc())
        .all()
    )


def ensure_five_star_alacarte_seed_data(db: Session, property_code: str) -> None:
    # Hotel demo flow: the ingredient master is seeded first, then recipe costing
    # lines are created so total cost, food cost %, and gross profit are calculated.
    normalized_property = property_code.strip().upper()
    created_any = False

    for recipe_seed in FIVE_STAR_ALACARTE_RECIPES:
        for name, unit, cost_per_unit, _quantity in recipe_seed["ingredients"]:
            if _ingredient_for_name(db, normalized_property, name):
                continue
            db.add(
                Ingredient(
                    property_code=normalized_property,
                    name=name,
                    category="Food",
                    unit=unit,
                    purchase_price=Decimal(str(cost_per_unit)),
                    cost_per_unit=Decimal(str(cost_per_unit)),
                    last_purchase_price=Decimal(str(cost_per_unit)),
                    average_cost=Decimal(str(cost_per_unit)),
                    supplier_name="Five-Star F&B Demo Supplier",
                    storage_location="Main Store",
                )
            )
            created_any = True

    if created_any:
        db.flush()

    for recipe_seed in FIVE_STAR_ALACARTE_RECIPES:
        existing_recipe = (
            db.query(Recipe)
            .filter(
                Recipe.property_code == normalized_property,
                Recipe.name == recipe_seed["name"],
            )
            .first()
        )
        if existing_recipe:
            continue

        recipe_lines = []
        for name, _unit, _cost_per_unit, quantity in recipe_seed["ingredients"]:
            ingredient = _ingredient_for_name(db, normalized_property, name)
            if ingredient:
                recipe_lines.append(
                    RecipeIngredientCreate(
                        ingredient_id=ingredient.id,
                        quantity_used=quantity,
                    )
                )

        if not recipe_lines:
            continue

        recipe = create_recipe(
            db,
            RecipeCreate(
                property_code=normalized_property,
                name=recipe_seed["name"],
                outlet_name=recipe_seed["department"],
                selling_price=recipe_seed["selling_price"],
                target_cost_percentage=35,
                ingredients=recipe_lines,
            ),
        )
        recipe.approval_status = "approved"
        db.commit()

    if created_any:
        db.commit()


def list_ingredients(db: Session, property_code: str):
    normalized_property = property_code.strip().upper()
    ensure_five_star_alacarte_seed_data(db, normalized_property)
    return (
        db.query(Ingredient)
        .filter(Ingredient.property_code == normalized_property)
        .order_by(Ingredient.name.asc())
        .all()
    )


# =====================================================
# RECIPES
# =====================================================

def create_recipe(db: Session, data: RecipeCreate):
    property_code = data.property_code.strip().upper()
    recipe_name = data.name.strip()
    existing_recipe = (
        db.query(Recipe)
        .filter(
            Recipe.property_code == property_code,
            Recipe.name == recipe_name,
        )
        .first()
    )
    if existing_recipe:
        raise HTTPException(status_code=409, detail="A recipe with this menu item name already exists for this property.")

    total_cost = Decimal("0.00")

    recipe = Recipe(
        property_code=property_code,
        name=recipe_name,
        outlet_name=data.outlet_name,
        selling_price=data.selling_price,
        total_cost=Decimal("0.00"),
        food_cost_percentage=Decimal("0.00"),
        target_cost_percentage=data.target_cost_percentage,
        approval_status="draft",
    )

    db.add(recipe)
    db.flush()

    for item in data.ingredients:
        ingredient = (
            db.query(Ingredient)
            .filter(Ingredient.id == item.ingredient_id)
            .first()
        )

        if not ingredient:
            continue

        cost_used = (
            Decimal(str(item.quantity_used))
            * Decimal(str(ingredient.cost_per_unit))
        )

        total_cost += cost_used

        db.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity_used=item.quantity_used,
                cost_used=cost_used,
            )
        )

    recipe.total_cost = total_cost

    recipe.food_cost_percentage = calculate_food_cost_percentage(total_cost, data.selling_price)
    recipe.profit_margin = Decimal(str(data.selling_price or 0)) - total_cost

    if recipe.food_cost_percentage > Decimal(str(data.target_cost_percentage or 35)):
        db.add(
            FoodCostAlert(
                property_code=data.property_code,
                alert_type="HIGH_FOOD_COST",
                severity="high",
                message=(
                    f"{recipe.name} food cost is "
                    f"{recipe.food_cost_percentage:.2f}%. "
                    f"Review selling price or ingredient cost."
                ),
            )
        )

    db.commit()
    db.refresh(recipe)

    return recipe


def list_recipes(db: Session, property_code: str):
    normalized_property = property_code.strip().upper()
    ensure_five_star_alacarte_seed_data(db, normalized_property)
    return (
        db.query(Recipe)
        .filter(Recipe.property_code == normalized_property)
        .order_by(Recipe.created_at.desc())
        .all()
    )


# =====================================================
# ALERTS
# =====================================================

def list_alerts(db: Session, property_code: str):
    return (
        db.query(FoodCostAlert)
        .filter(FoodCostAlert.property_code == property_code)
        .order_by(FoodCostAlert.created_at.desc())
        .all()
    )


# =====================================================
# PURCHASE ORDERS
# =====================================================

def create_purchase_order(db: Session, data):
    total_amount = Decimal(str(data.quantity)) * Decimal(str(data.unit_price))

    po = PurchaseOrder(
        property_code=data.property_code,
        supplier_name=data.supplier_name,
        supplier_id=data.supplier_id,
        ingredient_name=data.ingredient_name,
        quantity=data.quantity,
        ordered_qty=data.quantity,
        received_qty=0,
        rejected_qty=0,
        unit_price=data.unit_price,
        unit_cost=data.unit_price,
        invoice_number=data.invoice_number,
        received_by=data.received_by,
        approval_status=data.approval_status or "pending",
        total_amount=total_amount,
        status="PENDING",
    )

    db.add(po)
    db.commit()
    db.refresh(po)

    return po


def approve_purchase_order(db: Session, purchase_order_id: int, data, actor_email: str | None = None):
    po = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.id == purchase_order_id,
            PurchaseOrder.property_code == data.property_code,
        )
        .first()
    )
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found.")
    action = str(data.action or "approve").strip().lower()
    if action not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="Use approve or reject for Purchase Order approval.")
    po.approval_status = "approved" if action == "approve" else "rejected"
    po.status = "APPROVED" if action == "approve" else "REJECTED"
    po.received_by = data.approved_by
    record_pms_audit_log(
        db,
        property_code=data.property_code,
        user_email=actor_email,
        module="food_costing",
        action="purchase_order_approved" if action == "approve" else "purchase_order_rejected",
        record_type="purchase_order",
        record_id=po.id,
        new_value={
            "supplier": po.supplier_name,
            "ingredient": po.ingredient_name,
            "approved_by": data.approved_by,
            "status": po.approval_status,
        },
    )
    db.commit()
    db.refresh(po)
    return po


def list_purchase_orders(db: Session, property_code: str):
    return (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.property_code == property_code)
        .order_by(PurchaseOrder.created_at.desc())
        .all()
    )


# =====================================================
# GOODS RECEIVED
# =====================================================

def create_goods_received(db: Session, data):
    po = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.id == data.purchase_order_id,
            PurchaseOrder.property_code == data.property_code,
        )
        .first()
    )
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found for Goods Receiving Note.")
    if str(po.approval_status or "").lower() != "approved":
        raise HTTPException(status_code=409, detail="Purchase Order must be approved before delivery is received.")

    ordered_qty = _as_decimal(data.ordered_qty if data.ordered_qty is not None else po.ordered_qty or po.quantity)
    accepted_qty = _as_decimal(data.quantity_received)
    rejected_qty = _as_decimal(data.rejected_qty or 0)
    if accepted_qty < 0 or rejected_qty < 0:
        raise HTTPException(status_code=400, detail="Accepted and rejected quantities cannot be negative.")
    if accepted_qty + rejected_qty > ordered_qty:
        raise HTTPException(status_code=400, detail="Accepted plus rejected quantity cannot exceed the Purchase Order quantity.")

    ingredient = _ingredient_for_name(db, data.property_code, data.ingredient_name)
    unit = ingredient.unit if ingredient else "kg"
    unit_cost = _as_decimal(data.unit_cost if data.unit_cost is not None else po.unit_cost or po.unit_price)
    grn_payload = data.model_dump()
    grn_payload["ordered_qty"] = float(ordered_qty)
    grn_payload["unit_cost"] = float(unit_cost)
    grn = GoodsReceived(**grn_payload)

    po.status = "RECEIVED"
    po.received_qty = data.quantity_received
    po.rejected_qty = data.rejected_qty or 0
    po.invoice_number = data.invoice_number
    po.received_by = data.received_by
    po.approval_status = "received"

    if ingredient:
        old_cost = ingredient.cost_per_unit
        ingredient.last_purchase_price = unit_cost
        ingredient.average_cost = unit_cost
        ingredient.cost_per_unit = unit_cost
        if _as_decimal(old_cost) != unit_cost:
            record_pms_audit_log(
                db,
                property_code=data.property_code,
                user_email=data.received_by,
                module="food_costing",
                action="ingredient_unit_cost_changed",
                record_type="ingredient",
                record_id=ingredient.id,
                old_value={"unit_cost": str(old_cost)},
                new_value={"unit_cost": str(unit_cost), "source": f"GRN for PO #{po.id}"},
            )

    db.add(grn)
    db.flush()

    inventory_movement = InventoryMovement(
        property_code=data.property_code,
        ingredient_name=data.ingredient_name,
        movement_type="PURCHASE_RECEIVED",
        quantity=data.quantity_received,
        unit=unit,
        unit_cost=unit_cost,
        stock_value=_money(accepted_qty * unit_cost),
        reference=f"GRN #{grn.id} / PO #{po.id}",
        notes=(
            f"Goods Receiving Note accepted {accepted_qty} {unit}; "
            f"rejected {rejected_qty} {unit}; invoice {data.invoice_number or 'not provided'}"
        ).strip(),
        created_by=data.received_by,
    )

    db.add(inventory_movement)

    db.commit()
    db.refresh(grn)

    return grn


def list_goods_received(db: Session, property_code: str):
    return (
        db.query(GoodsReceived)
        .filter(GoodsReceived.property_code == property_code)
        .order_by(GoodsReceived.created_at.desc())
        .all()
    )


# =====================================================
# INVENTORY MOVEMENTS
# =====================================================

def create_inventory_movement(db: Session, data):
    payload = data.model_dump()
    ingredient = _ingredient_for_name(db, payload["property_code"], payload["ingredient_name"])
    if ingredient:
        payload["unit"] = payload.get("unit") or ingredient.unit
        payload["unit_cost"] = payload.get("unit_cost") or float(ingredient.average_cost or ingredient.cost_per_unit or 0)
    movement_type = str(payload["movement_type"]).upper()
    if movement_type in {"KITCHEN_ISSUE", "WASTAGE"}:
        if not payload.get("reference"):
            raise HTTPException(status_code=400, detail="Issue and waste movements must include a hotel reference.")
        if ingredient and ingredient.expiry_date and ingredient.expiry_date < date.today():
            raise HTTPException(status_code=409, detail="Expired stock cannot be issued from Main Store.")
        available = current_stock_quantity(db, payload["property_code"], payload["ingredient_name"])
        if _as_decimal(payload["quantity"]) > available:
            raise HTTPException(status_code=409, detail="Not enough Main Store stock available for this issue.")
    if payload.get("unit_cost") is not None:
        payload["stock_value"] = _money(_as_decimal(payload["quantity"]) * _as_decimal(payload["unit_cost"]))
    movement = InventoryMovement(**payload)

    db.add(movement)
    db.commit()
    db.refresh(movement)

    return movement


def list_inventory_movements(db: Session, property_code: str):
    return (
        db.query(InventoryMovement)
        .filter(InventoryMovement.property_code == property_code)
        .order_by(InventoryMovement.created_at.desc())
        .all()
    )


def get_main_store_ledger(db: Session, property_code: str) -> list[dict[str, Any]]:
    normalized_property = property_code.strip().upper()
    ingredients = list_ingredients(db, normalized_property)
    movements = list_inventory_movements(db, normalized_property)
    requisitions = list_kitchen_requisitions(db, normalized_property)
    requisition_by_item = {req.ingredient_name: req for req in requisitions}
    rows: list[dict[str, Any]] = []

    for serial_no, ingredient in enumerate(ingredients, start=1):
        item_movements = [movement for movement in movements if movement.ingredient_name == ingredient.name]
        opening_balance = sum(
            _as_decimal(movement.quantity)
            for movement in item_movements
            if str(movement.movement_type or "").upper() == "OPENING"
        )
        purchased_qty = sum(
            _as_decimal(movement.quantity)
            for movement in item_movements
            if str(movement.movement_type or "").upper() == "PURCHASE_RECEIVED"
        )
        issued_qty = sum(
            _as_decimal(movement.quantity)
            for movement in item_movements
            if str(movement.movement_type or "").upper() in {"KITCHEN_ISSUE", "WASTAGE"}
        )
        total_balance = opening_balance + purchased_qty
        balance_on_hand = total_balance - issued_qty
        unit_price = _as_decimal(ingredient.average_cost or ingredient.cost_per_unit or 0)
        reorder_level = _as_decimal(ingredient.reorder_level or 0)
        total_value = _money(balance_on_hand * unit_price)
        latest_purchase = next(
            (movement for movement in item_movements if str(movement.movement_type or "").upper() == "PURCHASE_RECEIVED"),
            None,
        )
        latest_issue = next(
            (movement for movement in item_movements if str(movement.movement_type or "").upper() == "KITCHEN_ISSUE"),
            None,
        )
        req = requisition_by_item.get(ingredient.name)
        status = "OK"
        if ingredient.expiry_date and ingredient.expiry_date < date.today():
            status = "EXPIRED"
        elif unit_price <= 0:
            status = "NO UNIT PRICE"
        elif balance_on_hand < 0:
            status = "NEGATIVE STOCK"
        elif reorder_level and balance_on_hand <= reorder_level:
            status = "LOW STOCK"

        rows.append(
            {
                "serial_no": serial_no,
                "date": str(getattr(latest_purchase or latest_issue or ingredient, "created_at", "") or ""),
                "item_code": f"FNB-{ingredient.id:04d}",
                "item_name": ingredient.name,
                "category": ingredient.category or "Food",
                "unit": ingredient.unit,
                "opening_balance": opening_balance,
                "purchased_quantity": purchased_qty,
                "total_balance": total_balance,
                "issued_quantity": issued_qty,
                "balance_on_hand": balance_on_hand,
                "unit_price": unit_price,
                "total_value": total_value,
                "supplier": ingredient.supplier_name or "",
                "grn_number": latest_purchase.reference if latest_purchase else "",
                "store_requisition_number": latest_issue.reference if latest_issue else "",
                "department_issued_to": getattr(req, "outlet_name", "") or "",
                "minimum_stock_level": reorder_level,
                "reorder_level": reorder_level,
                "status": status,
                "remarks": getattr(latest_issue or latest_purchase, "notes", None) or "",
            }
        )
    return rows


def get_store_control_reports(db: Session, property_code: str) -> dict[str, Any]:
    ledger = get_main_store_ledger(db, property_code)
    movements = list_inventory_movements(db, property_code.strip().upper())
    return {
        "daily_receiving_report": [m for m in movements if str(m.movement_type).upper() == "PURCHASE_RECEIVED"],
        "daily_issue_report": [m for m in movements if str(m.movement_type).upper() == "KITCHEN_ISSUE"],
        "balance_on_hand_report": ledger,
        "low_stock_report": [row for row in ledger if row["status"] in {"LOW STOCK", "NEGATIVE STOCK"}],
        "inventory_valuation_report": sum((_as_decimal(row["total_value"]) for row in ledger), Decimal("0")),
        "supplier_purchase_report": [m for m in movements if str(m.movement_type).upper() == "PURCHASE_RECEIVED"],
        "department_consumption_report": [m for m in movements if str(m.movement_type).upper() == "KITCHEN_ISSUE"],
        "expiry_near_expiry_report": [row for row in ledger if row["status"] == "EXPIRED"],
    }


# =====================================================
# POS SALES
# =====================================================

def create_pos_sale(db: Session, data, actor_email: str | None = None):
    total_revenue = (
        Decimal(str(data.quantity_sold))
        * Decimal(str(data.selling_price))
    )
    property_code = data.property_code.strip().upper()
    tax_rule = _active_tax_service_rule(db, property_code)
    service_rate = _as_decimal(tax_rule["service_charge_percent"])
    tax_rate = _as_decimal(tax_rule["tax_percent"])
    service_charge = _money(total_revenue * service_rate)
    tax_amount = _money((total_revenue + service_charge) * tax_rate)

    sale = PosSale(
        property_code=property_code,
        outlet_name=data.outlet_name,
        menu_item_name=data.menu_item_name,
        quantity_sold=data.quantity_sold,
        selling_price=data.selling_price,
        total_revenue=total_revenue,
        service_charge_amount=data.service_charge_amount if data.service_charge_amount is not None else service_charge,
        tax_amount=data.tax_amount if data.tax_amount is not None else tax_amount,
        payment_method=data.payment_method,
        room_charge_booking_id=data.room_charge_booking_id,
        business_date=data.business_date,
    )

    db.add(sale)
    db.flush()

    recipe = (
        db.query(Recipe)
        .filter(
            Recipe.property_code == data.property_code,
            Recipe.name == data.menu_item_name,
        )
        .first()
    )

    if recipe:
        recipe_lines = (
            db.query(RecipeIngredient)
            .filter(RecipeIngredient.recipe_id == recipe.id)
            .all()
        )

        for line in recipe_lines:
            ingredient = (
                db.query(Ingredient)
                .filter(Ingredient.id == line.ingredient_id)
                .first()
            )

            if ingredient:
                quantity_used = Decimal(
                    str(getattr(line, "quantity_used", 0))
                )

                movement = InventoryMovement(
                    property_code=property_code,
                    ingredient_name=ingredient.name,
                    movement_type="KITCHEN_ISSUE",
                    quantity=quantity_used * Decimal(str(data.quantity_sold)),
                    unit=ingredient.unit,
                    reference=f"POS Sale: {data.menu_item_name}",
                    notes=(
                        f"Auto-deducted from POS sale quantity "
                        f"{data.quantity_sold}"
                    ),
                    created_by="POS Auto Deduction",
                )

                db.add(movement)

    if data.room_charge_booking_id:
        assert_business_date_editable(db, property_code, data.business_date)
        folio_id = _get_or_create_folio(db, property_code, int(data.room_charge_booking_id))
        posted_ids: list[int] = []
        for category, description, amount in [
            ("fnb", f"{data.outlet_name}: {data.menu_item_name} x {data.quantity_sold}", total_revenue),
            ("service_charge", f"F&B service charge {service_rate * 100}%", _as_decimal(sale.service_charge_amount)),
            ("tax", f"F&B VAT/Tax {tax_rate * 100}%", _as_decimal(sale.tax_amount)),
        ]:
            if amount <= 0:
                continue
            row = db.execute(
                text(
                    """
                    INSERT INTO folio_transactions(
                      folio_id, property_code, business_date, txn_type, category,
                      description, amount, currency, booking_id
                    )
                    VALUES(
                      :folio_id, :property_code, :business_date, 'charge', :category,
                      :description, :amount, :currency, :booking_id
                    )
                    RETURNING id
                    """
                ),
                {
                    "folio_id": folio_id,
                    "property_code": property_code,
                    "business_date": data.business_date,
                    "category": category,
                    "description": description,
                    "amount": amount,
                    "currency": PROPERTY_BASE_CURRENCIES.get(property_code, "ETB"),
                    "booking_id": int(data.room_charge_booking_id),
                },
            ).first()
            posted_ids.append(int(row.id))
        sale.folio_transaction_id = posted_ids[0] if posted_ids else None
        _refresh_folio_totals(db, folio_id)
        record_pms_audit_log(
            db,
            property_code=property_code,
            user_email=actor_email,
            module="food_costing",
            action="fnb_charge_posted_to_folio",
            record_type="pos_sale",
            record_id=sale.id,
            new_value={
                "booking_id": data.room_charge_booking_id,
                "folio_id": folio_id,
                "transaction_ids": posted_ids,
                "total_revenue": str(total_revenue),
                "tax": str(sale.tax_amount or 0),
                "service_charge": str(sale.service_charge_amount or 0),
            },
        )

    db.commit()
    db.refresh(sale)

    return sale


def list_pos_sales(db: Session, property_code: str):
    return (
        db.query(PosSale)
        .filter(PosSale.property_code == property_code)
        .order_by(PosSale.created_at.desc())
        .all()
    )


def create_kitchen_requisition(db: Session, data, actor_email: str | None = None):
    # Hotel flow: Chef requests stock first; storekeeper approval/issue deducts Main Store later.
    req = KitchenRequisition(**data.model_dump())
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def approve_kitchen_requisition(db: Session, requisition_id: int, data, actor_email: str | None = None):
    req = (
        db.query(KitchenRequisition)
        .filter(
            KitchenRequisition.id == requisition_id,
            KitchenRequisition.property_code == data.property_code,
        )
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="Store Requisition not found.")
    if str(req.status or "").lower() in {"issued", "closed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Store Requisition is already closed or issued.")
    action = str(data.action or "approve").strip().lower()
    if action not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="Use approve or reject for Store Requisition approval.")
    req.status = "approved" if action == "approve" else "rejected"
    req.issued_by = data.approved_by if action == "approve" else req.issued_by
    req.notes = data.notes or req.notes
    record_pms_audit_log(
        db,
        property_code=data.property_code,
        user_email=actor_email,
        module="food_costing",
        action="store_requisition_approved" if action == "approve" else "store_requisition_rejected",
        record_type="fnb_kitchen_requisition",
        record_id=req.id,
        new_value={
            "ingredient": req.ingredient_name,
            "department": req.outlet_name,
            "approved_by": data.approved_by,
            "status": req.status,
        },
    )
    db.commit()
    db.refresh(req)
    return req


def issue_kitchen_requisition(db: Session, requisition_id: int, data, actor_email: str | None = None):
    req = (
        db.query(KitchenRequisition)
        .filter(
            KitchenRequisition.id == requisition_id,
            KitchenRequisition.property_code == data.property_code,
        )
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="Store Requisition not found.")
    if str(req.status or "").lower() in {"issued", "closed"}:
        raise HTTPException(status_code=409, detail="Store Requisition has already been issued.")
    if str(req.status or "").lower() != "approved":
        raise HTTPException(status_code=409, detail="Store Requisition must be approved before stock can be issued.")
    issued_qty = _as_decimal(data.issued_qty)
    if issued_qty <= 0:
        raise HTTPException(status_code=400, detail="Issued quantity must be greater than zero.")
    if issued_qty > _as_decimal(req.requested_qty):
        raise HTTPException(status_code=400, detail="Issued quantity cannot be more than requested quantity.")
    ingredient = _ingredient_for_name(db, data.property_code, req.ingredient_name)
    if ingredient and ingredient.expiry_date and ingredient.expiry_date < date.today():
        raise HTTPException(status_code=409, detail="Expired stock cannot be issued from Main Store.")
    available = current_stock_quantity(db, data.property_code, req.ingredient_name)
    manager_override = bool(getattr(data, "manager_override", False))
    if issued_qty > available and not manager_override:
        raise HTTPException(status_code=409, detail="Not enough Main Store stock available for this Store Requisition.")
    if issued_qty > available and manager_override and not getattr(data, "override_by", None):
        raise HTTPException(status_code=400, detail="Manager override name is required for negative stock issue.")
    unit_cost = _as_decimal(getattr(ingredient, "average_cost", None) or getattr(ingredient, "cost_per_unit", 0))
    req.issued_qty = issued_qty
    req.issued_by = data.issued_by
    req.status = "issued"
    req.notes = data.notes or req.notes
    db.add(
        InventoryMovement(
            property_code=data.property_code,
            ingredient_name=req.ingredient_name,
            movement_type="KITCHEN_ISSUE",
            quantity=issued_qty,
            unit=req.unit,
            unit_cost=unit_cost,
            stock_value=_money(issued_qty * unit_cost),
            reference=f"Store Requisition #{req.id}",
            notes=data.notes or req.notes or (f"Manager override by {data.override_by}" if manager_override else None),
            created_by=data.issued_by or actor_email or "Storekeeper",
        )
    )
    record_pms_audit_log(
        db,
        property_code=data.property_code,
        user_email=actor_email,
        module="food_costing",
        action="store_requisition_issued",
        record_type="fnb_kitchen_requisition",
        record_id=req.id,
        new_value={
            "ingredient": req.ingredient_name,
            "department": req.outlet_name,
            "requested_qty": str(req.requested_qty),
            "issued_qty": str(issued_qty),
            "manager_override": manager_override,
            "override_by": getattr(data, "override_by", None),
        },
    )
    db.commit()
    db.refresh(req)
    return req


def list_kitchen_requisitions(db: Session, property_code: str):
    return (
        db.query(KitchenRequisition)
        .filter(KitchenRequisition.property_code == property_code)
        .order_by(KitchenRequisition.created_at.desc())
        .all()
    )


def create_wastage_record(db: Session, data, actor_email: str | None = None):
    unit_cost = _as_decimal(data.unit_cost)
    quantity = _as_decimal(data.quantity)
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Waste quantity must be greater than zero.")
    if quantity > current_stock_quantity(db, data.property_code, data.ingredient_name):
        raise HTTPException(status_code=409, detail="Not enough Main Store stock available to record this waste.")
    if unit_cost <= 0:
        ingredient = _ingredient_for_name(db, data.property_code, data.ingredient_name)
        unit_cost = _as_decimal(getattr(ingredient, "cost_per_unit", 0))
    cost = _money(quantity * unit_cost)
    record = WastageRecord(
        property_code=data.property_code,
        ingredient_name=data.ingredient_name,
        quantity=data.quantity,
        unit=data.unit,
        unit_cost=unit_cost,
        cost=cost,
        reason=data.reason,
        recorded_by=data.recorded_by,
        approved_by=data.approved_by,
    )
    db.add(record)
    db.add(
        InventoryMovement(
            property_code=data.property_code,
            ingredient_name=data.ingredient_name,
            movement_type="WASTAGE",
            quantity=data.quantity,
            unit=data.unit,
            unit_cost=unit_cost,
            stock_value=cost,
            reference="Wastage / Spoilage",
            notes=data.reason,
            created_by=data.recorded_by,
        )
    )
    db.flush()
    record_pms_audit_log(
        db,
        property_code=data.property_code,
        user_email=actor_email,
        module="food_costing",
        action="waste_recorded",
        record_type="fnb_wastage_record",
        record_id=record.id,
        new_value={"ingredient": data.ingredient_name, "quantity": data.quantity, "cost": str(cost), "reason": data.reason},
    )
    db.commit()
    db.refresh(record)
    return record


def list_wastage_records(db: Session, property_code: str):
    return (
        db.query(WastageRecord)
        .filter(WastageRecord.property_code == property_code)
        .order_by(WastageRecord.created_at.desc())
        .all()
    )


def create_stock_count(db: Session, data, actor_email: str | None = None):
    unit_cost = _as_decimal(data.unit_cost)
    if unit_cost <= 0:
        ingredient = _ingredient_for_name(db, data.property_code, data.ingredient_name)
        unit_cost = _as_decimal(getattr(ingredient, "cost_per_unit", 0))
    variance = calculate_variance(data.system_qty, data.physical_qty, unit_cost)
    variance_qty = variance["difference"]
    variance_value = variance["variance_value"]
    count = StockCount(
        property_code=data.property_code,
        ingredient_name=data.ingredient_name,
        system_qty=data.system_qty,
        physical_qty=data.physical_qty,
        variance_qty=variance_qty,
        unit=data.unit,
        variance_value=variance_value,
        counted_by=data.counted_by,
        approved_by=data.approved_by,
        notes=data.notes,
    )
    db.add(count)
    db.add(
        InventoryMovement(
            property_code=data.property_code,
            ingredient_name=data.ingredient_name,
            movement_type="ADJUSTMENT",
            quantity=variance_qty,
            unit=data.unit,
            unit_cost=unit_cost,
            stock_value=variance_value,
            reference="Stock count adjustment",
            notes=data.notes,
            created_by=data.counted_by,
        )
    )
    db.flush()
    record_pms_audit_log(
        db,
        property_code=data.property_code,
        user_email=actor_email,
        module="food_costing",
        action="stock_count_adjusted",
        record_type="fnb_stock_count",
        record_id=count.id,
        new_value={"ingredient": data.ingredient_name, "variance_qty": str(variance_qty), "variance_value": str(variance_value)},
    )
    db.commit()
    db.refresh(count)
    return count


def list_stock_counts(db: Session, property_code: str):
    return (
        db.query(StockCount)
        .filter(StockCount.property_code == property_code)
        .order_by(StockCount.created_at.desc())
        .all()
    )


def get_fnb_dashboard(db: Session, property_code: str):
    sales = list_pos_sales(db, property_code)
    movements = list_inventory_movements(db, property_code)
    recipes = list_recipes(db, property_code)
    total_sales = sum(_as_decimal(s.total_revenue) for s in sales)
    wastage_value = sum(_as_decimal(m.stock_value) for m in movements if m.movement_type == "WASTAGE")
    issued_value = sum(_as_decimal(m.stock_value) for m in movements if m.movement_type == "KITCHEN_ISSUE")
    avg_food_cost = Decimal("0")
    if recipes:
        avg_food_cost = sum(_as_decimal(r.food_cost_percentage) for r in recipes) / Decimal(len(recipes))
    return {
        "property_code": property_code,
        "base_currency": PROPERTY_BASE_CURRENCIES.get(property_code, "ETB"),
        "daily_food_cost_percent": float(avg_food_cost),
        "beverage_cost_percent": 0.0,
        "pos_sales": float(total_sales),
        "issued_to_kitchen_value": float(issued_value),
        "wastage_value": float(wastage_value),
        "recipe_count": len(recipes),
        "low_stock_count": len([m for m in movements if m.movement_type == "LOW_STOCK"]),
    }


# =====================================================
# RECIPE INGREDIENT MASTER EDITOR
# =====================================================

def recalculate_recipe_cost(db, recipe_id):
    recipe = (
        db.query(Recipe)
        .filter(Recipe.id == recipe_id)
        .first()
    )

    if not recipe:
        return

    lines = (
        db.query(RecipeIngredient)
        .filter(RecipeIngredient.recipe_id == recipe_id)
        .all()
    )

    total_cost = Decimal("0.00")

    for line in lines:
        total_cost += Decimal(str(line.cost_used or 0))

    recipe.total_cost = total_cost

    selling_price = Decimal(str(recipe.selling_price or 0))

    recipe.food_cost_percentage = calculate_food_cost_percentage(total_cost, selling_price)
    recipe.profit_margin = selling_price - total_cost

    db.commit()


def list_recipe_ingredients(db, recipe_id):
    return (
        db.query(RecipeIngredient)
        .filter(RecipeIngredient.recipe_id == recipe_id)
        .all()
    )


def create_recipe_ingredient(db, data):
    recipe = db.query(Recipe).filter(Recipe.id == data.recipe_id).first()
    if not recipe:
        raise ValueError("Recipe not found")

    ingredient = db.query(Ingredient).filter(Ingredient.id == data.ingredient_id).first()
    if not ingredient:
        raise ValueError("Ingredient not found")

    quantity_used = Decimal(str(data.quantity_used or 0))
    cost_per_unit = Decimal(str(ingredient.cost_per_unit or 0))
    cost_used = quantity_used * cost_per_unit

    line = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        quantity_used=quantity_used,
        cost_used=cost_used,
    )

    db.add(line)
    db.commit()
    db.refresh(line)

    recalculate_recipe_cost(db, recipe.id)

    return line


def delete_recipe_ingredient(db, line_id):
    line = (
        db.query(RecipeIngredient)
        .filter(RecipeIngredient.id == line_id)
        .first()
    )

    if not line:
        return {"error": "Recipe ingredient not found"}

    recipe_id = line.recipe_id

    db.delete(line)
    db.commit()

    recalculate_recipe_cost(db, recipe_id)

    return {"message": "Deleted"}
