import { useEffect, useMemo, useState } from "react";
import { API_BASE_URL, DEFAULT_PROPERTY_CODE } from "../../config/pms";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Ingredient = {
  id: number;
  name: string;
  unit: string;
  cost_per_unit: string | number;
  supplier_name?: string | null;
};

type Recipe = {
  id: number;
  name: string;
  outlet_name?: string | null;
  selling_price: string | number;
  total_cost: string | number;
  food_cost_percentage: string | number;
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
  invoice_number?: string | null;
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

type Alert = {
  id: number;
  alert_type: string;
  message: string;
  severity: string;
};

type RecipeIngredientLine = {
  id: number;
  recipe_id: number;
  ingredient_id: number;
  quantity_used: number;
  cost_used: number;
};

const money = (value: number) => `$${value.toFixed(2)}`;

export default function FoodCostingPage() {
  const [role, setRole] = useState("fb_controller");
  const [activeWorkflow, setActiveWorkflow] = useState("dashboard");
  const [loading, setLoading] = useState(false);

  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [goodsReceived, setGoodsReceived] = useState<GoodsReceived[]>([]);
  const [inventoryMovements, setInventoryMovements] = useState<InventoryMovement[]>([]);
  const [posSales, setPosSales] = useState<PosSale[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  const [physicalCounts, setPhysicalCounts] = useState<Record<string, string>>({});
  const [selectedRecipeId, setSelectedRecipeId] = useState<number | "">("");
  const [recipeLines, setRecipeLines] = useState<RecipeIngredientLine[]>([]);
  const [newRecipeIngredient, setNewRecipeIngredient] = useState({
    ingredient_id: "",
    quantity_used: "",
  });

  const [newRecipe, setNewRecipe] = useState({
    name: "",
    outlet_name: "Main Restaurant",
    selling_price: "",
  });

  const [newIngredient, setNewIngredient] = useState({
    name: "",
    unit: "",
    cost_per_unit: "",
    supplier_name: "",
  });

  async function getJson(path: string) {
    const res = await fetch(`${API_BASE_URL}${path}`);
    if (!res.ok) return [];
    return res.json();
  }

  async function loadData() {
    setLoading(true);
    try {
      const [i, r, po, grn, mov, sales, a] = await Promise.all([
        getJson(`/food-costing/ingredients?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/recipes?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/purchase-orders?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/goods-received?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/inventory-movements?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/pos-sales?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/alerts?property_code=${DEFAULT_PROPERTY_CODE}`),
      ]);

      setIngredients(Array.isArray(i) ? i : []);
      setRecipes(Array.isArray(r) ? r : []);
      setPurchaseOrders(Array.isArray(po) ? po : []);
      setGoodsReceived(Array.isArray(grn) ? grn : []);
      setInventoryMovements(Array.isArray(mov) ? mov : []);
      setPosSales(Array.isArray(sales) ? sales : []);
      setAlerts(Array.isArray(a) ? a : []);
    } finally {
      setLoading(false);
    }
  }

  async function createIngredient(e: React.FormEvent) {
    e.preventDefault();

    if (!newIngredient.name || !newIngredient.unit || !newIngredient.cost_per_unit) {
      alert("Ingredient name, unit, and cost per unit are required.");
      return;
    }

    const costPerUnit = Number(newIngredient.cost_per_unit);

    if (costPerUnit <= 0) {
      alert("Cost per unit must be greater than 0.");
      return;
    }

    await fetch(`${API_BASE_URL}/food-costing/ingredients`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        property_code: DEFAULT_PROPERTY_CODE,
        name: newIngredient.name,
        unit: newIngredient.unit,
        purchase_price: costPerUnit,
        cost_per_unit: costPerUnit,
        supplier_name: newIngredient.supplier_name,
      }),
    });

    setNewIngredient({
      name: "",
      unit: "",
      cost_per_unit: "",
      supplier_name: "",
    });

    await loadData();
  }

  async function createNewRecipe(e: React.FormEvent) {
    e.preventDefault();

    if (!newRecipe.name || !newRecipe.selling_price) {
      alert("Recipe name and selling price are required.");
      return;
    }

    await fetch(`${API_BASE_URL}/food-costing/recipes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        property_code: DEFAULT_PROPERTY_CODE,
        name: newRecipe.name,
        outlet_name: newRecipe.outlet_name,
        selling_price: Number(newRecipe.selling_price),
        ingredients: [],
      }),
    });

    setNewRecipe({
      name: "",
      outlet_name: "Main Restaurant",
      selling_price: "",
    });

    await loadData();
  }

  async function loadRecipeLines(recipeId: number) {
    const data = await getJson(`/food-costing/recipes/${recipeId}/ingredients`);
    setRecipeLines(Array.isArray(data) ? data : []);
  }

  async function addRecipeIngredient(e: React.FormEvent) {
    e.preventDefault();

    if (!selectedRecipeId || !newRecipeIngredient.ingredient_id || !newRecipeIngredient.quantity_used) {
      return;
    }

    const quantityUsed = Number(newRecipeIngredient.quantity_used);

    if (quantityUsed <= 0 || quantityUsed > 100) {
      alert("Quantity used must be greater than 0 and less than or equal to 100.");
      return;
    }

    await fetch(`${API_BASE_URL}/food-costing/recipes/ingredients`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        recipe_id: Number(selectedRecipeId),
        ingredient_id: Number(newRecipeIngredient.ingredient_id),
        quantity_used: quantityUsed,
      }),
    });

    setNewRecipeIngredient({
      ingredient_id: "",
      quantity_used: "",
    });

    await loadRecipeLines(Number(selectedRecipeId));
    await loadData();
  }

  async function deleteRecipeIngredient(lineId: number) {
    await fetch(`${API_BASE_URL}/food-costing/recipes/ingredients/${lineId}`, {
      method: "DELETE",
    });

    if (selectedRecipeId) {
      await loadRecipeLines(Number(selectedRecipeId));
    }

    await loadData();
  }

  useEffect(() => {
    if (selectedRecipeId) {
      loadRecipeLines(Number(selectedRecipeId));
    } else {
      setRecipeLines([]);
    }
  }, [selectedRecipeId]);

  useEffect(() => {
    loadData();
  }, []);

  const totalRevenue = useMemo(
    () => posSales.reduce((sum, sale) => sum + Number(sale.total_revenue || 0), 0),
    [posSales]
  );

  const avgFoodCost = useMemo(() => {
    if (!recipes.length) return 0;
    return recipes.reduce((sum, r) => sum + Number(r.food_cost_percentage || 0), 0) / recipes.length;
  }, [recipes]);

  const stockBalances = useMemo(() => {
    const balances: Record<
      string,
      {
        ingredient: string;
        received: number;
        manualIssue: number;
        posIssue: number;
        wastage: number;
        adjustment: number;
        closing: number;
        unit: string;
      }
    > = {};

    inventoryMovements.forEach((m) => {
      if (!balances[m.ingredient_name]) {
        balances[m.ingredient_name] = {
          ingredient: m.ingredient_name,
          received: 0,
          manualIssue: 0,
          posIssue: 0,
          wastage: 0,
          adjustment: 0,
          closing: 0,
          unit: m.unit,
        };
      }

      const qty = Number(m.quantity || 0);

      if (m.movement_type === "OPENING" || m.movement_type === "PURCHASE_RECEIVED") {
        balances[m.ingredient_name].received += qty;
      }

      if (m.movement_type === "KITCHEN_ISSUE") {
        if (m.created_by === "POS Auto Deduction" || String(m.reference || "").startsWith("POS Sale:")) {
          balances[m.ingredient_name].posIssue += qty;
        } else {
          balances[m.ingredient_name].manualIssue += qty;
        }
      }

      if (m.movement_type === "WASTAGE") balances[m.ingredient_name].wastage += qty;
      if (m.movement_type === "ADJUSTMENT") balances[m.ingredient_name].adjustment += qty;

      balances[m.ingredient_name].closing =
        balances[m.ingredient_name].received +
        balances[m.ingredient_name].adjustment -
        balances[m.ingredient_name].manualIssue -
        balances[m.ingredient_name].posIssue -
        balances[m.ingredient_name].wastage;
    });

    return Object.values(balances);
  }, [inventoryMovements]);

  const wastageCost = useMemo(() => {
    return inventoryMovements
      .filter((m) => m.movement_type === "WASTAGE")
      .reduce((sum, m) => {
        const ing = ingredients.find((i) => i.name === m.ingredient_name);
        return sum + Number(m.quantity || 0) * Number(ing?.cost_per_unit || 0);
      }, 0);
  }, [inventoryMovements, ingredients]);

  const posProfitability = useMemo(() => {
    return posSales.map((sale) => {
      const recipe = recipes.find((r) => r.name.toLowerCase() === sale.menu_item_name.toLowerCase());
      const expectedCost = Number(recipe?.total_cost || 0) * Number(sale.quantity_sold || 0);
      const revenue = Number(sale.total_revenue || 0);
      const grossProfit = revenue - expectedCost;
      const foodCostPercent = revenue > 0 ? (expectedCost / revenue) * 100 : 0;

      return {
        name: sale.menu_item_name,
        quantity: Number(sale.quantity_sold || 0),
        revenue,
        expectedCost,
        grossProfit,
        foodCostPercent,
      };
    });
  }, [posSales, recipes]);

  const theoreticalCost = useMemo(
    () => posProfitability.reduce((sum, item) => sum + item.expectedCost, 0),
    [posProfitability]
  );

  const actualCost = useMemo(() => {
    return inventoryMovements
      .filter((m) => m.movement_type === "KITCHEN_ISSUE" || m.movement_type === "WASTAGE")
      .reduce((sum, m) => {
        const ing = ingredients.find((i) => i.name === m.ingredient_name);
        return sum + Number(m.quantity || 0) * Number(ing?.cost_per_unit || 0);
      }, 0);
  }, [inventoryMovements, ingredients]);

  const variance = actualCost - theoreticalCost;

  const lowStock = useMemo(() => stockBalances.filter((s) => s.closing <= 10), [stockBalances]);

  const stockHealthData = useMemo(
    () => [
      { name: "Healthy", value: Math.max(stockBalances.length - lowStock.length, 0) },
      { name: "Low Stock", value: lowStock.length },
    ],
    [stockBalances, lowStock]
  );

  const varianceRows = useMemo(() => {
    return stockBalances.map((s) => {
      const physical = Number(physicalCounts[s.ingredient] ?? s.closing);
      const varianceQty = physical - s.closing;
      const ing = ingredients.find((i) => i.name === s.ingredient);
      const value = varianceQty * Number(ing?.cost_per_unit || 0);

      return {
        ...s,
        physical,
        varianceQty,
        value,
        status: varianceQty < 0 ? "SHORTAGE" : varianceQty > 0 ? "OVERAGE" : "MATCHED",
      };
    });
  }, [stockBalances, physicalCounts, ingredients]);

  const workflows = [
    { id: "dashboard", label: "Executive Dashboard", roles: ["executive", "fb_controller", "admin"] },
    { id: "purchasing", label: "Purchasing & Receiving", roles: ["storekeeper", "fb_controller", "admin"] },
    { id: "inventory", label: "Inventory Control", roles: ["storekeeper", "fb_controller", "admin"] },
    { id: "recipes", label: "Recipe Management", roles: ["chef", "fb_controller", "admin"] },
    { id: "analytics", label: "Analytics & Variance", roles: ["executive", "fb_controller", "finance", "admin"] },
  ];

  const visibleWorkflows = workflows.filter((w) => w.roles.includes(role));

  const selectedRecipe = recipes.find((recipe) => recipe.id === Number(selectedRecipeId));

  const selectedRecipeTotalCost = selectedRecipe ? Number(selectedRecipe.total_cost || 0) : 0;
  const selectedRecipeSellingPrice = selectedRecipe ? Number(selectedRecipe.selling_price || 0) : 0;
  const selectedRecipeFoodCost =
    selectedRecipeSellingPrice > 0
      ? (selectedRecipeTotalCost / selectedRecipeSellingPrice) * 100
      : 0;


  return (
    <div className="min-h-screen bg-slate-50 p-6 text-slate-900">
      <div className="mb-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.25em] text-amber-700">
              Guzo F&B Cost Control AI
            </p>
            <h1 className="mt-2 text-3xl font-black">Enterprise Food & Beverage Control Center</h1>
            <p className="mt-1 text-sm text-slate-500">
              Workflow UX, role-based operations, visual analytics, and executive food-cost reporting.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 print:hidden">
            <select
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold"
              value={role}
              onChange={(e) => {
                setRole(e.target.value);
                setActiveWorkflow("dashboard");
              }}
            >
              <option value="executive">Executive</option>
              <option value="fb_controller">F&B Controller</option>
              <option value="storekeeper">Storekeeper</option>
              <option value="chef">Chef</option>
              <option value="finance">Finance</option>
              <option value="admin">Admin</option>
            </select>

            <button
              onClick={loadData}
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-bold text-white"
            >
              {loading ? "Refreshing..." : "Refresh"}
            </button>

            <button
              onClick={() => window.print()}
              className="rounded-xl bg-amber-700 px-4 py-2 text-sm font-bold text-white"
            >
              Print Report
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <aside className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm print:hidden">
          <p className="mb-3 px-2 text-xs font-bold uppercase tracking-wide text-slate-400">
            Workflow Navigation
          </p>

          <div className="space-y-2">
            {visibleWorkflows.map((workflow) => (
              <button
                key={workflow.id}
                onClick={() => setActiveWorkflow(workflow.id)}
                className={
                  "w-full rounded-2xl px-4 py-3 text-left text-sm font-bold transition " +
                  (activeWorkflow === workflow.id
                    ? "bg-slate-900 text-white shadow-sm"
                    : "bg-slate-50 text-slate-700 hover:bg-slate-100")
                }
              >
                {workflow.label}
              </button>
            ))}
          </div>

          <div className="mt-6 rounded-2xl bg-amber-50 p-4 text-sm text-amber-900">
            <p className="font-bold">Current Role</p>
            <p className="capitalize">{role.replace("_", " ")}</p>
          </div>
        </aside>

        <main className="space-y-6">
          <section className="grid gap-4 md:grid-cols-5">
            <KpiCard label="POS Revenue" value={money(totalRevenue)} tone="dark" />
            <KpiCard label="Avg Food Cost" value={`${avgFoodCost.toFixed(2)}%`} tone={avgFoodCost > 35 ? "danger" : "success"} />
            <KpiCard label="Actual Cost" value={money(actualCost)} tone="neutral" />
            <KpiCard label="Variance" value={money(variance)} tone={variance > 0 ? "danger" : "success"} />
            <KpiCard label="Low Stock" value={String(lowStock.length)} tone={lowStock.length ? "warning" : "success"} />
          </section>

          {activeWorkflow === "dashboard" && (
            <section className="grid gap-6 xl:grid-cols-2">
              <Panel title="Food Cost Analytics">
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={posProfitability}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" hide />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="revenue" name="Revenue" />
                      <Bar dataKey="grossProfit" name="Gross Profit" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Panel>

              <Panel title="Stock Health">
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={stockHealthData} dataKey="value" nameKey="name" outerRadius={90} label>
                        {stockHealthData.map((_, index) => (
                          <Cell key={index} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </Panel>

              <Panel title="Executive Risk Summary">
                <div className="grid gap-3 md:grid-cols-2">
                  <RiskItem label="High Food Cost Alerts" value={alerts.length} />
                  <RiskItem label="Low Stock Items" value={lowStock.length} />
                  <RiskItem label="Wastage Cost" value={money(wastageCost)} />
                  <RiskItem label="Purchasing Open/Pending" value={purchaseOrders.filter((p) => p.status !== "RECEIVED").length} />
                </div>
              </Panel>

              <Panel title="AI Management Summary">
                <p className="text-sm leading-6 text-slate-600">
                  Daily F&B revenue is {money(totalRevenue)}. Average recipe food cost is {avgFoodCost.toFixed(2)}%.
                  Actual cost is {money(actualCost)} compared with theoretical cost {money(theoreticalCost)}.
                  Current variance is {money(variance)}. Review low-stock ingredients and high food-cost recipes.
                </p>
              </Panel>
            </section>
          )}

          {activeWorkflow === "purchasing" && (
            <section className="grid gap-6 xl:grid-cols-2">
              <Panel title="Purchase Orders">
                <DataTable
                  columns={["PO", "Ingredient", "Supplier", "Qty", "Total", "Status"]}
                  rows={purchaseOrders.map((po) => [
                    `#${po.id}`,
                    po.ingredient_name,
                    po.supplier_name,
                    po.quantity,
                    money(Number(po.total_amount || 0)),
                    po.status,
                  ])}
                />
              </Panel>

              <Panel title="Goods Receiving">
                <DataTable
                  columns={["GRN", "PO", "Ingredient", "Qty", "Invoice", "Received By"]}
                  rows={goodsReceived.map((g) => [
                    `#${g.id}`,
                    `PO #${g.purchase_order_id}`,
                    g.ingredient_name,
                    g.quantity_received,
                    g.invoice_number || "-",
                    g.received_by,
                  ])}
                />
              </Panel>
            </section>
          )}

          {activeWorkflow === "inventory" && (
            <section className="grid gap-6">
              <Panel title="Stock Balance Summary">
                <DataTable
                  columns={["Ingredient", "Received/Open", "Manual Issue", "POS Deduction", "Waste", "Closing"]}
                  rows={stockBalances.map((s) => [
                    s.ingredient,
                    `${s.received.toFixed(3)} ${s.unit}`,
                    `${s.manualIssue.toFixed(3)} ${s.unit}`,
                    `${s.posIssue.toFixed(3)} ${s.unit}`,
                    `${s.wastage.toFixed(3)} ${s.unit}`,
                    `${s.closing.toFixed(3)} ${s.unit}`,
                  ])}
                />
              </Panel>

              <Panel title="Inventory Movement Audit Trail">
                <DataTable
                  columns={["Ingredient", "Type", "Qty", "Reference", "Created By"]}
                  rows={inventoryMovements.map((m) => [
                    m.ingredient_name,
                    m.movement_type,
                    `${m.quantity} ${m.unit}`,
                    m.reference || "-",
                    m.created_by,
                  ])}
                />
              </Panel>
            </section>
          )}

          {activeWorkflow === "recipes" && (
            <section className="grid gap-6">
              <Panel title="Interactive Recipe Workspace">
                <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <form onSubmit={createNewRecipe} className="mb-5 rounded-2xl border border-amber-200 bg-amber-50 p-4">
                      <p className="text-xs font-black uppercase text-amber-700">
                        Add New Menu Recipe
                      </p>

                      <input
                        className="mt-3 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                        placeholder="Recipe/menu item name"
                        value={newRecipe.name}
                        onChange={(e) => setNewRecipe({ ...newRecipe, name: e.target.value })}
                      />

                      <input
                        className="mt-3 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                        placeholder="Outlet name"
                        value={newRecipe.outlet_name}
                        onChange={(e) => setNewRecipe({ ...newRecipe, outlet_name: e.target.value })}
                      />

                      <input
                        className="mt-3 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                        type="number"
                        step="0.01"
                        min="0.01"
                        placeholder="Selling price"
                        value={newRecipe.selling_price}
                        onChange={(e) => setNewRecipe({ ...newRecipe, selling_price: e.target.value })}
                      />

                      <button
                        type="submit"
                        className="mt-3 w-full rounded-xl bg-amber-700 px-4 py-2 text-sm font-black text-white"
                      >
                        Create New Recipe
                      </button>
                    </form>

                    <label className="text-xs font-black uppercase text-slate-500">
                      Select Recipe
                    </label>

                    <select
                      className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                      value={selectedRecipeId}
                      onChange={(e) =>
                        setSelectedRecipeId(e.target.value ? Number(e.target.value) : "")
                      }
                    >
                      <option value="">Choose recipe</option>
                      {recipes.map((recipe) => (
                        <option key={recipe.id} value={recipe.id}>
                          {recipe.name}
                        </option>
                      ))}
                    </select>

                    {selectedRecipe && (
                      <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                        <p className="text-xs font-black uppercase text-emerald-700">
                          Selected Recipe Summary
                        </p>
                        <h3 className="mt-1 text-xl font-black text-emerald-950">
                          {selectedRecipe.name}
                        </h3>

                        <div className="mt-3 grid gap-2 text-sm text-emerald-950">
                          <div className="flex justify-between">
                            <span>Selling Price</span>
                            <strong>{money(selectedRecipeSellingPrice)}</strong>
                          </div>
                          <div className="flex justify-between">
                            <span>Recipe Cost</span>
                            <strong>{money(selectedRecipeTotalCost)}</strong>
                          </div>
                          <div className="flex justify-between">
                            <span>Food Cost %</span>
                            <strong>{selectedRecipeFoodCost.toFixed(2)}%</strong>
                          </div>
                          <div className="flex justify-between">
                            <span>Ingredient Lines</span>
                            <strong>{recipeLines.length}</strong>
                          </div>
                        </div>
                      </div>
                    )}

                    <form onSubmit={addRecipeIngredient} className="mt-4 space-y-3 rounded-2xl border border-slate-200 bg-white p-4">
                        <div>
                          <label className="text-xs font-black uppercase text-slate-500">
                            Add Ingredient
                          </label>

                          <p className="mt-2 text-xs font-semibold text-slate-500">
                            Available ingredients: {ingredients.length}
                          </p>

                          <select
                            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                            value={String(newRecipeIngredient.ingredient_id)}
                            onChange={(e) =>
                              setNewRecipeIngredient({
                                ...newRecipeIngredient,
                                ingredient_id: e.target.value,
                              })
                            }
                          >
                            <option value="">Choose ingredient</option>
                            {ingredients.length === 0 ? (
                              <option value="" disabled>
                                No ingredients available
                              </option>
                            ) : (
                              ingredients.map((ingredient) => (
                                <option key={ingredient.id} value={`${ingredient.id}`}>
                                  {ingredient.name} — ${Number(ingredient.cost_per_unit || 0).toFixed(2)} / {ingredient.unit}
                                </option>
                              ))
                            )}
                          </select>
                        </div>

                        <div>
                          <label className="text-xs font-black uppercase text-slate-500">
                            Quantity Used
                          </label>

                          <input
                            className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                            type="number"
                            step="0.001"
                            min="0.001"
                            max="100"
                            placeholder="Example: 0.100"
                            value={newRecipeIngredient.quantity_used}
                            onChange={(e) =>
                              setNewRecipeIngredient({
                                ...newRecipeIngredient,
                                quantity_used: e.target.value,
                              })
                            }
                          />
                        </div>

                        <button
                          type="submit"
                          disabled={!selectedRecipeId}
                          className="w-full rounded-xl bg-slate-900 px-4 py-2 text-sm font-black text-white disabled:cursor-not-allowed disabled:bg-slate-300"
                        >
                          Add Ingredient to Recipe
                        </button>

                        {!selectedRecipeId && (
                          <p className="text-xs font-semibold text-amber-700">
                            Select a recipe first, then choose ingredient and quantity.
                          </p>
                        )}
                      </form>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-xs font-black uppercase text-slate-500">
                          Saved Recipe Ingredient Lines
                        </p>
                        <h3 className="mt-1 text-lg font-black text-slate-900">
                          {selectedRecipe ? selectedRecipe.name : "No recipe selected"}
                        </h3>
                      </div>

                      <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-black text-slate-600">
                        {recipeLines.length} lines
                      </span>
                    </div>

                    {!selectedRecipe && (
                      <div className="mt-4 rounded-2xl bg-amber-50 p-4 text-sm font-semibold text-amber-800">
                        Select a recipe to retrieve saved ingredients and edit the recipe.
                      </div>
                    )}

                    {selectedRecipe && recipeLines.length === 0 && (
                      <div className="mt-4 rounded-2xl bg-slate-50 p-6 text-center text-sm text-slate-500">
                        No ingredients saved yet. Add ingredients from the left panel.
                      </div>
                    )}

                    <div className="mt-4 grid gap-3">
                      {recipeLines.map((line) => {
                        const ingredient = ingredients.find((i) => i.id === line.ingredient_id);

                        return (
                          <div
                            key={line.id}
                            className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
                          >
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div>
                                <p className="text-xs font-black uppercase text-slate-400">
                                  Line #{line.id}
                                </p>
                                <h4 className="text-lg font-black text-slate-900">
                                  {ingredient?.name || `Ingredient #${line.ingredient_id}`}
                                </h4>
                                <p className="mt-1 text-sm text-slate-500">
                                  Qty Used: {Number(line.quantity_used || 0).toFixed(3)} {ingredient?.unit || ""}
                                </p>
                              </div>

                              <div className="text-right">
                                <p className="text-xs font-black uppercase text-slate-400">
                                  Cost Used
                                </p>
                                <p className="text-xl font-black text-slate-900">
                                  {money(Number(line.cost_used || 0))}
                                </p>
                              </div>
                            </div>

                            <button
                              onClick={() => deleteRecipeIngredient(line.id)}
                              className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-black text-red-700"
                            >
                              Delete Line #{line.id}
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </Panel>

              <section className="grid gap-6 xl:grid-cols-2">
                <Panel title="Recipe Costing">
                  <DataTable
                    columns={["Recipe", "Selling", "Cost", "Food Cost %"]}
                    rows={recipes.map((r) => [
                      r.name,
                      money(Number(r.selling_price || 0)),
                      money(Number(r.total_cost || 0)),
                      `${Number(r.food_cost_percentage || 0).toFixed(2)}%`,
                    ])}
                  />
                </Panel>

                <Panel title="Ingredient Master">
                  <form
                    onSubmit={createIngredient}
                    className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 p-4"
                  >
                    <p className="text-xs font-black uppercase text-emerald-700">
                      Add Ingredient Master
                    </p>

                    <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      <input
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                        placeholder="Ingredient name"
                        value={newIngredient.name}
                        onChange={(e) =>
                          setNewIngredient({
                            ...newIngredient,
                            name: e.target.value,
                          })
                        }
                      />

                      <input
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                        placeholder="Unit, e.g. kg, gm, pc"
                        value={newIngredient.unit}
                        onChange={(e) =>
                          setNewIngredient({
                            ...newIngredient,
                            unit: e.target.value,
                          })
                        }
                      />

                      <input
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                        type="number"
                        step="0.01"
                        min="0.01"
                        placeholder="Cost per unit"
                        value={newIngredient.cost_per_unit}
                        onChange={(e) =>
                          setNewIngredient({
                            ...newIngredient,
                            cost_per_unit: e.target.value,
                          })
                        }
                      />

                      <input
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                        placeholder="Supplier name"
                        value={newIngredient.supplier_name}
                        onChange={(e) =>
                          setNewIngredient({
                            ...newIngredient,
                            supplier_name: e.target.value,
                          })
                        }
                      />
                    </div>

                    <button
                      type="submit"
                      className="mt-4 rounded-xl bg-emerald-700 px-4 py-2 text-sm font-black text-white"
                    >
                      Create Ingredient
                    </button>
                  </form>

                  <DataTable
                    columns={["Ingredient", "Unit", "Cost/Unit", "Supplier"]}
                    rows={ingredients.map((i) => [
                      i.name,
                      i.unit,
                      money(Number(i.cost_per_unit || 0)),
                      i.supplier_name || "-",
                    ])}
                  />
                </Panel>
              </section>
            </section>
          )}

          {activeWorkflow === "analytics" && (
            <section className="grid gap-6">
              <Panel title="Actual vs Theoretical Food Cost">
                <div className="grid gap-4 md:grid-cols-4">
                  <KpiCard label="Theoretical" value={money(theoreticalCost)} tone="neutral" />
                  <KpiCard label="Actual" value={money(actualCost)} tone="neutral" />
                  <KpiCard label="Variance" value={money(variance)} tone={variance > 0 ? "danger" : "success"} />
                  <KpiCard label="Variance %" value={theoreticalCost ? `${((variance / theoreticalCost) * 100).toFixed(2)}%` : "0.00%"} tone="warning" />
                </div>
              </Panel>

              <Panel title="Physical Stock Count & Variance">
                <DataTable
                  columns={["Ingredient", "System", "Physical", "Variance", "Status"]}
                  rows={varianceRows.map((row) => [
                    row.ingredient,
                    `${row.closing.toFixed(3)} ${row.unit}`,
                    `${row.physical.toFixed(3)} ${row.unit}`,
                    `${row.varianceQty.toFixed(3)} ${row.unit}`,
                    row.status,
                  ])}
                />
              </Panel>

              <Panel title="Menu Engineering">
                <DataTable
                  columns={["Menu Item", "Sold", "Revenue", "Gross Profit", "Food Cost %", "Class"]}
                  rows={posProfitability.map((item) => {
                    const classification =
                      item.foodCostPercent <= 30 && item.quantity >= 10
                        ? "STAR"
                        : item.foodCostPercent > 30 && item.quantity >= 10
                        ? "PLOW HORSE"
                        : item.foodCostPercent <= 30
                        ? "PUZZLE"
                        : "DOG";

                    return [
                      item.name,
                      item.quantity,
                      money(item.revenue),
                      money(item.grossProfit),
                      `${item.foodCostPercent.toFixed(2)}%`,
                      classification,
                    ];
                  })}
                />
              </Panel>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "dark" | "danger" | "success" | "warning" | "neutral";
}) {
  const toneMap = {
    dark: "bg-slate-900 text-white",
    danger: "bg-red-50 text-red-900 border-red-200",
    success: "bg-emerald-50 text-emerald-900 border-emerald-200",
    warning: "bg-amber-50 text-amber-900 border-amber-200",
    neutral: "bg-white text-slate-900 border-slate-200",
  };

  return (
    <div className={`rounded-2xl border p-5 shadow-sm ${toneMap[tone]}`}>
      <p className="text-xs font-bold uppercase tracking-wide opacity-70">{label}</p>
      <p className="mt-2 text-2xl font-black">{value}</p>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-black text-slate-900">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function RiskItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs font-bold uppercase text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-black text-slate-900">{value}</p>
    </div>
  );
}

function DataTable({ columns, rows }: { columns: string[]; rows: (string | number)[][] }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
          <thead>
            <tr className="bg-slate-100">
              {columns.map((column, index) => (
                <th
                  key={column}
                  className={
                    "whitespace-nowrap border-b border-slate-200 px-5 py-4 text-xs font-black uppercase tracking-wide text-slate-600 " +
                    (index === 0 ? "rounded-tl-2xl" : "") +
                    (index === columns.length - 1 ? " rounded-tr-2xl text-right" : "")
                  }
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td
                  className="px-5 py-8 text-center text-sm font-semibold text-slate-500"
                  colSpan={columns.length}
                >
                  No records found.
                </td>
              </tr>
            ) : (
              rows.map((row, rowIndex) => (
                <tr
                  key={rowIndex}
                  className="border-b border-slate-100 transition hover:bg-slate-50"
                >
                  {row.map((cell, cellIndex) => (
                    <td
                      key={cellIndex}
                      className={
                        "whitespace-nowrap border-b border-slate-100 px-5 py-4 align-middle text-slate-700 " +
                        (cellIndex === 0 ? "font-bold text-slate-950" : "") +
                        (cellIndex === row.length - 1 ? " text-right font-semibold" : "")
                      }
                    >
                      {cell}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
