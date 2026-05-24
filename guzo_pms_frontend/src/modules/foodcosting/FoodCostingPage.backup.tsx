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
export default function FoodCostingPage() {
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(false);
  const [newRecipe, setNewRecipe] = useState({
    name: "",
    outlet_name: "Main Restaurant",
    selling_price: "",
  });

  const [recipeLines, setRecipeLines] = useState([
    { ingredient_id: "", quantity_used: "" },
  ]);
  const [newIngredient, setNewIngredient] = useState({
    name: "",
    unit: "kg",
    purchase_price: "",
    cost_per_unit: "",
    supplier_name: "",
  });

  async function createRecipe(event: React.FormEvent) {
    event.preventDefault();

    await fetch(`${API_BASE_URL}/food-costing/recipes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        property_code: DEFAULT_PROPERTY_CODE,
        name: newRecipe.name,
        outlet_name: newRecipe.outlet_name,
        selling_price: Number(newRecipe.selling_price),
        ingredients: recipeLines
          .filter((line) => line.ingredient_id && line.quantity_used)
          .map((line) => ({
            ingredient_id: Number(line.ingredient_id),
            quantity_used: Number(line.quantity_used),
          })),
      }),
    });

    setNewRecipe({
      name: "",
      outlet_name: "Main Restaurant",
      selling_price: "",
    });

    setRecipeLines([{ ingredient_id: "", quantity_used: "" }]);

    loadData();
  }

  async function loadData() {
    setLoading(true);
    try {
      const [i, r, a] = await Promise.all([
        fetch(`${API_BASE_URL}/food-costing/ingredients?property_code=${DEFAULT_PROPERTY_CODE}`),
        fetch(`${API_BASE_URL}/food-costing/recipes?property_code=${DEFAULT_PROPERTY_CODE}`),
        fetch(`${API_BASE_URL}/food-costing/alerts?property_code=${DEFAULT_PROPERTY_CODE}`),
      ]);

      setIngredients(await i.json());
      setRecipes(await r.json());
      setAlerts(await a.json());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function addIngredient(event: React.FormEvent) {
    event.preventDefault();

    await fetch(`${API_BASE_URL}/food-costing/ingredients`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        property_code: DEFAULT_PROPERTY_CODE,
        name: newIngredient.name,
        unit: newIngredient.unit,
        purchase_price: Number(newIngredient.purchase_price),
        cost_per_unit: Number(newIngredient.cost_per_unit),
        supplier_name: newIngredient.supplier_name || null,
      }),
    });

    setNewIngredient({
      name: "",
      unit: "kg",
      purchase_price: "",
      cost_per_unit: "",
      supplier_name: "",
    });

    loadData();
  }

  async function addIngredient(event: React.FormEvent) {
    event.preventDefault();

    await fetch(`${API_BASE_URL}/food-costing/ingredients`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        property_code: DEFAULT_PROPERTY_CODE,
        name: newIngredient.name,
        unit: newIngredient.unit,
        purchase_price: Number(newIngredient.purchase_price),
        cost_per_unit: Number(newIngredient.cost_per_unit),
        supplier_name: newIngredient.supplier_name || null,
      }),
    });

    setNewIngredient({
      name: "",
      unit: "kg",
      purchase_price: "",
      cost_per_unit: "",
      supplier_name: "",
    });

    loadData();
  }

  const avgFoodCost = useMemo(() => {
    if (!recipes.length) return 0;
    return recipes.reduce((sum, r) => sum + Number(r.food_cost_percentage || 0), 0) / recipes.length;
  }, [recipes]);

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
          Five-star hotel system for recipe costing, inventory control, kitchen production,
          purchasing, POS analysis, finance reporting, and AI food-cost alerts.
        </p>

        <button
          onClick={loadData}
          className="mt-4 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
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
          <p className="text-sm text-slate-500">AI Alerts</p>
          <p className="mt-2 text-3xl font-bold">{alerts.length}</p>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        {[
          ["Recipe Costing", "Ingredients, portion cost, selling price, food cost %, and gross profit."],
          ["Inventory Control", "Opening stock, purchases, kitchen issues, closing stock, wastage, and variance."],
          ["Purchasing Control", "Supplier comparison, purchase orders, goods receiving, and price alerts."],
          ["Kitchen Production", "Standard recipe cards, portion control, yield, batch production, and prep waste."],
          ["POS Integration", "Items sold, expected usage, actual usage, and low-profit menu analysis."],
          ["AI Agent", "Detects high cost, recommends price changes, flags waste, and creates daily reports."],
        ].map(([title, text]) => (
          <div key={title} className="rounded-2xl border bg-white p-5 shadow-sm">
            <h2 className="text-lg font-bold text-slate-900">{title}</h2>
            <p className="mt-2 text-sm text-slate-600">{text}</p>
          </div>
        ))}
      </section>

      <section className="rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-xl font-bold">Add Ingredient</h2>
        <form onSubmit={addIngredient} className="mt-4 grid gap-3 md:grid-cols-5">
          <input
            className="rounded-xl border px-3 py-2 text-sm"
            placeholder="Ingredient name"
            value={newIngredient.name}
            onChange={(e) => setNewIngredient({ ...newIngredient, name: e.target.value })}
            required
          />
          <input
            className="rounded-xl border px-3 py-2 text-sm"
            placeholder="Unit"
            value={newIngredient.unit}
            onChange={(e) => setNewIngredient({ ...newIngredient, unit: e.target.value })}
            required
          />
          <input
            className="rounded-xl border px-3 py-2 text-sm"
            placeholder="Purchase price"
            type="number"
            step="0.01"
            value={newIngredient.purchase_price}
            onChange={(e) => setNewIngredient({ ...newIngredient, purchase_price: e.target.value })}
            required
          />
          <input
            className="rounded-xl border px-3 py-2 text-sm"
            placeholder="Cost per unit"
            type="number"
            step="0.01"
            value={newIngredient.cost_per_unit}
            onChange={(e) => setNewIngredient({ ...newIngredient, cost_per_unit: e.target.value })}
            required
          />
          <input
            className="rounded-xl border px-3 py-2 text-sm"
            placeholder="Supplier"
            value={newIngredient.supplier_name}
            onChange={(e) => setNewIngredient({ ...newIngredient, supplier_name: e.target.value })}
          />
          <button className="rounded-xl bg-amber-700 px-4 py-2 text-sm font-semibold text-white md:col-span-5">
            Save Ingredient
          </button>
        </form>
      </section>

      <section className="rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-xl font-bold">Create Recipe</h2>
        <p className="mt-1 text-sm text-slate-500">
          Build a standard recipe card with multiple ingredients and quantities.
        </p>

        <form onSubmit={createRecipe} className="mt-4 space-y-4">
          <div className="grid gap-3 md:grid-cols-3">
            <input
              className="rounded-xl border px-3 py-2 text-sm"
              placeholder="Recipe name"
              value={newRecipe.name}
              onChange={(e) => setNewRecipe({ ...newRecipe, name: e.target.value })}
              required
            />

            <input
              className="rounded-xl border px-3 py-2 text-sm"
              placeholder="Outlet name"
              value={newRecipe.outlet_name}
              onChange={(e) => setNewRecipe({ ...newRecipe, outlet_name: e.target.value })}
              required
            />

            <input
              className="rounded-xl border px-3 py-2 text-sm"
              placeholder="Selling price"
              type="number"
              step="0.01"
              value={newRecipe.selling_price}
              onChange={(e) => setNewRecipe({ ...newRecipe, selling_price: e.target.value })}
              required
            />
          </div>

          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-700">Recipe Ingredients</h3>

            {recipeLines.map((line, index) => (
              <div key={index} className="grid gap-3 md:grid-cols-[1fr_160px_90px]">
                <select
                  className="rounded-xl border px-3 py-2 text-sm"
                  value={line.ingredient_id}
                  onChange={(e) => {
                    const next = [...recipeLines];
                    next[index].ingredient_id = e.target.value;
                    setRecipeLines(next);
                  }}
                  required
                >
                  <option value="">Select ingredient</option>
                  {ingredients.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name} - ${Number(item.cost_per_unit).toFixed(2)} / {item.unit}
                    </option>
                  ))}
                </select>

                <input
                  className="rounded-xl border px-3 py-2 text-sm"
                  placeholder="Quantity used"
                  type="number"
                  step="0.001"
                  value={line.quantity_used}
                  onChange={(e) => {
                    const next = [...recipeLines];
                    next[index].quantity_used = e.target.value;
                    setRecipeLines(next);
                  }}
                  required
                />

                <button
                  type="button"
                  className="rounded-xl border px-3 py-2 text-sm"
                  onClick={() => {
                    if (recipeLines.length === 1) return;
                    setRecipeLines(recipeLines.filter((_, i) => i !== index));
                  }}
                >
                  Remove
                </button>
              </div>
            ))}

            <button
              type="button"
              className="rounded-xl border border-amber-700 px-4 py-2 text-sm font-semibold text-amber-800"
              onClick={() =>
                setRecipeLines([...recipeLines, { ingredient_id: "", quantity_used: "" }])
              }
            >
              + Add Ingredient Line
            </button>
          </div>

          <button className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white">
            Save Multi-Ingredient Recipe
          </button>
        </form>
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
            {recipes.length ? recipes.map((recipe) => (
              <div key={recipe.id} className="rounded-xl border p-3 text-sm">
                <div className="flex justify-between">
                  <span className="font-semibold">{recipe.name}</span>
                  <span>{Number(recipe.food_cost_percentage).toFixed(2)}%</span>
                </div>
                <div className="text-xs text-slate-500">
                  Selling ${Number(recipe.selling_price).toFixed(2)} | Cost ${Number(recipe.total_cost).toFixed(2)}
                </div>
              </div>
            )) : <p className="text-sm text-slate-500">No recipe records yet.</p>}
          </div>
        </div>
      </section>

      <section className="rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-xl font-bold">AI Food Cost Alerts</h2>
        <div className="mt-4 space-y-2">
          {alerts.length ? alerts.map((alert) => (
            <div key={alert.id} className="rounded-xl border border-red-200 bg-red-50 p-4">
              <p className="font-bold text-red-800">{alert.alert_type}</p>
              <p className="text-sm text-red-700">{alert.message}</p>
            </div>
          )) : <p className="text-sm text-slate-500">No AI food-cost alerts yet.</p>}
        </div>
      </section>
    </div>
  );
}
