from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class IngredientCreate(BaseModel):
    property_code: str
    name: str
    unit: str
    purchase_price: float
    cost_per_unit: float
    supplier_name: Optional[str] = None


class IngredientOut(IngredientCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RecipeIngredientCreate(BaseModel):
    recipe_id: Optional[int] = None
    ingredient_id: int
    quantity_used: float


class RecipeIngredientResponse(BaseModel):
    id: int
    recipe_id: int
    ingredient_id: int
    quantity_used: float
    cost_used: float

    class Config:
        from_attributes = True


class RecipeCreate(BaseModel):
    property_code: str
    name: str
    outlet_name: Optional[str] = None
    selling_price: float
    ingredients: List[RecipeIngredientCreate]


class RecipeOut(BaseModel):
    id: int
    property_code: str
    name: str
    outlet_name: Optional[str] = None
    selling_price: float
    total_cost: float
    food_cost_percentage: float
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PurchaseOrderCreate(BaseModel):
    property_code: str
    supplier_name: str
    ingredient_name: str
    quantity: float
    unit_price: float


class GoodsReceivedCreate(BaseModel):
    property_code: str
    purchase_order_id: int
    supplier_name: str
    ingredient_name: str
    quantity_received: float
    received_by: str
    invoice_number: Optional[str] = None


class InventoryMovementCreate(BaseModel):
    property_code: str
    ingredient_name: str
    movement_type: str
    quantity: float
    unit: str
    reference: Optional[str] = None
    notes: Optional[str] = None
    created_by: str


class PosSaleCreate(BaseModel):
    property_code: str
    outlet_name: str
    menu_item_name: str
    quantity_sold: float
    selling_price: float
    business_date: str
