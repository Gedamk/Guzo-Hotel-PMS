from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guzo_backend.modules.food_costing.models import Base, InventoryMovement, Recipe
from guzo_backend.modules.food_costing.schemas import (
    GoodsReceivedCreate,
    IngredientCreate,
    KitchenRequisitionCreate,
    KitchenRequisitionIssue,
    KitchenRequisitionApproval,
    PurchaseOrderApproval,
    PurchaseOrderCreate,
    RecipeCreate,
    RecipeIngredientCreate,
)
from guzo_backend.modules.food_costing import services
from guzo_backend.services.pms_security_service import DEFAULT_PERMISSION_MAP


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    return TestingSession()


def test_purchase_order_approval(monkeypatch):
    monkeypatch.setattr(services, "record_pms_audit_log", lambda *args, **kwargs: None)
    db = _db()
    po = services.create_purchase_order(
        db,
        PurchaseOrderCreate(
            property_code="DRE001",
            supplier_name="Local F&B Supplier",
            ingredient_name="Teff flour",
            quantity=25,
            unit_price=80,
        ),
    )

    approved = services.approve_purchase_order(
        db,
        po.id,
        PurchaseOrderApproval(property_code="DRE001", approved_by="Purchasing Manager"),
        actor_email="purchasing@guzo.local",
    )

    assert approved.approval_status == "approved"
    assert approved.status == "APPROVED"


def test_receiving_updates_inventory():
    db = _db()
    services.create_ingredient(
        db,
        IngredientCreate(
            property_code="DRE001",
            name="Teff flour",
            category="Food",
            unit="kg",
            purchase_price=80,
            cost_per_unit=80,
        ),
    )
    po = services.create_purchase_order(
        db,
        PurchaseOrderCreate(
            property_code="DRE001",
            supplier_name="Addis Supplier",
            ingredient_name="Teff flour",
            quantity=20,
            unit_price=90,
            approval_status="approved",
        ),
    )
    po.status = "APPROVED"
    db.commit()

    services.create_goods_received(
        db,
        GoodsReceivedCreate(
            property_code="DRE001",
            purchase_order_id=po.id,
            supplier_name="Addis Supplier",
            ingredient_name="Teff flour",
            ordered_qty=20,
            quantity_received=18,
            rejected_qty=2,
            unit_cost=90,
            received_by="Storekeeper",
            invoice_number="INV-100",
        ),
    )

    assert services.current_stock_quantity(db, "DRE001", "Teff flour") == Decimal("18.000")
    movement = db.query(InventoryMovement).filter(InventoryMovement.ingredient_name == "Teff flour").one()
    assert movement.unit == "kg"
    assert movement.stock_value == Decimal("1620.00")


def test_receiving_updates_unit_cost_after_grn(monkeypatch):
    monkeypatch.setattr(services, "record_pms_audit_log", lambda *args, **kwargs: None)
    db = _db()
    ingredient = services.create_ingredient(
        db,
        IngredientCreate(
            property_code="DRE001",
            name="Niter kibbeh",
            category="Food",
            unit="kg",
            purchase_price=120,
            cost_per_unit=120,
        ),
    )
    po = services.create_purchase_order(
        db,
        PurchaseOrderCreate(
            property_code="DRE001",
            supplier_name="Addis Dairy Supplier",
            ingredient_name="Niter kibbeh",
            quantity=5,
            unit_price=150,
            approval_status="approved",
        ),
    )
    po.status = "APPROVED"
    db.commit()

    services.create_goods_received(
        db,
        GoodsReceivedCreate(
            property_code="DRE001",
            purchase_order_id=po.id,
            supplier_name="Addis Dairy Supplier",
            ingredient_name="Niter kibbeh",
            ordered_qty=5,
            quantity_received=5,
            rejected_qty=0,
            unit_cost=150,
            received_by="Storekeeper",
            invoice_number="INV-200",
        ),
    )

    db.refresh(ingredient)
    assert ingredient.cost_per_unit == Decimal("150.0000")
    assert ingredient.average_cost == Decimal("150.0000")
    assert ingredient.last_purchase_price == Decimal("150.00")


