from datetime import datetime
from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class IngredientCreate(BaseModel):
    property_code: str
    name: str
    category: Optional[str] = None
    unit: str
    purchase_price: float
    cost_per_unit: float
    last_purchase_price: Optional[float] = None
    average_cost: Optional[float] = None
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    reorder_level: Optional[float] = None
    expiry_date: Optional[date] = None
    storage_location: Optional[str] = None


class IngredientOut(IngredientCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SupplierCreate(BaseModel):
    property_code: str
    supplier_name: str
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: Optional[str] = None


class SupplierOut(SupplierCreate):
    id: int
    is_active: bool = True
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
    target_cost_percentage: Optional[float] = 35
    ingredients: List[RecipeIngredientCreate]


class RecipeOut(BaseModel):
    id: int
    property_code: str
    name: str
    outlet_name: Optional[str] = None
    selling_price: float
    total_cost: float
    food_cost_percentage: float
    target_cost_percentage: Optional[float] = None
    profit_margin: Optional[float] = None
    approval_status: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PurchaseOrderCreate(BaseModel):
    property_code: str
    supplier_name: str
    supplier_id: Optional[int] = None
    ingredient_name: str
    quantity: float
    unit_price: float
    invoice_number: Optional[str] = None
    received_by: Optional[str] = None
    approval_status: Optional[str] = "pending"


class PurchaseOrderApproval(BaseModel):
    property_code: str
    approved_by: str
    action: str = "approve"


class GoodsReceivedCreate(BaseModel):
    property_code: str
    purchase_order_id: int
    supplier_name: str
    ingredient_name: str
    ordered_qty: Optional[float] = None
    quantity_received: float
    rejected_qty: Optional[float] = 0
    unit_cost: Optional[float] = None
    received_by: str
    invoice_number: Optional[str] = None


class InventoryMovementCreate(BaseModel):
    property_code: str
    ingredient_name: str
    movement_type: str
    quantity: float
    unit: str
    unit_cost: Optional[float] = None
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
    tax_amount: Optional[float] = None
    service_charge_amount: Optional[float] = None
    payment_method: Optional[str] = "cash"
    room_charge_booking_id: Optional[int] = None


class KitchenRequisitionCreate(BaseModel):
    property_code: str
    ingredient_name: str
    requested_qty: float
    issued_qty: Optional[float] = None
    unit: str
    outlet_name: Optional[str] = None
    requested_by: str
    issued_by: Optional[str] = None
    status: Optional[str] = "requested"
    priority: Optional[str] = "normal"
    notes: Optional[str] = None


class KitchenRequisitionIssue(BaseModel):
    property_code: str
    issued_qty: float
    issued_by: str
    notes: Optional[str] = None
    manager_override: Optional[bool] = False
    override_by: Optional[str] = None


class KitchenRequisitionApproval(BaseModel):
    property_code: str
    approved_by: str
    action: str = "approve"
    notes: Optional[str] = None


class WastageRecordCreate(BaseModel):
    property_code: str
    ingredient_name: str
    quantity: float
    unit: str
    unit_cost: Optional[float] = None
    reason: str
    recorded_by: str
    approved_by: Optional[str] = None


class StockCountCreate(BaseModel):
    property_code: str
    ingredient_name: str
    system_qty: float
    physical_qty: float
    unit: str
    unit_cost: Optional[float] = None
    counted_by: str
    approved_by: Optional[str] = None
    notes: Optional[str] = None


class FnbReportApprovalAction(BaseModel):
    property_code: str
    report_period: str
    report_start_date: date
    report_end_date: date
    action: str
    prepared_by: Optional[str] = None
    override_reason: Optional[str] = None
