from decimal import Decimal
from sqlalchemy.orm import Session

from guzo_backend.modules.food_costing.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    FoodCostAlert,
    PurchaseOrder,
    GoodsReceived,
    InventoryMovement,
    PosSale,
)

from guzo_backend.modules.food_costing.schemas import (
    IngredientCreate,
    RecipeCreate,
)


# =====================================================
# INGREDIENTS
# =====================================================

def create_ingredient(db: Session, data: IngredientCreate):
    ingredient = Ingredient(**data.model_dump())

    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)

    return ingredient


def list_ingredients(db: Session, property_code: str):
    return (
        db.query(Ingredient)
        .filter(Ingredient.property_code == property_code)
        .order_by(Ingredient.name.asc())
        .all()
    )


# =====================================================
# RECIPES
# =====================================================

def create_recipe(db: Session, data: RecipeCreate):
    total_cost = Decimal("0.00")

    recipe = Recipe(
        property_code=data.property_code,
        name=data.name,
        outlet_name=data.outlet_name,
        selling_price=data.selling_price,
        total_cost=Decimal("0.00"),
        food_cost_percentage=Decimal("0.00"),
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

    if Decimal(str(data.selling_price)) > 0:
        recipe.food_cost_percentage = round(
            (total_cost / Decimal(str(data.selling_price))) * Decimal("100"),
            2,
        )
    else:
        recipe.food_cost_percentage = Decimal("0.00")

    if recipe.food_cost_percentage > 35:
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
    return (
        db.query(Recipe)
        .filter(Recipe.property_code == property_code)
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
        ingredient_name=data.ingredient_name,
        quantity=data.quantity,
        unit_price=data.unit_price,
        total_amount=total_amount,
        status="PENDING",
    )

    db.add(po)
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
    grn = GoodsReceived(**data.model_dump())

    po = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.id == data.purchase_order_id)
        .first()
    )

    if po:
        po.status = "RECEIVED"

    db.add(grn)

    inventory_movement = InventoryMovement(
        property_code=data.property_code,
        ingredient_name=data.ingredient_name,
        movement_type="PURCHASE_RECEIVED",
        quantity=data.quantity_received,
        unit="kg",
        reference=f"GRN #{data.purchase_order_id}",
        notes=(
            f"Auto-created from goods received invoice "
            f"{data.invoice_number or ''}"
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
    movement = InventoryMovement(**data.model_dump())

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


# =====================================================
# POS SALES
# =====================================================

def create_pos_sale(db: Session, data):
    total_revenue = (
        Decimal(str(data.quantity_sold))
        * Decimal(str(data.selling_price))
    )

    sale = PosSale(
        property_code=data.property_code,
        outlet_name=data.outlet_name,
        menu_item_name=data.menu_item_name,
        quantity_sold=data.quantity_sold,
        selling_price=data.selling_price,
        total_revenue=total_revenue,
        business_date=data.business_date,
    )

    db.add(sale)

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
                    property_code=data.property_code,
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

    if selling_price > 0:
        recipe.food_cost_percentage = round(
            (total_cost / selling_price) * Decimal("100"),
            2,
        )
    else:
        recipe.food_cost_percentage = Decimal("0.00")

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
