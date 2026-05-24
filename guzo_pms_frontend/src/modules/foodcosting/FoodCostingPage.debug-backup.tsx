import { useEffect, useMemo, useState } from "react";
import { API_BASE_URL, DEFAULT_PROPERTY_CODE } from "../../config/pms";

type Ingredient = {
  id: number;
  name: string;
  unit: string;
  cost_per_unit: string;
  supplier_name?: string | null;
};

type Recipe = {
  id: number;
  name: string;
  outlet_name?: string | null;
  selling_price: string;
  total_cost: string;
  food_cost_percentage: string;
};

type Alert = {
  id: number;
  alert_type: string;
  message: string;
  severity: string;
};

type PurchaseOrder = {
  id: number;
  supplier_name: string;
  ingredient_name: string;
  quantity: number;
  unit_price: number;
  total_amount: number;
  status: string;
};

type GoodsReceived = {
  id: number;
  purchase_order_id: number;
  supplier_name: string;
  ingredient_name: string;
  quantity_received: number;
  received_by: string;
  invoice_number?: string;
};

type InventoryMovement = {
  id: number;
  ingredient_name: string;
  movement_type: string;
  quantity: number;
  unit: string;
  reference?: string | null;
  notes?: string | null;
  created_by: string;
};

type PosSale = {
  id: number;
  outlet_name: string;
  menu_item_name: string;
  quantity_sold: number;
  selling_price: number;
  total_revenue: number;
  business_date: string;
};

