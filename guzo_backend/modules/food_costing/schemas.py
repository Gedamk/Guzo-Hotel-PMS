from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import Optional, List


class IngredientCreate(BaseModel):
    property_code: str
    name: str
    unit: str
    purchase_price: Decimal
    cost_per_unit: Decimal
    supplier_name: Optional[str] = None


class IngredientOut(IngredientCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class RecipeIngredientCreate(BaseModel):
    ingredient_id: int
    quantity_used: Decimal


class RecipeCreate(BaseModel):
    property_code: str
    name: str
    outlet_name: Optional[str] = None
    selling_price: Decimal
    ingredients: List[RecipeIngredientCreate]


class RecipeOut(BaseModel):
    id: int
    property_code: str
    name: str
    outlet_name: Optional[str]
    selling_price: Decimal
    total_cost: Decimal
    food_cost_percentage: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


class PurchaseOrderCreate(BaseModel):
    property_code: str
    supplier_name: str
    ingredient_name: str
    quantity: Decimal
    unit_price: Decimal


class GoodsReceivedCreate(BaseModel):
    property_code: str
    purchase_order_id: int
    supplier_name: str
    ingredient_name: str
    quantity_received: Decimal
    received_by: str
    invoice_number: Optional[str] = None


class InventoryMovementCreate(BaseModel):
    property_code: str
    ingredient_name: str
    movement_type: str
    quantity: Decimal
    unit: str
    reference: Optional[str] = None
    notes: Optional[str] = None
    created_by: str


class PosSaleCreate(BaseModel):
    property_code: str
    outlet_name: str
    menu_item_name: str
    quantity_sold: Decimal
    selling_price: Decimal
    business_date: str
