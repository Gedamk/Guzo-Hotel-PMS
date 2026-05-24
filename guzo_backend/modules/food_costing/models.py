from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    property_code = Column(String(20), index=True, nullable=False)
    name = Column(String(150), nullable=False)
    unit = Column(String(20), nullable=False)
    purchase_price = Column(Numeric(10, 2), nullable=False)
    cost_per_unit = Column(Numeric(10, 4), nullable=False)
    supplier_name = Column(String(150), nullable=True)
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
    ingredient_name = Column(String, nullable=False)
    quantity = Column(Numeric(12, 3), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
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
    quantity_received = Column(Numeric(12, 3), nullable=False)
    received_by = Column(String, nullable=False)
    invoice_number = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True)
    property_code = Column(String, nullable=False)
    ingredient_name = Column(String, nullable=False)
    movement_type = Column(String, nullable=False)  # OPENING, PURCHASE_RECEIVED, KITCHEN_ISSUE, WASTAGE, ADJUSTMENT
    quantity = Column(Numeric(12, 3), nullable=False)
    unit = Column(String, nullable=False)
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
    business_date = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
