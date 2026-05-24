import { useEffect, useMemo, useState } from "react";
import { API_BASE_URL, DEFAULT_PROPERTY_CODE } from "../../config/pms";

type Ingredient = { id: number; name: string; unit: string; cost_per_unit: string | number; supplier_name?: string | null };
type Recipe = { id: number; name: string; selling_price: string | number; total_cost: string | number; food_cost_percentage: string | number };
type Alert = { id: number; alert_type: string; message: string; severity: string };
type PurchaseOrder = { id: number; supplier_name: string; ingredient_name: string; quantity: number; unit_price: number; total_amount: number; status: string };
type GoodsReceived = { id: number; purchase_order_id: number; supplier_name: string; ingredient_name: string; quantity_received: number; received_by: string; invoice_number?: string | null };
type InventoryMovement = { id: number; ingredient_name: string; movement_type: string; quantity: number; unit: string; reference?: string | null; notes?: string | null; created_by: string };
type PosSale = { id: number; outlet_name: string; menu_item_name: string; quantity_sold: number; selling_price: number; total_revenue: number; business_date: string };

export default function FoodCostingPage() {
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [goodsReceived, setGoodsReceived] = useState<GoodsReceived[]>([]);
  const [inventoryMovements, setInventoryMovements] = useState<InventoryMovement[]>([]);
  const [posSales, setPosSales] = useState<PosSale[]>([]);
  const [loading, setLoading] = useState(false);
  const [reportMode, setReportMode] = useState(false);

  const [newPo, setNewPo] = useState({ supplier_name: "", ingredient_name: "", quantity: "", unit_price: "" });
  const [newGrn, setNewGrn] = useState({ purchase_order_id: "", quantity_received: "", received_by: "", invoice_number: "" });
  const [newMovement, setNewMovement] = useState({ ingredient_name: "", movement_type: "KITCHEN_ISSUE", quantity: "", unit: "kg", reference: "", notes: "", created_by: "Store Controller" });
  const [newSale, setNewSale] = useState({ outlet_name: "Main Restaurant", menu_item_name: "", quantity_sold: "", selling_price: "", business_date: "2026-04-06" });

  async function getJson(path: string) {
    const res = await fetch(`${API_BASE_URL}${path}`);
    if (!res.ok) return [];
    return res.json();
  }

  async function loadData() {
    setLoading(true);
    try {
      const [i, r, a, po, grn, mov, sales] = await Promise.all([
        getJson(`/food-costing/ingredients?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/recipes?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/alerts?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/purchase-orders?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/goods-received?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/inventory-movements?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/pos-sales?property_code=${DEFAULT_PROPERTY_CODE}`),
      ]);

      setIngredients(Array.isArray(i) ? i : []);
      setRecipes(Array.isArray(r) ? r : []);
      setAlerts(Array.isArray(a) ? a : []);
      setPurchaseOrders(Array.isArray(po) ? po : []);
      setGoodsReceived(Array.isArray(grn) ? grn : []);
      setInventoryMovements(Array.isArray(mov) ? mov : []);
      setPosSales(Array.isArray(sales) ? sales : []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function createPurchaseOrder(e: React.FormEvent) {
    e.preventDefault();
    await fetch(`${API_BASE_URL}/food-costing/purchase-orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ property_code: DEFAULT_PROPERTY_CODE, ...newPo, quantity: Number(newPo.quantity), unit_price: Number(newPo.unit_price) }),
    });
    setNewPo({ supplier_name: "", ingredient_name: "", quantity: "", unit_price: "" });
    loadData();
  }

  async function createGoodsReceived(e: React.FormEvent) {
    e.preventDefault();
    const po = purchaseOrders.find((item) => String(item.id) === newGrn.purchase_order_id);
    await fetch(`${API_BASE_URL}/food-costing/goods-received`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        property_code: DEFAULT_PROPERTY_CODE,
        purchase_order_id: Number(newGrn.purchase_order_id),
        supplier_name: po?.supplier_name || "",
        ingredient_name: po?.ingredient_name || "",
        quantity_received: Number(newGrn.quantity_received),
        received_by: newGrn.received_by,
        invoice_number: newGrn.invoice_number || null,
      }),
    });
    setNewGrn({ purchase_order_id: "", quantity_received: "", received_by: "", invoice_number: "" });
    loadData();
  }

  async function createInventoryMovement(e: React.FormEvent) {
    e.preventDefault();
    await fetch(`${API_BASE_URL}/food-costing/inventory-movements`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ property_code: DEFAULT_PROPERTY_CODE, ...newMovement, quantity: Number(newMovement.quantity) }),
    });
    setNewMovement({ ingredient_name: "", movement_type: "KITCHEN_ISSUE", quantity: "", unit: "kg", reference: "", notes: "", created_by: "Store Controller" });
    loadData();
  }

  async function createPosSale(e: React.FormEvent) {
    e.preventDefault();
    await fetch(`${API_BASE_URL}/food-costing/pos-sales`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ property_code: DEFAULT_PROPERTY_CODE, ...newSale, quantity_sold: Number(newSale.quantity_sold), selling_price: Number(newSale.selling_price) }),
    });
    setNewSale({ outlet_name: "Main Restaurant", menu_item_name: "", quantity_sold: "", selling_price: "", business_date: "2026-04-06" });
    loadData();
  }

  const avgFoodCost = useMemo(() => recipes.length ? recipes.reduce((s, r) => s + Number(r.food_cost_percentage || 0), 0) / recipes.length : 0, [recipes]);
  const totalPosRevenue = useMemo(() => posSales.reduce((s, x) => s + Number(x.total_revenue || 0), 0), [posSales]);

  const posProfitSummary = useMemo(() => posSales.map((sale) => {
    const recipe = recipes.find((r) => r.name.toLowerCase() === sale.menu_item_name.toLowerCase());
    const expectedCost = Number(recipe?.total_cost || 0) * Number(sale.quantity_sold || 0);
    const revenue = Number(sale.total_revenue || 0);
    return { id: sale.id, menuItem: sale.menu_item_name, quantitySold: Number(sale.quantity_sold || 0), revenue, expectedCost, grossProfit: revenue - expectedCost, foodCostPercent: revenue ? (expectedCost / revenue) * 100 : 0 };
  }), [posSales, recipes]);

  const wastageSummary = useMemo(() => inventoryMovements.filter((m) => m.movement_type === "WASTAGE").map((m) => {
    const ing = ingredients.find((i) => i.name === m.ingredient_name);
    const costPerUnit = Number(ing?.cost_per_unit || 0);
    const quantity = Number(m.quantity || 0);
    return { id: m.id, ingredient: m.ingredient_name, quantity, unit: m.unit, costPerUnit, totalCost: quantity * costPerUnit, reference: m.reference || "No reference", createdBy: m.created_by };
  }), [inventoryMovements, ingredients]);

  const totalWastageCost = useMemo(() => wastageSummary.reduce((s, x) => s + x.totalCost, 0), [wastageSummary]);

  const stockBalances = useMemo(() => {
    const b: Record<string, { ingredient: string; received: number; issued: number; wastage: number; adjustment: number; closing: number; unit: string }> = {};
    inventoryMovements.forEach((m) => {
      if (!b[m.ingredient_name]) b[m.ingredient_name] = { ingredient: m.ingredient_name, received: 0, issued: 0, wastage: 0, adjustment: 0, closing: 0, unit: m.unit };
      const q = Number(m.quantity || 0);
      if (m.movement_type === "OPENING" || m.movement_type === "PURCHASE_RECEIVED") b[m.ingredient_name].received += q;
      if (m.movement_type === "KITCHEN_ISSUE") b[m.ingredient_name].issued += q;
      if (m.movement_type === "WASTAGE") b[m.ingredient_name].wastage += q;
      if (m.movement_type === "ADJUSTMENT") b[m.ingredient_name].adjustment += q;
      b[m.ingredient_name].closing = b[m.ingredient_name].received + b[m.ingredient_name].adjustment - b[m.ingredient_name].issued - b[m.ingredient_name].wastage;
    });
    return Object.values(b);
  }, [inventoryMovements]);

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border bg-white p-6 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-wide text-amber-700">Guzo F&B Cost Control AI</p>
        <h1 className="mt-2 text-3xl font-bold text-slate-900">Food & Beverage Cost Control</h1>
        <p className="mt-2 text-sm text-slate-600">Recipe costing, inventory control, purchasing, goods receiving, POS analysis, finance reporting, and AI food-cost alerts.</p>
        <div className="mt-4 flex flex-wrap items-center gap-6">
          <button onClick={loadData} className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white">{loading ? "Refreshing..." : "Refresh"}</button>
          <button onClick={() => setReportMode(!reportMode)} className="rounded-xl bg-blue-700 px-4 py-2 text-sm font-semibold text-white">{reportMode ? "Show Entry Forms" : "Manager Report View"}</button>
          <button onClick={() => window.print()} className="rounded-xl bg-amber-700 px-4 py-2 text-sm font-semibold text-white">Print Executive Report</button>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-5">
        <div className="rounded-2xl border bg-white p-5"><p>Ingredients</p><h2>{ingredients.length}</h2></div>
        <div className="rounded-2xl border bg-white p-5"><p>Recipes</p><h2>{recipes.length}</h2></div>
        <div className="rounded-2xl border bg-white p-5"><p>Avg Food Cost</p><h2>{avgFoodCost.toFixed(2)}%</h2></div>
        <div className="rounded-2xl border bg-white p-5"><p>Purchase Orders</p><h2>{purchaseOrders.length}</h2></div>
        <div className="rounded-2xl border bg-white p-5"><p>POS Revenue</p><h2>${totalPosRevenue.toFixed(0)}</h2></div>
      </section>

      {!reportMode && (
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border bg-white p-5">
            <h2 className="text-xl font-bold">Create Purchase Order</h2>
            <form onSubmit={createPurchaseOrder} className="mt-4 grid gap-3 md:grid-cols-2">
              <input className="rounded-xl border px-3 py-2" placeholder="Supplier name" value={newPo.supplier_name} onChange={(e) => setNewPo({ ...newPo, supplier_name: e.target.value })} required />
              <input className="rounded-xl border px-3 py-2" placeholder="Ingredient name" value={newPo.ingredient_name} onChange={(e) => setNewPo({ ...newPo, ingredient_name: e.target.value })} required />
              <input className="rounded-xl border px-3 py-2" type="number" placeholder="Quantity" value={newPo.quantity} onChange={(e) => setNewPo({ ...newPo, quantity: e.target.value })} required />
              <input className="rounded-xl border px-3 py-2" type="number" placeholder="Unit price" value={newPo.unit_price} onChange={(e) => setNewPo({ ...newPo, unit_price: e.target.value })} required />
              <button className="rounded-xl bg-amber-700 px-4 py-2 text-white md:col-span-2">Save Purchase Order</button>
            </form>
          </div>

          <div className="rounded-2xl border bg-white p-5">
            <h2 className="text-xl font-bold">Goods Receiving</h2>
            <form onSubmit={createGoodsReceived} className="mt-4 grid gap-3 md:grid-cols-2">
              <select className="rounded-xl border px-3 py-2" value={newGrn.purchase_order_id} onChange={(e) => setNewGrn({ ...newGrn, purchase_order_id: e.target.value })} required>
                <option value="">Select purchase order</option>
                {purchaseOrders.map((po) => <option key={po.id} value={po.id}>PO #{po.id} - {po.ingredient_name} - {po.status}</option>)}
              </select>
              <input className="rounded-xl border px-3 py-2" type="number" placeholder="Quantity received" value={newGrn.quantity_received} onChange={(e) => setNewGrn({ ...newGrn, quantity_received: e.target.value })} required />
              <input className="rounded-xl border px-3 py-2" placeholder="Received by" value={newGrn.received_by} onChange={(e) => setNewGrn({ ...newGrn, received_by: e.target.value })} required />
              <input className="rounded-xl border px-3 py-2" placeholder="Invoice number" value={newGrn.invoice_number} onChange={(e) => setNewGrn({ ...newGrn, invoice_number: e.target.value })} />
              <button className="rounded-xl bg-slate-900 px-4 py-2 text-white md:col-span-2">Receive Goods</button>
            </form>
          </div>
        </section>
      )}

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border bg-white p-5"><h2 className="text-xl font-bold">Purchase Orders</h2>{purchaseOrders.map((po) => <div key={po.id} className="mt-2 rounded-xl border p-3">PO #{po.id} — {po.ingredient_name} <b>{po.status}</b><br />{po.supplier_name} | Qty {po.quantity} | Total ${Number(po.total_amount).toFixed(2)}</div>)}</div>
        <div className="rounded-2xl border bg-white p-5"><h2 className="text-xl font-bold">Goods Received</h2>{goodsReceived.map((g) => <div key={g.id} className="mt-2 rounded-xl border p-3">GRN #{g.id} — {g.ingredient_name}<br />PO #{g.purchase_order_id} | Qty {g.quantity_received} | Invoice {g.invoice_number || "—"}</div>)}</div>
      </section>

      {!reportMode && (
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border bg-white p-5">
            <h2 className="text-xl font-bold">Inventory Movement</h2>
            <form onSubmit={createInventoryMovement} className="mt-4 grid gap-3 md:grid-cols-2">
              <select className="rounded-xl border px-3 py-2" value={newMovement.ingredient_name} onChange={(e) => setNewMovement({ ...newMovement, ingredient_name: e.target.value })} required>
                <option value="">Select ingredient</option>
                {ingredients.map((i) => <option key={i.id} value={i.name}>{i.name}</option>)}
              </select>
              <select className="rounded-xl border px-3 py-2" value={newMovement.movement_type} onChange={(e) => setNewMovement({ ...newMovement, movement_type: e.target.value })}>
                <option value="KITCHEN_ISSUE">Kitchen Issue</option>
                <option value="WASTAGE">Wastage</option>
                <option value="PURCHASE_RECEIVED">Purchase Received</option>
                <option value="ADJUSTMENT">Adjustment</option>
                <option value="OPENING">Opening Stock</option>
              </select>
              <input className="rounded-xl border px-3 py-2" type="number" placeholder="Quantity" value={newMovement.quantity} onChange={(e) => setNewMovement({ ...newMovement, quantity: e.target.value })} required />
              <input className="rounded-xl border px-3 py-2" placeholder="Unit" value={newMovement.unit} onChange={(e) => setNewMovement({ ...newMovement, unit: e.target.value })} required />
              <input className="rounded-xl border px-3 py-2" placeholder="Reference" value={newMovement.reference} onChange={(e) => setNewMovement({ ...newMovement, reference: e.target.value })} />
              <input className="rounded-xl border px-3 py-2" placeholder="Created by" value={newMovement.created_by} onChange={(e) => setNewMovement({ ...newMovement, created_by: e.target.value })} required />
              <button className="rounded-xl bg-emerald-700 px-4 py-2 text-white md:col-span-2">Save Inventory Movement</button>
            </form>
          </div>

          <div className="rounded-2xl border bg-white p-5">
            <h2 className="text-xl font-bold">POS Sales Entry</h2>
            <form onSubmit={createPosSale} className="mt-4 grid gap-3 md:grid-cols-2">
              <input className="rounded-xl border px-3 py-2" placeholder="Outlet" value={newSale.outlet_name} onChange={(e) => setNewSale({ ...newSale, outlet_name: e.target.value })} required />
              <input className="rounded-xl border px-3 py-2" placeholder="Menu item name" value={newSale.menu_item_name} onChange={(e) => setNewSale({ ...newSale, menu_item_name: e.target.value })} required />
              <input className="rounded-xl border px-3 py-2" type="number" placeholder="Quantity sold" value={newSale.quantity_sold} onChange={(e) => setNewSale({ ...newSale, quantity_sold: e.target.value })} required />
              <input className="rounded-xl border px-3 py-2" type="number" placeholder="Selling price" value={newSale.selling_price} onChange={(e) => setNewSale({ ...newSale, selling_price: e.target.value })} required />
              <input className="rounded-xl border px-3 py-2 md:col-span-2" type="date" value={newSale.business_date} onChange={(e) => setNewSale({ ...newSale, business_date: e.target.value })} required />
              <button className="rounded-xl bg-indigo-700 px-4 py-2 text-white md:col-span-2">Save POS Sale</button>
            </form>
          </div>
        </section>
      )}

      <section className="rounded-2xl border bg-white p-5">
        <h2 className="text-xl font-bold">POS Profitability Summary</h2>
        {posProfitSummary.map((x) => <div key={x.id} className="mt-2 rounded-xl border p-3">{x.menuItem} — {x.quantitySold} sold<br />Revenue ${x.revenue.toFixed(2)} | Expected Cost ${x.expectedCost.toFixed(2)} | Gross Profit ${x.grossProfit.toFixed(2)} | Food Cost {x.foodCostPercent.toFixed(2)}%</div>)}
      </section>

      <section className="rounded-2xl border bg-white p-5">
        <h2 className="text-xl font-bold">Menu Engineering Analysis</h2>
        {posProfitSummary.map((item) => {
          const category = item.foodCostPercent <= 30 && item.quantitySold >= 10 ? "⭐ STAR" : item.foodCostPercent > 30 && item.quantitySold >= 10 ? "🐎 PLOW HORSE" : item.foodCostPercent <= 30 ? "🧩 PUZZLE" : "🐶 DOG";
          return <div key={item.id} className="mt-2 rounded-xl border p-3"><b>{item.menuItem}</b> <span className="ml-4 rounded-full bg-amber-100 px-3 py-1 text-xs font-bold">{category}</span><br />Sold {item.quantitySold} | Revenue ${item.revenue.toFixed(2)} | Gross Profit ${item.grossProfit.toFixed(2)} | Food Cost {item.foodCostPercent.toFixed(2)}%</div>;
        })}
      </section>

      <section className="rounded-2xl border bg-white p-5"><h2 className="text-xl font-bold">Stock Movement History</h2>{inventoryMovements.map((m) => <div key={m.id} className="mt-2 rounded-xl border p-3">{m.ingredient_name} — {m.movement_type} {m.quantity} {m.unit}<br />{m.reference || "No reference"} | {m.created_by}</div>)}</section>
      <section className="rounded-2xl border bg-white p-5"><h2 className="text-xl font-bold">Wastage Cost Summary</h2><b>Total Wastage Cost: ${totalWastageCost.toFixed(2)}</b>{wastageSummary.map((w) => <div key={w.id} className="mt-2">{w.ingredient} — {w.quantity} {w.unit} × ${w.costPerUnit.toFixed(2)} = ${w.totalCost.toFixed(2)}</div>)}</section>
      <section className="rounded-2xl border bg-white p-5"><h2 className="text-xl font-bold">Stock Balance Summary</h2>{stockBalances.map((s) => <div key={s.ingredient} className="mt-2">{s.ingredient} | Received {s.received.toFixed(3)} | Issue {s.issued.toFixed(3)} | Waste {s.wastage.toFixed(3)} | Closing <b>{s.closing.toFixed(3)} {s.unit}</b></div>)}</section>
      <section className="grid gap-4 lg:grid-cols-2"><div className="rounded-2xl border bg-white p-5"><h2 className="text-xl font-bold">Ingredient Inventory</h2>{ingredients.map((i) => <div key={i.id} className="mt-2 rounded-xl border p-3">{i.name} — ${Number(i.cost_per_unit).toFixed(2)} / {i.unit}<br />{i.supplier_name || "No supplier"}</div>)}</div><div className="rounded-2xl border bg-white p-5"><h2 className="text-xl font-bold">Recipe Costing</h2>{recipes.map((r) => <div key={r.id} className="mt-2 rounded-xl border p-3">{r.name} — {Number(r.food_cost_percentage).toFixed(2)}%<br />Selling ${Number(r.selling_price).toFixed(2)} | Cost ${Number(r.total_cost).toFixed(2)}</div>)}</div></section>
      <section className="rounded-2xl border bg-white p-5"><h2 className="text-xl font-bold">AI Food Cost Alerts</h2>{alerts.map((a) => <div key={a.id} className="mt-2 rounded-xl border border-red-200 bg-red-50 p-3"><b>{a.alert_type}</b><br />{a.message}</div>)}</section>
    </div>
  );
}