def test_issuing_deducts_inventory(monkeypatch):
    monkeypatch.setattr(services, "record_pms_audit_log", lambda *args, **kwargs: None)
    db = _db()
    services.create_ingredient(
        db,
        IngredientCreate(
            property_code="DRE001",
            name="Berbere",
            category="Food",
            unit="kg",
            purchase_price=200,
            cost_per_unit=200,
        ),
    )
    services.create_inventory_movement(
        db,
        type(
            "Movement",
            (),
            {
                "model_dump": lambda self: {
                    "property_code": "DRE001",
                    "ingredient_name": "Berbere",
                    "movement_type": "OPENING",
                    "quantity": 10,
                    "unit": "kg",
                    "unit_cost": 200,
                    "reference": "Opening balance",
                    "notes": None,
                    "created_by": "Storekeeper",
                }
            },
        )(),
    )
    req = services.create_kitchen_requisition(
        db,
        KitchenRequisitionCreate(
            property_code="DRE001",
            ingredient_name="Berbere",
            requested_qty=3,
            unit="kg",
            outlet_name="Ethiopian Traditional Kitchen",
            requested_by="Chef",
        ),
    )
    services.approve_kitchen_requisition(
        db,
        req.id,
        KitchenRequisitionApproval(property_code="DRE001", approved_by="Executive Chef"),
        actor_email="executive.chef@guzo.local",
    )

    services.issue_kitchen_requisition(
        db,
        req.id,
        KitchenRequisitionIssue(property_code="DRE001", issued_qty=3, issued_by="Storekeeper"),
        actor_email="storekeeper@guzo.local",
    )

    assert services.current_stock_quantity(db, "DRE001", "Berbere") == Decimal("7.000")


def test_expired_stock_cannot_be_issued(monkeypatch):
    monkeypatch.setattr(services, "record_pms_audit_log", lambda *args, **kwargs: None)
    db = _db()
    services.create_ingredient(
        db,
        IngredientCreate(
            property_code="DRE001",
            name="Cream",
            category="Food",
            unit="liter",
            purchase_price=250,
            cost_per_unit=250,
            expiry_date=date.today() - timedelta(days=1),
        ),
    )
    services.create_inventory_movement(
        db,
        type(
            "Movement",
            (),
            {
                "model_dump": lambda self: {
                    "property_code": "DRE001",
                    "ingredient_name": "Cream",
                    "movement_type": "OPENING",
                    "quantity": 3,
                    "unit": "liter",
                    "unit_cost": 250,
                    "reference": "Opening balance",
                    "notes": None,
                    "created_by": "Storekeeper",
                }
            },
        )(),
    )
    req = services.create_kitchen_requisition(
        db,
        KitchenRequisitionCreate(
            property_code="DRE001",
            ingredient_name="Cream",
            requested_qty=1,
            unit="liter",
            outlet_name="Pastry/Bakery",
            requested_by="Chef",
        ),
    )
    services.approve_kitchen_requisition(
        db,
        req.id,
        KitchenRequisitionApproval(property_code="DRE001", approved_by="Executive Chef"),
        actor_email="executive.chef@guzo.local",
    )

    with pytest.raises(Exception) as exc:
        services.issue_kitchen_requisition(
            db,
            req.id,
            KitchenRequisitionIssue(property_code="DRE001", issued_qty=1, issued_by="Storekeeper"),
            actor_email="storekeeper@guzo.local",
        )

    assert "Expired stock cannot be issued" in str(exc.value)