export default function FoodCostingPage() {
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [goodsReceived, setGoodsReceived] = useState<GoodsReceived[]>([]);
  const [inventoryMovements, setInventoryMovements] = useState<InventoryMovement[]>([]);
  const [posSales, setPosSales] = useState<PosSale[]>([]);
  const [loading, setLoading] = useState(false);

  const [newPo, setNewPo] = useState({
    supplier_name: "",
    ingredient_name: "",
    quantity: "",
    unit_price: "",
  });

  const [newGrn, setNewGrn] = useState({
    purchase_order_id: "",
    supplier_name: "",
    ingredient_name: "",
    quantity_received: "",
    received_by: "",
    invoice_number: "",
  });

  const [newMovement, setNewMovement] = useState({
    ingredient_name: "",
    movement_type: "KITCHEN_ISSUE",
    quantity: "",
    unit: "kg",
    reference: "",
    notes: "",
    created_by: "Store Controller",
  });

  const [newSale, setNewSale] = useState({
    outlet_name: "Main Restaurant",
    menu_item_name: "",
    quantity_sold: "",
    selling_price: "",
    business_date: "2026-04-06",
  });

  async function loadData() {
    setLoading(true);

    async function getJson(path: string) {
      const res = await fetch(`${API_BASE_URL}${path}`);
      if (!res.ok) {
        console.error("API failed:", path, res.status);
        return [];
      }
      return res.json();
    }

    try {
      const ingredientsData = await getJson(`/food-costing/ingredients?property_code=${DEFAULT_PROPERTY_CODE}`);
      const recipesData = await getJson(`/food-costing/recipes?property_code=${DEFAULT_PROPERTY_CODE}`);
      const alertsData = await getJson(`/food-costing/alerts?property_code=${DEFAULT_PROPERTY_CODE}`);
      const poData = await getJson(`/food-costing/purchase-orders?property_code=${DEFAULT_PROPERTY_CODE}`);
      const grnData = await getJson(`/food-costing/goods-received?property_code=${DEFAULT_PROPERTY_CODE}`);
      const movementData = await getJson(`/food-costing/inventory-movements?property_code=${DEFAULT_PROPERTY_CODE}`);
      const salesData = await getJson(`/food-costing/pos-sales?property_code=${DEFAULT_PROPERTY_CODE}`);

      setIngredients(ingredientsData);
      setRecipes(recipesData);
      setAlerts(alertsData);
      setPurchaseOrders(poData);
      setGoodsReceived(grnData);
      setInventoryMovements(movementData);
      setPosSales(salesData);

      console.log("F&B loaded:", {
        ingredients: ingredientsData.length,
        recipes: recipesData.length,
        purchaseOrders: poData.length,
        movements: movementData.length,
        posSales: salesData.length,
      });
    } finally {
      setLoading(false);
    }
  }

  async function createPurchaseOrder(event: React.FormEvent) {
    event.preventDefault();

    await fetch(`${API_BASE_URL}/food-costing/purchase-orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        property_code: DEFAULT_PROPERTY_CODE,
        supplier_name: newPo.supplier_name,
        ingredient_name: newPo.ingredient_name,
        quantity: Number(newPo.quantity),
        unit_price: Number(newPo.unit_price),
      }),
    });

    setNewPo({ supplier_name: "", ingredient_name: "", quantity: "", unit_price: "" });
    loadData();
  }

  async function createGoodsReceived(event: React.FormEvent) {
    event.preventDefault();

    const selectedPo = purchaseOrders.find((po) => String(po.id) === newGrn.purchase_order_id);

    await fetch(`${API_BASE_URL}/food-costing/goods-received`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        property_code: DEFAULT_PROPERTY_CODE,
        purchase_order_id: Number(newGrn.purchase_order_id),
        supplier_name: newGrn.supplier_name || selectedPo?.supplier_name || "",
        ingredient_name: newGrn.ingredient_name || selectedPo?.ingredient_name || "",
        quantity_received: Number(newGrn.quantity_received),
        received_by: newGrn.received_by,
        invoice_number: newGrn.invoice_number || null,
      }),
    });

    setNewGrn({
      purchase_order_id: "",
      supplier_name: "",
      ingredient_name: "",
      quantity_received: "",
      received_by: "",
      invoice_number: "",
    });

    loadData();
  }

  async function createPosSale(event: React.FormEvent) {
    event.preventDefault();

    await fetch(`${API_BASE_URL}/food-costing/pos-sales`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        property_code: DEFAULT_PROPERTY_CODE,
        outlet_name: newSale.outlet_name,
        menu_item_name: newSale.menu_item_name,
        quantity_sold: Number(newSale.quantity_sold),
        selling_price: Number(newSale.selling_price),
        business_date: newSale.business_date,
      }),
    });

    setNewSale({
      outlet_name: "Main Restaurant",
      menu_item_name: "",
      quantity_sold: "",
      selling_price: "",
      business_date: "2026-04-06",
    });

    loadData();
  }

  async function createInventoryMovement(event: React.FormEvent) {
    event.preventDefault();

    await fetch(`${API_BASE_URL}/food-costing/inventory-movements`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        property_code: DEFAULT_PROPERTY_CODE,
        ingredient_name: newMovement.ingredient_name,
        movement_type: newMovement.movement_type,
        quantity: Number(newMovement.quantity),
        unit: newMovement.unit,
        reference: newMovement.reference || null,
        notes: newMovement.notes || null,
        created_by: newMovement.created_by,
      }),
    });

    setNewMovement({
      ingredient_name: "",
      movement_type: "KITCHEN_ISSUE",
      quantity: "",
      unit: "kg",
      reference: "",
      notes: "",
      created_by: "Store Controller",
    });

    loadData();
  }

  useEffect(() => {
    loadData();
  }, []);

  const avgFoodCost = useMemo(() => {
    if (!recipes.length) return 0;
    return recipes.reduce((sum, r) => sum + Number(r.food_cost_percentage || 0), 0) / recipes.length;
  }, [recipes]);

  const wastageSummary = useMemo(() => {
    return inventoryMovements
      .filter((movement) => movement.movement_type === "WASTAGE")
      .map((movement) => {
        const ingredient = ingredients.find((item) => item.name === movement.ingredient_name);
        const costPerUnit = Number(ingredient?.cost_per_unit || 0);
        const quantity = Number(movement.quantity || 0);

        return {
          id: movement.id,
          ingredient: movement.ingredient_name,
          quantity,
          unit: movement.unit,
          costPerUnit,
          totalCost: quantity * costPerUnit,
          reference: movement.reference || "No reference",
          createdBy: movement.created_by,
          notes: movement.notes || "",
        };
      });
  }, [inventoryMovements, ingredients]);

  const totalWastageCost = useMemo(() => {
    return wastageSummary.reduce((sum, item) => sum + item.totalCost, 0);
  }, [wastageSummary]);

  const totalPosRevenue = useMemo(() => {
    return posSales.reduce((sum, sale) => sum + Number(sale.total_revenue || 0), 0);
  }, [posSales]);

  const posProfitSummary = useMemo(() => {
    return posSales.map((sale) => {
      const recipe = recipes.find(
        (item) => item.name.toLowerCase() === sale.menu_item_name.toLowerCase()
      );

      const recipeCost = Number(recipe?.total_cost || 0);
      const expectedCost = recipeCost * Number(sale.quantity_sold || 0);
      const revenue = Number(sale.total_revenue || 0);
      const grossProfit = revenue - expectedCost;
      const foodCostPercent = revenue > 0 ? (expectedCost / revenue) * 100 : 0;

      return {
        id: sale.id,
        menuItem: sale.menu_item_name,
        outlet: sale.outlet_name,
        quantitySold: Number(sale.quantity_sold || 0),
        revenue,
        expectedCost,
        grossProfit,
        foodCostPercent,
        businessDate: sale.business_date,
      };
    });
  }, [posSales, recipes]);

  const stockBalances = useMemo(() => {
    const balances: Record<string, { ingredient: string; received: number; issued: number; wastage: number; adjustment: number; closing: number; unit: string }> = {};

    inventoryMovements.forEach((movement) => {
      const name = movement.ingredient_name;
      if (!balances[name]) {
        balances[name] = {
          ingredient: name,
          received: 0,
          issued: 0,
          wastage: 0,
          adjustment: 0,
          closing: 0,
          unit: movement.unit,
        };
      }

      const qty = Number(movement.quantity || 0);

      if (movement.movement_type === "OPENING" || movement.movement_type === "PURCHASE_RECEIVED") {
        balances[name].received += qty;
      } else if (movement.movement_type === "KITCHEN_ISSUE") {
        balances[name].issued += qty;
      } else if (movement.movement_type === "WASTAGE") {
        balances[name].wastage += qty;
      } else if (movement.movement_type === "ADJUSTMENT") {
        balances[name].adjustment += qty;
      }

      balances[name].closing =
        balances[name].received +
        balances[name].adjustment -
        balances[name].issued -
        balances[name].wastage;
    });

    return Object.values(balances);
  }, [inventoryMovements]);

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border bg-white p-6 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-wide text-amber-700">
          Guzo F&B Cost Control AI
        </p>
        <h1 className="mt-2 text-3xl font-bold text-slate-900">
          Food & Beverage Cost Control
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Recipe costing, inventory control, purchasing, goods receiving, POS analysis, finance reporting, and AI food-cost alerts.
        </p>
        <button onClick={loadData} className="mt-4 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white">
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </section>

      <section className="grid gap-4 md:grid-cols-5">
        <div className="rounded-2xl border bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Ingredients</p>
          <p className="mt-2 text-3xl font-bold">{ingredients.length}</p>
        </div>
        <div className="rounded-2xl border bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Recipes</p>
          <p className="mt-2 text-3xl font-bold">{recipes.length}</p>
        </div>
        <div className="rounded-2xl border bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Avg Food Cost</p>
          <p className="mt-2 text-3xl font-bold">{avgFoodCost.toFixed(2)}%</p>
        </div>
        <div className="rounded-2xl border bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Purchase Orders</p>
          <p className="mt-2 text-3xl font-bold">{purchaseOrders.length}</p>
        </div>
        <div className="rounded-2xl border bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">POS Revenue</p>
          <p className="mt-2 text-3xl font-bold">${totalPosRevenue.toFixed(0)}</p>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-bold">Create Purchase Order</h2>
          <form onSubmit={createPurchaseOrder} className="mt-4 grid gap-3 md:grid-cols-2">
            <input className="rounded-xl border px-3 py-2 text-sm" placeholder="Supplier name" value={newPo.supplier_name} onChange={(e) => setNewPo({ ...newPo, supplier_name: e.target.value })} required />
            <input className="rounded-xl border px-3 py-2 text-sm" placeholder="Ingredient name" value={newPo.ingredient_name} onChange={(e) => setNewPo({ ...newPo, ingredient_name: e.target.value })} required />
            <input className="rounded-xl border px-3 py-2 text-sm" type="number" step="0.001" placeholder="Quantity" value={newPo.quantity} onChange={(e) => setNewPo({ ...newPo, quantity: e.target.value })} required />
            <input className="rounded-xl border px-3 py-2 text-sm" type="number" step="0.01" placeholder="Unit price" value={newPo.unit_price} onChange={(e) => setNewPo({ ...newPo, unit_price: e.target.value })} required />
            <button className="rounded-xl bg-amber-700 px-4 py-2 text-sm font-semibold text-white md:col-span-2">
              Save Purchase Order
            </button>
          </form>
        </div>

        <div className="rounded-2xl border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-bold">Goods Receiving</h2>
          <form onSubmit={createGoodsReceived} className="mt-4 grid gap-3 md:grid-cols-2">
            <select className="rounded-xl border px-3 py-2 text-sm" value={newGrn.purchase_order_id} onChange={(e) => setNewGrn({ ...newGrn, purchase_order_id: e.target.value })} required>
              <option value="">Select purchase order</option>
              {purchaseOrders.map((po) => (
                <option key={po.id} value={po.id}>
                  PO #{po.id} - {po.ingredient_name} - {po.status}
                </option>
              ))}
            </select>
            <input className="rounded-xl border px-3 py-2 text-sm" type="number" step="0.001" placeholder="Quantity received" value={newGrn.quantity_received} onChange={(e) => setNewGrn({ ...newGrn, quantity_received: e.target.value })} required />
            <input className="rounded-xl border px-3 py-2 text-sm" placeholder="Received by" value={newGrn.received_by} onChange={(e) => setNewGrn({ ...newGrn, received_by: e.target.value })} required />
            <input className="rounded-xl border px-3 py-2 text-sm" placeholder="Invoice number" value={newGrn.invoice_number} onChange={(e) => setNewGrn({ ...newGrn, invoice_number: e.target.value })} />
            <button className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white md:col-span-2">
              Receive Goods
            </button>
          </form>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-bold">Purchase Orders</h2>
          <div className="mt-4 space-y-2">
            {purchaseOrders.map((po) => (
              <div key={po.id} className="rounded-xl border p-3 text-sm">
                <div className="flex justify-between">
                  <span className="font-semibold">PO #{po.id} — {po.ingredient_name}</span>
                  <span>{po.status}</span>
                </div>
                <div className="text-xs text-slate-500">
                  {po.supplier_name} | Qty {po.quantity} | Unit ${Number(po.unit_price).toFixed(2)} | Total ${Number(po.total_amount).toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-bold">Goods Received</h2>
          <div className="mt-4 space-y-2">
            {goodsReceived.map((grn) => (
              <div key={grn.id} className="rounded-xl border p-3 text-sm">
                <div className="font-semibold">GRN #{grn.id} — {grn.ingredient_name}</div>
                <div className="text-xs text-slate-500">
                  PO #{grn.purchase_order_id} | Qty {grn.quantity_received} | Invoice {grn.invoice_number || "—"} | Received by {grn.received_by}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-bold">Inventory Movement</h2>
          <p className="mt-1 text-sm text-slate-500">
            Record kitchen issues, wastage, purchase received, and stock adjustments.
          </p>

          <form onSubmit={createInventoryMovement} className="mt-4 grid gap-3 md:grid-cols-2">
            <select
              className="rounded-xl border px-3 py-2 text-sm"
              value={newMovement.ingredient_name}
              onChange={(e) => setNewMovement({ ...newMovement, ingredient_name: e.target.value })}
              required
            >
              <option value="">Select ingredient</option>
              {ingredients.map((item) => (
                <option key={item.id} value={item.name}>
                  {item.name}
                </option>
              ))}
            </select>

            <select
              className="rounded-xl border px-3 py-2 text-sm"
              value={newMovement.movement_type}
              onChange={(e) => setNewMovement({ ...newMovement, movement_type: e.target.value })}
              required
            >
              <option value="KITCHEN_ISSUE">Kitchen Issue</option>
              <option value="WASTAGE">Wastage</option>
              <option value="PURCHASE_RECEIVED">Purchase Received</option>
              <option value="ADJUSTMENT">Adjustment</option>
              <option value="OPENING">Opening Stock</option>
            </select>

            <input
              className="rounded-xl border px-3 py-2 text-sm"
              type="number"
              step="0.001"
              placeholder="Quantity"
              value={newMovement.quantity}
              onChange={(e) => setNewMovement({ ...newMovement, quantity: e.target.value })}
              required
            />

            <input
              className="rounded-xl border px-3 py-2 text-sm"
              placeholder="Unit"
              value={newMovement.unit}
              onChange={(e) => setNewMovement({ ...newMovement, unit: e.target.value })}
              required
            />

            <input
              className="rounded-xl border px-3 py-2 text-sm"
              placeholder="Reference"
              value={newMovement.reference}
              onChange={(e) => setNewMovement({ ...newMovement, reference: e.target.value })}
            />

            <input
              className="rounded-xl border px-3 py-2 text-sm"
              placeholder="Created by"
              value={newMovement.created_by}
              onChange={(e) => setNewMovement({ ...newMovement, created_by: e.target.value })}
              required
            />

            <input
              className="rounded-xl border px-3 py-2 text-sm md:col-span-2"
              placeholder="Notes"
              value={newMovement.notes}
              onChange={(e) => setNewMovement({ ...newMovement, notes: e.target.value })}
            />

            <button className="rounded-xl bg-emerald-700 px-4 py-2 text-sm font-semibold text-white md:col-span-2">
              Save Inventory Movement
            </button>
          </form>
        </div>

        <div className="rounded-2xl border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-bold">Stock Movement History</h2>
          <div className="mt-4 space-y-2">
            {inventoryMovements.map((movement) => (
              <div key={movement.id} className="rounded-xl border p-3 text-sm">
                <div className="flex justify-between">
                  <span className="font-semibold">
                    {movement.ingredient_name} — {movement.movement_type}
                  </span>
                  <span>{movement.quantity} {movement.unit}</span>
                </div>
                <div className="text-xs text-slate-500">
                  {movement.reference || "No reference"} | {movement.created_by}
                </div>
                {movement.notes ? (
                  <div className="text-xs text-slate-500">{movement.notes}</div>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-bold">POS Sales Entry</h2>
          <p className="mt-1 text-sm text-slate-500">
            Record sold menu items from restaurant POS to compare revenue with recipe cost.
          </p>

          <form onSubmit={createPosSale} className="mt-4 grid gap-3 md:grid-cols-2">
            <input
              className="rounded-xl border px-3 py-2 text-sm"
              placeholder="Outlet name"
              value={newSale.outlet_name}
              onChange={(e) => setNewSale({ ...newSale, outlet_name: e.target.value })}
              required
            />

            <div className="space-y-2">
              <select
                className="w-full rounded-xl border px-3 py-2 text-sm"
                value={newSale.menu_item_name}
                onChange={(e) => {
                  const recipe = recipes.find((item) => item.name === e.target.value);
                  setNewSale({
                    ...newSale,
                    menu_item_name: e.target.value,
                    selling_price: recipe ? String(recipe.selling_price) : newSale.selling_price,
                  });
                }}
              >
                <option value="">Select recipe/menu item</option>
                {recipes.map((recipe) => (
                  <option key={recipe.id} value={recipe.name}>
                    {recipe.name}
                  </option>
                ))}
              </select>

              <input
                className="w-full rounded-xl border px-3 py-2 text-sm"
                placeholder="Or type new menu item name"
                value={newSale.menu_item_name}
                onChange={(e) => setNewSale({ ...newSale, menu_item_name: e.target.value })}
                required
              />
            </div>

            <input
              className="rounded-xl border px-3 py-2 text-sm"
              type="number"
              step="0.001"
              placeholder="Quantity sold"
              value={newSale.quantity_sold}
              onChange={(e) => setNewSale({ ...newSale, quantity_sold: e.target.value })}
              required
            />

            <input
              className="rounded-xl border px-3 py-2 text-sm"
              type="number"
              step="0.01"
              placeholder="Selling price"
              value={newSale.selling_price}
              onChange={(e) => setNewSale({ ...newSale, selling_price: e.target.value })}
              required
            />

            <input
              className="rounded-xl border px-3 py-2 text-sm md:col-span-2"
              type="date"
              value={newSale.business_date}
              onChange={(e) => setNewSale({ ...newSale, business_date: e.target.value })}
              required
            />

            <button className="rounded-xl bg-indigo-700 px-4 py-2 text-sm font-semibold text-white md:col-span-2">
              Save POS Sale
            </button>
          </form>
        </div>

        <div className="rounded-2xl border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-bold">POS Profitability Summary</h2>
          <div className="mt-4 space-y-2">
            {posProfitSummary.length ? (
              posProfitSummary.map((sale) => (
                <div key={sale.id} className="rounded-xl border p-3 text-sm">
                  <div className="flex justify-between">
                    <span className="font-semibold">{sale.menuItem}</span>
                    <span>{sale.quantitySold} sold</span>
                  </div>
                  <div className="text-xs text-slate-500">
                    Revenue ${sale.revenue.toFixed(2)} | Expected Cost ${sale.expectedCost.toFixed(2)} | Gross Profit ${sale.grossProfit.toFixed(2)} | Food Cost {sale.foodCostPercent.toFixed(2)}%
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No POS sales recorded yet.</p>
            )}
          </div>
        </div>
      </section>

      <section className="rounded-2xl border bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold">Wastage Cost Summary</h2>
            <p className="mt-1 text-sm text-slate-500">
              Tracks food loss by multiplying wastage quantity by ingredient cost per unit.
            </p>
          </div>
          <div className="rounded-xl bg-red-50 px-4 py-3 text-right">
            <p className="text-xs font-semibold uppercase text-red-700">Total Wastage Cost</p>
            <p className="text-2xl font-bold text-red-800">${totalWastageCost.toFixed(2)}</p>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b text-slate-500">
                <th className="py-2">Ingredient</th>
                <th className="py-2">Quantity</th>
                <th className="py-2">Cost/Unit</th>
                <th className="py-2">Wastage Cost</th>
                <th className="py-2">Reference</th>
                <th className="py-2">Created By</th>
              </tr>
            </thead>
            <tbody>
              {wastageSummary.length ? (
                wastageSummary.map((item) => (
                  <tr key={item.id} className="border-b">
                    <td className="py-2 font-semibold">{item.ingredient}</td>
                    <td className="py-2">{item.quantity.toFixed(3)} {item.unit}</td>
                    <td className="py-2">${item.costPerUnit.toFixed(2)}</td>
                    <td className="py-2 font-bold text-red-700">${item.totalCost.toFixed(2)}</td>
                    <td className="py-2">{item.reference}</td>
                    <td className="py-2">{item.createdBy}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="py-3 text-slate-500" colSpan={6}>
                    No wastage movements recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-xl font-bold">Stock Balance Summary</h2>
        <p className="mt-1 text-sm text-slate-500">
          Closing Stock = Opening/Purchase Received + Adjustment - Kitchen Issue - Wastage
        </p>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b text-slate-500">
                <th className="py-2">Ingredient</th>
                <th className="py-2">Received/Open</th>
                <th className="py-2">Kitchen Issue</th>
                <th className="py-2">Wastage</th>
                <th className="py-2">Adjustment</th>
                <th className="py-2">Closing Stock</th>
              </tr>
            </thead>
            <tbody>
              {stockBalances.length ? (
                stockBalances.map((row) => (
                  <tr key={row.ingredient} className="border-b">
                    <td className="py-2 font-semibold">{row.ingredient}</td>
                    <td className="py-2">{row.received.toFixed(3)} {row.unit}</td>
                    <td className="py-2">{row.issued.toFixed(3)} {row.unit}</td>
                    <td className="py-2">{row.wastage.toFixed(3)} {row.unit}</td>
                    <td className="py-2">{row.adjustment.toFixed(3)} {row.unit}</td>
                    <td className="py-2 font-bold">{row.closing.toFixed(3)} {row.unit}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="py-3 text-slate-500" colSpan={6}>
                    No stock movements yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-bold">Ingredient Inventory</h2>
          <div className="mt-4 space-y-2">
            {ingredients.map((item) => (
              <div key={item.id} className="rounded-xl border p-3 text-sm">
                <span className="font-semibold">{item.name}</span> — {item.unit} — ${Number(item.cost_per_unit).toFixed(2)}
                <div className="text-xs text-slate-500">{item.supplier_name || "No supplier"}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-bold">Recipe Costing</h2>
          <div className="mt-4 space-y-2">
            {recipes.map((recipe) => (
              <div key={recipe.id} className="rounded-xl border p-3 text-sm">
                <div className="flex justify-between">
                  <span className="font-semibold">{recipe.name}</span>
                  <span>{Number(recipe.food_cost_percentage).toFixed(2)}%</span>
                </div>
                <div className="text-xs text-slate-500">
                  Selling ${Number(recipe.selling_price).toFixed(2)} | Cost ${Number(recipe.total_cost).toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-xl font-bold">AI Food Cost Alerts</h2>
        <div className="mt-4 space-y-2">
          {alerts.map((alert) => (
            <div key={alert.id} className="rounded-xl border border-red-200 bg-red-50 p-4">
              <p className="font-bold text-red-800">{alert.alert_type}</p>
              <p className="text-sm text-red-700">{alert.message}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
