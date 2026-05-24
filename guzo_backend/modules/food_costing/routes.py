from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from guzo_backend.core.postgres_db import get_db
from guzo_backend.modules.food_costing.schemas import IngredientCreate, IngredientOut, RecipeCreate, RecipeOut, PurchaseOrderCreate, GoodsReceivedCreate, InventoryMovementCreate, PosSaleCreate
from guzo_backend.modules.food_costing import services

router = APIRouter(prefix="/food-costing", tags=["Food Costing"])


@router.post("/ingredients", response_model=IngredientOut)
def create_ingredient(data: IngredientCreate, db: Session = Depends(get_db)):
    return services.create_ingredient(db, data)


@router.get("/ingredients", response_model=list[IngredientOut])
def list_ingredients(property_code: str, db: Session = Depends(get_db)):
    return services.list_ingredients(db, property_code)


@router.post("/recipes", response_model=RecipeOut)
def create_recipe(data: RecipeCreate, db: Session = Depends(get_db)):
    return services.create_recipe(db, data)


@router.get("/recipes", response_model=list[RecipeOut])
def list_recipes(property_code: str, db: Session = Depends(get_db)):
    return services.list_recipes(db, property_code)


@router.get("/alerts")
def list_alerts(property_code: str, db: Session = Depends(get_db)):
    return services.list_alerts(db, property_code)


@router.post("/purchase-orders")
def create_purchase_order(data: PurchaseOrderCreate, db: Session = Depends(get_db)):
    return services.create_purchase_order(db, data)


@router.get("/purchase-orders")
def list_purchase_orders(property_code: str, db: Session = Depends(get_db)):
    return services.list_purchase_orders(db, property_code)


@router.post("/goods-received")
def create_goods_received(data: GoodsReceivedCreate, db: Session = Depends(get_db)):
    return services.create_goods_received(db, data)


@router.get("/goods-received")
def list_goods_received(property_code: str, db: Session = Depends(get_db)):
    return services.list_goods_received(db, property_code)


@router.post("/inventory-movements")
def create_inventory_movement_api(
    data: InventoryMovementCreate,
    db: Session = Depends(get_db),
):
    return services.create_inventory_movement(db, data)




@router.get("/inventory-movements")
def list_inventory_movements(property_code: str, db: Session = Depends(get_db)):
    return services.list_inventory_movements(db, property_code)


@router.post("/pos-sales")
def create_pos_sale(data: PosSaleCreate, db: Session = Depends(get_db)):
    return services.create_pos_sale(db, data)


@router.get("/pos-sales")
def list_pos_sales(property_code: str, db: Session = Depends(get_db)):
    return services.list_pos_sales(db, property_code)