def test_store_control_issue_requires_approved_requisition(monkeypatch):
    monkeypatch.setattr(services, "record_pms_audit_log", lambda *args, **kwargs: None)
    db = _db()
    services.create_ingredient(
        db,
        IngredientCreate(property_code="DRE001", name="Coffee beans", category="Beverage", unit="kg", purchase_price=600, cost_per_unit=600),
    )
    services.create_inventory_movement(
        db,
        type(
            "Movement",
            (),
            {"model_dump": lambda self: {"property_code": "DRE001", "ingredient_name": "Coffee beans", "movement_type": "OPENING", "quantity": 2, "unit": "kg", "unit_cost": 600, "reference": "Opening", "notes": None, "created_by": "Storekeeper"}},
        )(),
    )
    req = services.create_kitchen_requisition(
        db,
        KitchenRequisitionCreate(property_code="DRE001", ingredient_name="Coffee beans", requested_qty=1, unit="kg", outlet_name="Coffee Shop", requested_by="Chef"),
    )

    with pytest.raises(Exception) as exc:
        services.issue_kitchen_requisition(
            db,
            req.id,
            KitchenRequisitionIssue(property_code="DRE001", issued_qty=1, issued_by="Storekeeper"),
            actor_email="storekeeper@guzo.local",
        )

    assert "must be approved" in str(exc.value)


def test_store_control_blocks_over_issue_without_manager_override(monkeypatch):
    monkeypatch.setattr(services, "record_pms_audit_log", lambda *args, **kwargs: None)
    db = _db()
    services.create_ingredient(
        db,
        IngredientCreate(property_code="DRE001", name="Bottled water", category="Beverage", unit="bottle", purchase_price=25, cost_per_unit=25),
    )
    req = services.create_kitchen_requisition(
        db,
        KitchenRequisitionCreate(property_code="DRE001", ingredient_name="Bottled water", requested_qty=5, unit="bottle", outlet_name="Bar", requested_by="Chef"),
    )
    services.approve_kitchen_requisition(
        db,
        req.id,
        KitchenRequisitionApproval(property_code="DRE001", approved_by="F&B Manager"),
        actor_email="fnb.manager@guzo.local",
    )

    with pytest.raises(Exception) as exc:
        services.issue_kitchen_requisition(
            db,
            req.id,
            KitchenRequisitionIssue(property_code="DRE001", issued_qty=5, issued_by="Storekeeper"),
            actor_email="storekeeper@guzo.local",
        )

    assert "Not enough Main Store stock" in str(exc.value)


def test_store_control_manager_override_allows_negative_stock(monkeypatch):
    monkeypatch.setattr(services, "record_pms_audit_log", lambda *args, **kwargs: None)
    db = _db()
    services.create_ingredient(
        db,
        IngredientCreate(property_code="DRE001", name="Soft drinks", category="Beverage", unit="bottle", purchase_price=30, cost_per_unit=30),
    )
    req = services.create_kitchen_requisition(
        db,
        KitchenRequisitionCreate(property_code="DRE001", ingredient_name="Soft drinks", requested_qty=2, unit="bottle", outlet_name="Bar", requested_by="Chef"),
    )
    services.approve_kitchen_requisition(
        db,
        req.id,
        KitchenRequisitionApproval(property_code="DRE001", approved_by="F&B Manager"),
        actor_email="fnb.manager@guzo.local",
    )
    services.issue_kitchen_requisition(
        db,
        req.id,
        KitchenRequisitionIssue(property_code="DRE001", issued_qty=2, issued_by="Storekeeper", manager_override=True, override_by="F&B Manager"),
        actor_email="storekeeper@guzo.local",
    )

    assert services.current_stock_quantity(db, "DRE001", "Soft drinks") == Decimal("-2.000")


def test_store_control_ledger_low_stock_and_total_value():
    db = _db()
    services.create_ingredient(
        db,
        IngredientCreate(property_code="DRE001", name="Shiro", category="Food", unit="kg", purchase_price=100, cost_per_unit=100, reorder_level=5),
    )
    services.create_inventory_movement(
        db,
        type(
            "Movement",
            (),
            {"model_dump": lambda self: {"property_code": "DRE001", "ingredient_name": "Shiro", "movement_type": "OPENING", "quantity": 4, "unit": "kg", "unit_cost": 100, "reference": "Opening", "notes": None, "created_by": "Storekeeper"}},
        )(),
    )

    ledger = services.get_main_store_ledger(db, "DRE001")
    row = next(item for item in ledger if item["item_name"] == "Shiro")

    assert row["status"] == "LOW STOCK"
    assert row["total_balance"] == Decimal("4")
    assert row["balance_on_hand"] == Decimal("4")
    assert row["total_value"] == Decimal("400.00")


