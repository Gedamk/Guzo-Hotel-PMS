"""Add five-star F&B cost control workflow schema.

Revision ID: 20260602_0020
Revises: 20260602_0019
Create Date: 2026-06-06
"""

from __future__ import annotations

from alembic import op


revision = "20260602_0020"
down_revision = "20260602_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ingredients (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            name VARCHAR(150) NOT NULL,
            category VARCHAR(80),
            unit VARCHAR(20) NOT NULL,
            purchase_price NUMERIC(10, 2) NOT NULL DEFAULT 0,
            cost_per_unit NUMERIC(10, 4) NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS recipes (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            name VARCHAR(150) NOT NULL,
            outlet_name VARCHAR(150),
            selling_price NUMERIC(10, 2) NOT NULL DEFAULT 0,
            total_cost NUMERIC(10, 2) DEFAULT 0,
            food_cost_percentage NUMERIC(10, 2) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            ingredient_name VARCHAR(150),
            quantity NUMERIC(12, 3) DEFAULT 0,
            unit_price NUMERIC(12, 2) DEFAULT 0,
            status VARCHAR(40) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS goods_received (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            purchase_order_id INTEGER,
            ingredient_name VARCHAR(150),
            quantity NUMERIC(12, 3) DEFAULT 0,
            received_by VARCHAR(150),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_movements (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            ingredient_name VARCHAR(150) NOT NULL,
            movement_type VARCHAR(50) NOT NULL,
            quantity NUMERIC(12, 3) NOT NULL,
            unit VARCHAR(20) NOT NULL,
            reference VARCHAR(160),
            notes TEXT,
            created_by VARCHAR(150) NOT NULL DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pos_sales (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            outlet_name VARCHAR(150) NOT NULL,
            menu_item_name VARCHAR(150) NOT NULL,
            quantity_sold NUMERIC(12, 3) NOT NULL,
            selling_price NUMERIC(12, 2) NOT NULL,
            total_revenue NUMERIC(12, 2) NOT NULL,
            business_date VARCHAR(20) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fnb_suppliers (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            supplier_name VARCHAR(150) NOT NULL,
            contact_name VARCHAR(150),
            phone VARCHAR(80),
            email VARCHAR(150),
            tax_id VARCHAR(80),
            payment_terms VARCHAR(120),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_fnb_suppliers_property_code ON fnb_suppliers(property_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_fnb_suppliers_name ON fnb_suppliers(supplier_name)")

    for statement in [
        "ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS category VARCHAR(80)",
        "ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS last_purchase_price NUMERIC(10, 2)",
        "ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS average_cost NUMERIC(10, 4)",
        "ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS supplier_id INTEGER",
        "ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS supplier_name VARCHAR(150)",
        "ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS reorder_level NUMERIC(12, 3)",
        "ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS expiry_date DATE",
        "ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS storage_location VARCHAR(120)",
        "UPDATE ingredients SET last_purchase_price = COALESCE(last_purchase_price, purchase_price)",
        "UPDATE ingredients SET average_cost = COALESCE(average_cost, cost_per_unit)",
        "CREATE INDEX IF NOT EXISTS ix_ingredients_supplier_id ON ingredients(supplier_id)",
        "CREATE INDEX IF NOT EXISTS ix_ingredients_expiry_date ON ingredients(expiry_date)",
        "CREATE INDEX IF NOT EXISTS ix_ingredients_category ON ingredients(category)",
    ]:
        op.execute(statement)

    for statement in [
        "ALTER TABLE recipes ADD COLUMN IF NOT EXISTS target_cost_percentage NUMERIC(10, 2)",
        "ALTER TABLE recipes ADD COLUMN IF NOT EXISTS profit_margin NUMERIC(10, 2)",
        "ALTER TABLE recipes ADD COLUMN IF NOT EXISTS approval_status VARCHAR(40) DEFAULT 'draft'",
    ]:
        op.execute(statement)

    for statement in [
        "ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS supplier_id INTEGER",
        "ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS ordered_qty NUMERIC(12, 3)",
        "ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS received_qty NUMERIC(12, 3)",
        "ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS rejected_qty NUMERIC(12, 3)",
        "ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS unit_cost NUMERIC(12, 2)",
        "ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS invoice_number VARCHAR(120)",
        "ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS received_by VARCHAR(150)",
        "ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS approval_status VARCHAR(40) DEFAULT 'pending'",
        "UPDATE purchase_orders SET ordered_qty = COALESCE(ordered_qty, quantity)",
        "UPDATE purchase_orders SET unit_cost = COALESCE(unit_cost, unit_price)",
        "CREATE INDEX IF NOT EXISTS ix_purchase_orders_supplier_id ON purchase_orders(supplier_id)",
        "CREATE INDEX IF NOT EXISTS ix_purchase_orders_approval_status ON purchase_orders(approval_status)",
    ]:
        op.execute(statement)

    for statement in [
        "ALTER TABLE goods_received ADD COLUMN IF NOT EXISTS ordered_qty NUMERIC(12, 3)",
        "ALTER TABLE goods_received ADD COLUMN IF NOT EXISTS rejected_qty NUMERIC(12, 3)",
        "ALTER TABLE goods_received ADD COLUMN IF NOT EXISTS unit_cost NUMERIC(12, 2)",
        "ALTER TABLE goods_received ADD COLUMN IF NOT EXISTS approval_status VARCHAR(40) DEFAULT 'received'",
    ]:
        op.execute(statement)

    for statement in [
        "ALTER TABLE inventory_movements ADD COLUMN IF NOT EXISTS unit_cost NUMERIC(12, 2)",
        "ALTER TABLE inventory_movements ADD COLUMN IF NOT EXISTS stock_value NUMERIC(12, 2)",
        "CREATE INDEX IF NOT EXISTS ix_inventory_movements_type ON inventory_movements(movement_type)",
        "CREATE INDEX IF NOT EXISTS ix_inventory_movements_property_ingredient ON inventory_movements(property_code, ingredient_name)",
    ]:
        op.execute(statement)

    for statement in [
        "ALTER TABLE pos_sales ADD COLUMN IF NOT EXISTS tax_amount NUMERIC(12, 2)",
        "ALTER TABLE pos_sales ADD COLUMN IF NOT EXISTS service_charge_amount NUMERIC(12, 2)",
        "ALTER TABLE pos_sales ADD COLUMN IF NOT EXISTS payment_method VARCHAR(80)",
        "ALTER TABLE pos_sales ADD COLUMN IF NOT EXISTS room_charge_booking_id INTEGER",
        "ALTER TABLE pos_sales ADD COLUMN IF NOT EXISTS folio_transaction_id INTEGER",
        "CREATE INDEX IF NOT EXISTS ix_pos_sales_room_charge_booking_id ON pos_sales(room_charge_booking_id)",
        "CREATE INDEX IF NOT EXISTS ix_pos_sales_business_date ON pos_sales(business_date)",
    ]:
        op.execute(statement)

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fnb_kitchen_requisitions (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            ingredient_name VARCHAR(150) NOT NULL,
            requested_qty NUMERIC(12, 3) NOT NULL,
            issued_qty NUMERIC(12, 3),
            unit VARCHAR(20) NOT NULL,
            outlet_name VARCHAR(150),
            requested_by VARCHAR(150) NOT NULL,
            issued_by VARCHAR(150),
            status VARCHAR(40) DEFAULT 'requested',
            priority VARCHAR(40) DEFAULT 'normal',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_fnb_kitchen_requisitions_property ON fnb_kitchen_requisitions(property_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_fnb_kitchen_requisitions_status ON fnb_kitchen_requisitions(status)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fnb_wastage_records (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            ingredient_name VARCHAR(150) NOT NULL,
            quantity NUMERIC(12, 3) NOT NULL,
            unit VARCHAR(20) NOT NULL,
            unit_cost NUMERIC(12, 2) NOT NULL,
            cost NUMERIC(12, 2) NOT NULL,
            reason TEXT NOT NULL,
            recorded_by VARCHAR(150) NOT NULL,
            approved_by VARCHAR(150),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_fnb_wastage_property ON fnb_wastage_records(property_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_fnb_wastage_ingredient ON fnb_wastage_records(ingredient_name)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fnb_stock_counts (
            id SERIAL PRIMARY KEY,
            property_code VARCHAR(20) NOT NULL,
            ingredient_name VARCHAR(150) NOT NULL,
            system_qty NUMERIC(12, 3) NOT NULL,
            physical_qty NUMERIC(12, 3) NOT NULL,
            variance_qty NUMERIC(12, 3) NOT NULL,
            unit VARCHAR(20) NOT NULL,
            variance_value NUMERIC(12, 2) NOT NULL,
            counted_by VARCHAR(150) NOT NULL,
            approved_by VARCHAR(150),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_fnb_stock_counts_property ON fnb_stock_counts(property_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_fnb_stock_counts_ingredient ON fnb_stock_counts(ingredient_name)")

    for role_key in ["general_manager", "admin", "fb_controller"]:
        for permission_key in [
            "fnb.create_purchase_order",
            "fnb.receive_goods",
            "fnb.issue_stock",
            "fnb.manage_recipes",
            "fnb.record_waste",
            "fnb.stock_count",
            "fnb.post_room_charge",
            "fnb.view_reports",
        ]:
            op.execute(
                f"""
                INSERT INTO pms_role_permissions(role_key, permission_key, allowed)
                VALUES ('{role_key}', '{permission_key}', TRUE)
                ON CONFLICT (role_key, permission_key) DO NOTHING
                """
            )
    for role_key, permission_key in [
        ("finance_cashier", "fnb.post_room_charge"),
        ("finance_cashier", "fnb.view_reports"),
        ("read_only_owner", "fnb.view_reports"),
    ]:
        op.execute(
            f"""
            INSERT INTO pms_role_permissions(role_key, permission_key, allowed)
            VALUES ('{role_key}', '{permission_key}', TRUE)
            ON CONFLICT (role_key, permission_key) DO NOTHING
            """
        )

    op.execute(
        """
        INSERT INTO pms_roles(role_key, role_name, description, is_system_role)
        VALUES ('fb_controller', 'F&B Controller', 'Food and beverage cost control and revenue posting review.', TRUE)
        ON CONFLICT (role_key) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO pms_users(full_name, email, role_key, property_code, is_active)
        VALUES ('F&B Controller', 'fnb@guzo.local', 'fb_controller', 'DRE001', TRUE)
        ON CONFLICT (email) DO NOTHING
        """
    )


def downgrade() -> None:
    pass
