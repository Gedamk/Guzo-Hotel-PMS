from sqlalchemy import Boolean, Column, Date, Integer, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    property_code = Column(String(20), index=True, nullable=False)
    name = Column(String(150), nullable=False)
    category = Column(String(80), nullable=True)
    unit = Column(String(20), nullable=False)
    purchase_price = Column(Numeric(10, 2), nullable=False)
    cost_per_unit = Column(Numeric(10, 4), nullable=False)
    last_purchase_price = Column(Numeric(10, 2), nullable=True)
    average_cost = Column(Numeric(10, 4), nullable=True)
    supplier_id = Column(Integer, nullable=True)
    supplier_name = Column(String(150), nullable=True)
    reorder_level = Column(Numeric(12, 3), nullable=True)
    expiry_date = Column(Date, nullable=True)
    storage_location = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Supplier(Base):
    __tablename__ = "fnb_suppliers"

    id = Column(Integer, primary_key=True, index=True)
    property_code = Column(String(20), index=True, nullable=False)
    supplier_name = Column(String(150), nullable=False)
    contact_name = Column(String(150), nullable=True)
    phone = Column(String(80), nullable=True)
    email = Column(String(150), nullable=True)
    tax_id = Column(String(80), nullable=True)
    payment_terms = Column(String(120), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    property_code = Column(String(20), index=True, nullable=False)
    name = Column(String(150), nullable=False)
    outlet_name = Column(String(150), nullable=True)
    selling_price = Column(Numeric(10, 2), nullable=False)
    total_cost = Column(Numeric(10, 2), nullable=False, default=0)
    food_cost_percentage = Column(Numeric(10, 2), nullable=False, default=0)
    target_cost_percentage = Column(Numeric(10, 2), nullable=True)
    profit_margin = Column(Numeric(10, 2), nullable=True)
    approval_status = Column(String(40), default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    quantity_used = Column(Numeric(10, 3), nullable=False)
    cost_used = Column(Numeric(10, 2), nullable=False)


class FoodCostAlert(Base):
    __tablename__ = "food_cost_alerts"

    id = Column(Integer, primary_key=True, index=True)
    property_code = Column(String(20), index=True, nullable=False)
    alert_type = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), default="medium")
    created_at = Column(DateTime(timezone=True), server_default=func.now())



class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    property_code = Column(String, nullable=False)
    supplier_name = Column(String, nullable=False)
    supplier_id = Column(Integer, nullable=True)
    ingredient_name = Column(String, nullable=False)
    quantity = Column(Numeric(12, 3), nullable=False)
    ordered_qty = Column(Numeric(12, 3), nullable=True)
    received_qty = Column(Numeric(12, 3), nullable=True)
    rejected_qty = Column(Numeric(12, 3), nullable=True)
    unit_price = Column(Numeric(12, 2), nullable=False)
    unit_cost = Column(Numeric(12, 2), nullable=True)
    invoice_number = Column(String(120), nullable=True)
    received_by = Column(String(150), nullable=True)
    approval_status = Column(String(40), default="pending")
    total_amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GoodsReceived(Base):
    __tablename__ = "goods_received"

    id = Column(Integer, primary_key=True, index=True)
    property_code = Column(String, nullable=False)
    purchase_order_id = Column(Integer, nullable=False)
    supplier_name = Column(String, nullable=False)
    ingredient_name = Column(String, nullable=False)
    ordered_qty = Column(Numeric(12, 3), nullable=True)
    quantity_received = Column(Numeric(12, 3), nullable=False)
    rejected_qty = Column(Numeric(12, 3), nullable=True)
    unit_cost = Column(Numeric(12, 2), nullable=True)
    received_by = Column(String, nullable=False)
    invoice_number = Column(String, nullable=True)
    approval_status = Column(String(40), default="received")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True)
    property_code = Column(String, nullable=False)
    ingredient_name = Column(String, nullable=False)
    movement_type = Column(String, nullable=False)  # OPENING, PURCHASE_RECEIVED, KITCHEN_ISSUE, WASTAGE, ADJUSTMENT
    quantity = Column(Numeric(12, 3), nullable=False)
    unit = Column(String, nullable=False)
    unit_cost = Column(Numeric(12, 2), nullable=True)
    stock_value = Column(Numeric(12, 2), nullable=True)
    reference = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PosSale(Base):
    __tablename__ = "pos_sales"

    id = Column(Integer, primary_key=True, index=True)
    property_code = Column(String, nullable=False)
    outlet_name = Column(String, nullable=False)
    menu_item_name = Column(String, nullable=False)
    quantity_sold = Column(Numeric(12, 3), nullable=False)
    selling_price = Column(Numeric(12, 2), nullable=False)
    total_revenue = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), nullable=True)
    service_charge_amount = Column(Numeric(12, 2), nullable=True)
    payment_method = Column(String(80), nullable=True)
    room_charge_booking_id = Column(Integer, nullable=True)
    folio_transaction_id = Column(Integer, nullable=True)
    business_date = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KitchenRequisition(Base):
    __tablename__ = "fnb_kitchen_requisitions"

    id = Column(Integer, primary_key=True, index=True)
    property_code = Column(String(20), index=True, nullable=False)
    ingredient_name = Column(String(150), nullable=False)
    requested_qty = Column(Numeric(12, 3), nullable=False)
    issued_qty = Column(Numeric(12, 3), nullable=True)
    unit = Column(String(20), nullable=False)
    outlet_name = Column(String(150), nullable=True)
    requested_by = Column(String(150), nullable=False)
    issued_by = Column(String(150), nullable=True)
    status = Column(String(40), default="requested")
    priority = Column(String(40), default="normal")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WastageRecord(Base):
    __tablename__ = "fnb_wastage_records"

    id = Column(Integer, primary_key=True, index=True)
    property_code = Column(String(20), index=True, nullable=False)
    ingredient_name = Column(String(150), nullable=False)
    quantity = Column(Numeric(12, 3), nullable=False)
    unit = Column(String(20), nullable=False)
    unit_cost = Column(Numeric(12, 2), nullable=False)
    cost = Column(Numeric(12, 2), nullable=False)
    reason = Column(Text, nullable=False)
    recorded_by = Column(String(150), nullable=False)
    approved_by = Column(String(150), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StockCount(Base):
    __tablename__ = "fnb_stock_counts"

    id = Column(Integer, primary_key=True, index=True)
    property_code = Column(String(20), index=True, nullable=False)
    ingredient_name = Column(String(150), nullable=False)
    system_qty = Column(Numeric(12, 3), nullable=False)
    physical_qty = Column(Numeric(12, 3), nullable=False)
    variance_qty = Column(Numeric(12, 3), nullable=False)
    unit = Column(String(20), nullable=False)
    variance_value = Column(Numeric(12, 2), nullable=False)
    counted_by = Column(String(150), nullable=False)
    approved_by = Column(String(150), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