def test_recipe_cost_calculation():
    db = _db()
    ingredient = services.create_ingredient(
        db,
        IngredientCreate(
            property_code="DRE001",
            name="Coffee beans",
            category="Beverage",
            unit="kg",
            purchase_price=600,
            cost_per_unit=600,
        ),
    )
    recipe = services.create_recipe(
        db,
        RecipeCreate(
            property_code="DRE001",
            name="Ethiopian Coffee",
            outlet_name="Coffee Shop",
            selling_price=150,
            ingredients=[RecipeIngredientCreate(ingredient_id=ingredient.id, quantity_used=0.05)],
        ),
    )

    assert recipe.total_cost == Decimal("30.00")
    assert recipe.food_cost_percentage == Decimal("20.00")


def test_five_star_alacarte_seed_is_idempotent_and_costing_ready():
    db = _db()
    expected_names = {seed["name"] for seed in services.FIVE_STAR_ALACARTE_RECIPES}

    services.ensure_five_star_alacarte_seed_data(db, "DRE001")
    services.ensure_five_star_alacarte_seed_data(db, "DRE001")

    recipes = db.query(Recipe).filter(Recipe.property_code == "DRE001").all()
    seeded_recipes = [recipe for recipe in recipes if recipe.name in expected_names]

    assert len(seeded_recipes) == 5
    assert {recipe.name for recipe in seeded_recipes} == expected_names
    for recipe_name in expected_names:
        assert sum(1 for recipe in seeded_recipes if recipe.name == recipe_name) == 1

    recipe_costing_names = {recipe.name for recipe in services.list_recipes(db, "DRE001")}
    assert expected_names.issubset(recipe_costing_names)

    ala_carte_costing_names = {
        recipe.name
        for recipe in services.list_recipes(db, "DRE001")
        if recipe.name in expected_names
    }
    assert ala_carte_costing_names == expected_names

    for recipe in seeded_recipes:
        gross_profit = Decimal(str(recipe.selling_price)) - Decimal(str(recipe.total_cost))
        assert Decimal(str(recipe.selling_price)) > Decimal("0")
        assert Decimal(str(recipe.total_cost)) > Decimal("0")
        assert Decimal(str(recipe.food_cost_percentage)) > Decimal("0")
        assert gross_profit > Decimal("0")
        assert recipe.approval_status == "approved"


def test_buffet_cost_per_guest():
    assert services.calculate_buffet_cost_per_guest(24000, 80) == Decimal("300.00")


def test_beverage_cost_per_serving():
    result = services.calculate_beverage_cost_per_serving(bottle_cost=600, bottle_size=750, serving_size=150)
    assert result["expected_servings"] == Decimal("5.000")
    assert result["cost_per_serving"] == Decimal("120.00")


def test_variance_calculation():
    result = services.calculate_variance(expected_usage=10, actual_usage=12.5, unit_cost=80)
    assert result["difference"] == Decimal("2.5")
    assert result["variance_value"] == Decimal("200.00")


def test_fnb_role_permission_checks():
    assert "fnb.receive_goods" in DEFAULT_PERMISSION_MAP["storekeeper"]
    assert "fnb.issue_stock" in DEFAULT_PERMISSION_MAP["storekeeper"]
    assert "fnb.request_stock" in DEFAULT_PERMISSION_MAP["chef"]
    assert "fnb.issue_stock" not in DEFAULT_PERMISSION_MAP["chef"]
    assert "fnb.approve_report" in DEFAULT_PERMISSION_MAP["executive_chef"]
    assert "fnb.approve_purchase_order" in DEFAULT_PERMISSION_MAP["purchasing_manager"]
    assert "fnb.view_reports" in DEFAULT_PERMISSION_MAP["finance_manager"]
    assert "fnb.finance_review_report" in DEFAULT_PERMISSION_MAP["finance_manager"]
    assert "fnb.override_report" in DEFAULT_PERMISSION_MAP["admin"]
