from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from guzo_backend.core.postgres_db import get_db

from guzo_backend.modules.food_costing.schemas import (
    IngredientCreate,
    IngredientOut,
    RecipeCreate,
    RecipeOut,
    SupplierCreate,
    SupplierOut,
    PurchaseOrderCreate,
    PurchaseOrderApproval,
    GoodsReceivedCreate,
    InventoryMovementCreate,
    PosSaleCreate,
    RecipeIngredientCreate,
    KitchenRequisitionCreate,
    KitchenRequisitionIssue,
    KitchenRequisitionApproval,
    WastageRecordCreate,
    StockCountCreate,
    FnbReportApprovalAction,
)

from guzo_backend.modules.food_costing import services
from guzo_backend.services.pms_security_service import record_pms_audit_log, require_pms_permission

router = APIRouter(
    prefix="/food-costing",
    tags=["Food Costing"],
)


# =====================================================
# SUPPLIERS
# =====================================================

@router.post("/suppliers", response_model=SupplierOut)
def create_supplier(
    data: SupplierCreate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    actor = require_pms_permission(
        db,
        permission_key="fnb.create_purchase_order",
        property_code=data.property_code,
        user_email=x_pms_user_email,
    )
    supplier = services.create_supplier(db, data)
    record_pms_audit_log(
        db,
        property_code=data.property_code,
        user_email=actor["email"],
        module="food_costing",
        action="supplier_created",
        record_type="fnb_supplier",
        record_id=supplier.id,
        new_value={"supplier_name": supplier.supplier_name},
    )
    db.commit()
    return supplier


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(
    property_code: str,
    db: Session = Depends(get_db),
):
    return services.list_suppliers(db, property_code)


# =====================================================
# INGREDIENTS
# =====================================================

@router.post("/ingredients", response_model=IngredientOut)
def create_ingredient(
    data: IngredientCreate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    actor = require_pms_permission(
        db,
        permission_key="fnb.manage_recipes",
        property_code=data.property_code,
        user_email=x_pms_user_email,
    )
    ingredient = services.create_ingredient(db, data)
    record_pms_audit_log(
        db,
        property_code=data.property_code,
        user_email=actor["email"],
        module="food_costing",
        action="ingredient_master_updated",
        record_type="ingredient",
        record_id=ingredient.id,
        new_value={"ingredient_name": ingredient.name, "average_cost": str(ingredient.average_cost or ingredient.cost_per_unit)},
    )
    db.commit()
    return ingredient


@router.get("/ingredients", response_model=list[IngredientOut])
def list_ingredients(
    property_code: str,
    db: Session = Depends(get_db),
):
    return services.list_ingredients(db, property_code)


# =====================================================
# RECIPES
# =====================================================

@router.post("/recipes", response_model=RecipeOut)
def create_recipe(
    data: RecipeCreate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    actor = require_pms_permission(
        db,
        permission_key="fnb.manage_recipes",
        property_code=data.property_code,
        user_email=x_pms_user_email,
    )
    recipe = services.create_recipe(db, data)
    record_pms_audit_log(
        db,
        property_code=data.property_code,
        user_email=actor["email"],
        module="food_costing",
        action="recipe_cost_updated",
        record_type="recipe",
        record_id=recipe.id,
        new_value={"menu_item": recipe.name, "food_cost_percentage": str(recipe.food_cost_percentage)},
    )
    db.commit()
    return recipe


@router.get("/recipes", response_model=list[RecipeOut])
def list_recipes(
    property_code: str,
    db: Session = Depends(get_db),
):
    return services.list_recipes(db, property_code)


# =====================================================
# RECIPE INGREDIENT MASTER
# =====================================================

@router.get("/recipes/{recipe_id}/ingredients")
def get_recipe_ingredients(
    recipe_id: int,
    db: Session = Depends(get_db),
):
    return services.list_recipe_ingredients(db, recipe_id)




@router.delete("/recipes/ingredients/{line_id}")
def delete_recipe_ingredient_api(
    line_id: int,
    db: Session = Depends(get_db),
):
    return services.delete_recipe_ingredient(db, line_id)


# =====================================================
# FOOD COST ALERTS
# =====================================================

@router.get("/alerts")
def list_alerts(
    property_code: str,
    db: Session = Depends(get_db),
):
    return services.list_alerts(db, property_code)


# =====================================================
# PURCHASE ORDERS
# =====================================================

@router.post("/purchase-orders")
def create_purchase_order(
    data: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    actor = require_pms_permission(
        db,
        permission_key="fnb.create_purchase_order",
        property_code=data.property_code,
        user_email=x_pms_user_email,
    )
    po = services.create_purchase_order(db, data)
    record_pms_audit_log(
        db,
        property_code=data.property_code,
        user_email=actor["email"],
        module="food_costing",
        action="purchase_order_created",
        record_type="purchase_order",
        record_id=po.id,
        new_value={"supplier": po.supplier_name, "ingredient": po.ingredient_name, "total_amount": str(po.total_amount)},
    )
    db.commit()
    return po


@router.get("/purchase-orders")
def list_purchase_orders(
    property_code: str,
    db: Session = Depends(get_db),
):
    return services.list_purchase_orders(db, property_code)


@router.patch("/purchase-orders/{purchase_order_id}/approval")
def approve_purchase_order(
    purchase_order_id: int,
    data: PurchaseOrderApproval,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    actor = require_pms_permission(
        db,
        permission_key="fnb.approve_purchase_order",
        property_code=data.property_code,
        user_email=x_pms_user_email,
    )
    return services.approve_purchase_order(db, purchase_order_id, data, actor_email=actor["email"])


# =====================================================
# GOODS RECEIVED
# =====================================================

@router.post("/goods-received")
def create_goods_received(
    data: GoodsReceivedCreate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    actor = require_pms_permission(
        db,
        permission_key="fnb.receive_goods",
        property_code=data.property_code,
        user_email=x_pms_user_email,
    )
    grn = services.create_goods_received(db, data)
    record_pms_audit_log(
        db,
        property_code=data.property_code,
        user_email=actor["email"],
        module="food_costing",
        action="goods_received",
        record_type="goods_received",
        record_id=grn.id,
        new_value={"po_id": grn.purchase_order_id, "received_qty": str(grn.quantity_received)},
    )
    db.commit()
    return grn


@router.get("/goods-received")
def list_goods_received(
    property_code: str,
    db: Session = Depends(get_db),
):
    return services.list_goods_received(db, property_code)


# =====================================================
# INVENTORY MOVEMENTS
# =====================================================

@router.post("/inventory-movements")
def create_inventory_movement_api(
    data: InventoryMovementCreate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    permission = "fnb.record_waste" if data.movement_type.upper() == "WASTAGE" else "fnb.issue_stock"
    actor = require_pms_permission(
        db,
        permission_key=permission,
        property_code=data.property_code,
        user_email=x_pms_user_email,
    )
    movement = services.create_inventory_movement(db, data)
    action = "waste_recorded" if data.movement_type.upper() == "WASTAGE" else "kitchen_issue"
    record_pms_audit_log(
        db,
        property_code=data.property_code,
        user_email=actor["email"],
        module="food_costing",
        action=action,
        record_type="inventory_movement",
        record_id=movement.id,
        new_value={"ingredient": movement.ingredient_name, "movement_type": movement.movement_type, "quantity": str(movement.quantity)},
    )
    db.commit()
    return movement


@router.get("/inventory-movements")
def list_inventory_movements(
    property_code: str,
    db: Session = Depends(get_db),
):
    return services.list_inventory_movements(db, property_code)


# =====================================================
# POS SALES
# =====================================================

@router.post("/pos-sales")
def create_pos_sale(
    data: PosSaleCreate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    actor = None
    if data.room_charge_booking_id:
        actor = require_pms_permission(
            db,
            permission_key="fnb.post_room_charge",
            property_code=data.property_code,
            user_email=x_pms_user_email,
        )
    return services.create_pos_sale(db, data, actor_email=(actor or {}).get("email"))


@router.get("/pos-sales")
def list_pos_sales(
    property_code: str,
    db: Session = Depends(get_db),
):
    return services.list_pos_sales(db, property_code)

@router.post("/recipes/ingredients")
def create_recipe_ingredient_api(
    data: RecipeIngredientCreate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    recipe = db.query(services.Recipe).filter(services.Recipe.id == data.recipe_id).first() if data.recipe_id else None
    require_pms_permission(
        db,
        permission_key="fnb.manage_recipes",
        property_code=getattr(recipe, "property_code", None),
        user_email=x_pms_user_email,
    )
    line = services.create_recipe_ingredient(db, data)
    return {
        "id": line.id,
        "recipe_id": line.recipe_id,
        "ingredient_id": line.ingredient_id,
        "quantity_used": float(line.quantity_used),
        "cost_used": float(line.cost_used),
    }


# =====================================================
# KITCHEN REQUISITIONS / WASTE / STOCK COUNT / REPORTS
# =====================================================

@router.post("/kitchen-requisitions")
def create_kitchen_requisition(
    data: KitchenRequisitionCreate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    actor = require_pms_permission(
        db,
        permission_key="fnb.request_stock",
        property_code=data.property_code,
        user_email=x_pms_user_email,
    )
    req = services.create_kitchen_requisition(db, data, actor_email=actor["email"])
    record_pms_audit_log(
        db,
        property_code=data.property_code,
        user_email=actor["email"],
        module="food_costing",
        action="store_requisition_requested",
        record_type="fnb_kitchen_requisition",
        record_id=req.id,
        new_value={"ingredient": req.ingredient_name, "department": req.outlet_name, "requested_qty": str(req.requested_qty)},
    )
    db.commit()
    return req


@router.patch("/kitchen-requisitions/{requisition_id}/issue")
def issue_kitchen_requisition(
    requisition_id: int,
    data: KitchenRequisitionIssue,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    actor = require_pms_permission(
        db,
        permission_key="fnb.issue_stock",
        property_code=data.property_code,
        user_email=x_pms_user_email,
    )
    return services.issue_kitchen_requisition(db, requisition_id, data, actor_email=actor["email"])


@router.patch("/kitchen-requisitions/{requisition_id}/approval")
def approve_kitchen_requisition(
    requisition_id: int,
    data: KitchenRequisitionApproval,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    actor = require_pms_permission(
        db,
        permission_key="fnb.approve_report",
        property_code=data.property_code,
        user_email=x_pms_user_email,
    )
    return services.approve_kitchen_requisition(db, requisition_id, data, actor_email=actor["email"])


@router.get("/kitchen-requisitions")
def list_kitchen_requisitions(
    property_code: str,
    db: Session = Depends(get_db),
):
    return services.list_kitchen_requisitions(db, property_code)


@router.get("/store-ledger")
def get_main_store_ledger(
    property_code: str,
    db: Session = Depends(get_db),
):
    return services.get_main_store_ledger(db, property_code)


@router.get("/store-reports")
def get_store_control_reports(
    property_code: str,
    db: Session = Depends(get_db),
):
    return services.get_store_control_reports(db, property_code)


@router.post("/wastage")
def create_wastage_record(
    data: WastageRecordCreate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    actor = require_pms_permission(
        db,
        permission_key="fnb.record_waste",
        property_code=data.property_code,
        user_email=x_pms_user_email,
    )
    return services.create_wastage_record(db, data, actor_email=actor["email"])


@router.get("/wastage")
def list_wastage_records(
    property_code: str,
    db: Session = Depends(get_db),
):
    return services.list_wastage_records(db, property_code)


@router.post("/stock-counts")
def create_stock_count(
    data: StockCountCreate,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    actor = require_pms_permission(
        db,
        permission_key="fnb.stock_count",
        property_code=data.property_code,
        user_email=x_pms_user_email,
    )
    return services.create_stock_count(db, data, actor_email=actor["email"])


@router.get("/stock-counts")
def list_stock_counts(
    property_code: str,
    db: Session = Depends(get_db),
):
    return services.list_stock_counts(db, property_code)


@router.get("/dashboard")
def get_fnb_dashboard(
    property_code: str,
    db: Session = Depends(get_db),
):
    return services.get_fnb_dashboard(db, property_code)


@router.get("/reports/approval")
def get_report_approval(
    property_code: str,
    report_period: str,
    report_start_date: str,
    report_end_date: str,
    db: Session = Depends(get_db),
):
    return services.get_report_approval(
        db,
        property_code.strip().upper(),
        report_period.strip().lower(),
        report_start_date,
        report_end_date,
    )


@router.patch("/reports/approval")
def update_report_approval(
    data: FnbReportApprovalAction,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    permission_by_action = {
        "submit": "fnb.submit_report",
        "finance_review": "fnb.finance_review_report",
        "fnb_approve": "fnb.approve_report",
        "gm_lock": "fnb.gm_lock_report",
        "override": "fnb.override_report",
    }
    action = data.action.strip().lower()
    permission = permission_by_action.get(action)
    if not permission:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Unsupported F&B report approval action: {data.action}")
    actor = require_pms_permission(
        db,
        permission_key=permission,
        property_code=data.property_code,
        user_email=x_pms_user_email,
    )
    return services.update_report_approval(db, data, actor["email"])
