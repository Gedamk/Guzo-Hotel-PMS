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
import {
  AlertTriangle,
  BarChart3,
  Boxes,
  ChefHat,
  ClipboardList,
  Download,
  FileCheck2,
  LayoutDashboard,
  PackageMinus,
  PackagePlus,
  PackageSearch,
  RefreshCw,
  ScrollText,
  Truck,
  Utensils,
  WalletCards,
  type LucideIcon,
} from "lucide-react";

type Ingredient = {
  id: number;
  name: string;
  category?: string | null;
  unit: string;
  purchase_price?: string | number;
  cost_per_unit: string | number;
  last_purchase_price?: string | number | null;
  average_cost?: string | number | null;
  reorder_level?: string | number | null;
  expiry_date?: string | null;
  storage_location?: string | null;
  supplier_name?: string | null;
};

type Supplier = {
  id: number;
  supplier_name: string;
  contact_name?: string | null;
  phone?: string | null;
  email?: string | null;
  payment_terms?: string | null;
  is_active?: boolean;
};

type Recipe = {
  id: number;
  name: string;
  outlet_name?: string | null;
  selling_price: string | number;
  total_cost: string | number;
  food_cost_percentage: string | number;
  target_cost_percentage?: string | number | null;
  profit_margin?: string | number | null;
  approval_status?: string | null;
};

type PurchaseOrder = {
  id: number;
  supplier_name: string;
  ingredient_name: string;
  quantity: number;
  ordered_qty?: number;
  received_qty?: number;
  rejected_qty?: number;
  unit_price: number;
  unit_cost?: number;
  invoice_number?: string | null;
  received_by?: string | null;
  approval_status?: string | null;
  total_amount: number;
  status: string;
};

type GoodsReceived = {
  id: number;
  purchase_order_id: number;
  supplier_name: string;
  ingredient_name: string;
  ordered_qty?: number;
  quantity_received: number;
  rejected_qty?: number;
  unit_cost?: number;
  received_by: string;
  invoice_number?: string | null;
  approval_status?: string | null;
};

type InventoryMovement = {
  id: number;
  ingredient_name: string;
  movement_type: string;
  quantity: number;
  unit: string;
  unit_cost?: number | null;
  stock_value?: number | null;
  reference?: string | null;
  notes?: string | null;
  created_by: string;
};

type KitchenRequisition = {
  id: number;
  ingredient_name: string;
  requested_qty: number;
  issued_qty?: number | null;
  unit: string;
  outlet_name?: string | null;
  requested_by: string;
  issued_by?: string | null;
  status: string;
  priority?: string | null;
  notes?: string | null;
};

type PosSale = {
  id: number;
  outlet_name: string;
  menu_item_name: string;
  quantity_sold: number;
  selling_price: number;
  total_revenue: number;
  tax_amount?: number | null;
  service_charge_amount?: number | null;
  payment_method?: string | null;
  room_charge_booking_id?: number | null;
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

type ReportPeriod = "daily" | "weekly" | "monthly";
type ReportStatus =
  | "draft"
  | "submitted"
  | "finance_reviewed"
  | "fnb_manager_approved"
  | "gm_approved"
  | "locked";

type ReportApproval = {
  id?: number;
  status: ReportStatus;
  prepared_by?: string | null;
  prepared_at?: string | null;
  finance_reviewed_by?: string | null;
  finance_reviewed_at?: string | null;
  fnb_approved_by?: string | null;
  fnb_approved_at?: string | null;
  gm_approved_by?: string | null;
  gm_approved_at?: string | null;
  locked_at?: string | null;
};

const money = (value: number) => `ETB ${value.toFixed(2)}`;
const hotelDepartments = [
  "Main Kitchen",
  "Ethiopian Traditional Kitchen",
  "Pastry/Bakery",
  "Garde Manger",
  "Juice Bar",
  "Bar",
  "Coffee Shop",
  "Banquet Kitchen",
  "Staff Cafeteria",
];
const ethiopianItems = [
  "Teff flour",
  "Injera",
  "Berbere",
  "Shiro",
  "Niter kibbeh",
  "Doro wot ingredients",
  "Tibs ingredients",
  "Kitfo ingredients",
  "Coffee beans",
  "Bottled water",
  "Soft drinks",
];
const hotelUnits = ["kg", "gram", "liter", "ml", "bottle", "crate", "pack", "piece"];
const alaCarteRecipeMeta: Record<string, { menuType: string; portion: string }> = {
  "Grilled Beef Tenderloin with Pepper Sauce": { menuType: "À La Carte", portion: "1 plate" },
  "Pan-Seared Nile Perch with Lemon Butter Sauce": { menuType: "À La Carte", portion: "1 plate" },
  "Doro Wot Fine Dining Plate": { menuType: "À La Carte", portion: "1 plate" },
  "Kitfo Royal Plate": { menuType: "À La Carte", portion: "1 plate" },
  "Chicken Alfredo Pasta": { menuType: "À La Carte", portion: "1 plate" },
};

const todayIso = () => new Date().toISOString().slice(0, 10);
const actorByRole: Record<string, string> = {
  general_manager: "manager@guzo.local",
  fb_controller: "fnb@guzo.local",
  fnb_manager: "fnb.manager@guzo.local",
  purchasing_manager: "purchasing@guzo.local",
  storekeeper: "fnb@guzo.local",
  chef: "chef@guzo.local",
  executive_chef: "executive.chef@guzo.local",
  finance_manager: "finance.manager@guzo.local",
  admin: "admin@guzo.local",
};

function addDays(dateText: string, days: number) {
  const date = new Date(`${dateText}T00:00:00`);
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function monthEnd(dateText: string) {
  const date = new Date(`${dateText}T00:00:00`);
  return new Date(date.getFullYear(), date.getMonth() + 1, 0).toISOString().slice(0, 10);
}

function reportRange(period: ReportPeriod, anchorDate: string) {
  if (period === "weekly") {
    return { start: anchorDate, end: addDays(anchorDate, 6), label: "Weekly" };
  }
  if (period === "monthly") {
    return { start: anchorDate.slice(0, 8) + "01", end: monthEnd(anchorDate), label: "Monthly" };
  }
  return { start: anchorDate, end: anchorDate, label: "Daily" };
}

function csvCell(value: unknown) {
  const text = value === null || value === undefined ? "" : String(value);
  return `"${text.replace(/"/g, '""')}"`;
}

function csvSection(title: string, columns: string[], rows: (string | number | null | undefined)[][]) {
  return [
    [title].map(csvCell).join(","),
    columns.map(csvCell).join(","),
    ...(rows.length ? rows.map((row) => row.map(csvCell).join(",")) : [[`No ${title.toLowerCase()} records`].map(csvCell).join(",")]),
    "",
  ].join("\n");
}

export default function FoodCostingPage() {
  const [role, setRole] = useState("fb_controller");
  const [activeWorkflow, setActiveWorkflow] = useState("fnb-dashboard");
  const [activeMetric, setActiveMetric] = useState("revenue");
  const [reportPeriod, setReportPeriod] = useState<ReportPeriod>("daily");
  const [reportDate, setReportDate] = useState(todayIso());
  const [reportApproval, setReportApproval] = useState<ReportApproval>({ status: "draft" });
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [loading, setLoading] = useState(false);

  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [goodsReceived, setGoodsReceived] = useState<GoodsReceived[]>([]);
  const [inventoryMovements, setInventoryMovements] = useState<InventoryMovement[]>([]);
  const [kitchenRequisitions, setKitchenRequisitions] = useState<KitchenRequisition[]>([]);
  const [posSales, setPosSales] = useState<PosSale[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  const [physicalCounts, setPhysicalCounts] = useState<Record<string, string>>({});
  const [showSupplierForm, setShowSupplierForm] = useState(false);
  const [filters, setFilters] = useState({
    search: "",
    date: "",
    department: "",
    category: "",
    supplier: "",
    item: "",
    status: "",
  });
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
    category: "",
    unit: "",
    cost_per_unit: "",
    supplier_name: "",
    reorder_level: "",
    expiry_date: "",
    storage_location: "",
  });
  const [newSupplier, setNewSupplier] = useState({
    supplier_name: "",
    contact_name: "",
    phone: "",
    email: "",
    payment_terms: "",
  });
  const [newPo, setNewPo] = useState({
    supplier_name: "",
    ingredient_name: "Teff flour",
    quantity: "",
    unit_price: "",
  });
  const [newGrn, setNewGrn] = useState({
    purchase_order_id: "",
    quantity_received: "",
    rejected_qty: "0",
    unit_cost: "",
    received_by: "Storekeeper",
    invoice_number: "",
  });
  const [newRequisition, setNewRequisition] = useState({
    ingredient_name: "Teff flour",
    requested_qty: "",
    unit: "kg",
    outlet_name: "Main Kitchen",
    requested_by: "Chef",
    notes: "",
  });
  const [issueForm, setIssueForm] = useState({
    requisition_id: "",
    issued_qty: "",
    issued_by: "Storekeeper",
    manager_override: false,
    override_by: "",
  });
  const [newWaste, setNewWaste] = useState({
    ingredient_name: "Injera",
    quantity: "",
    unit: "piece",
    reason: "",
    recorded_by: "Chef",
  });
  const [newStockCount, setNewStockCount] = useState({
    ingredient_name: "Teff flour",
    system_qty: "",
    physical_qty: "",
    unit: "kg",
    counted_by: "Storekeeper",
    notes: "",
  });

  async function getJson(path: string) {
    const res = await fetch(`${API_BASE_URL}${path}`);
    if (!res.ok) return [];
    return res.json();
  }

  async function sendJson(path: string, method: "POST" | "PATCH", body: unknown) {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        "X-PMS-User-Email": actorByRole[role] || "fnb@guzo.local",
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || "The request could not be completed. Please check the details and try again.");
    }
    return res.json();
  }

  async function loadReportApproval(period = reportPeriod, window = reportWindow) {
    try {
      const data = await getJson(
        `/food-costing/reports/approval?property_code=${DEFAULT_PROPERTY_CODE}&report_period=${period}&report_start_date=${window.start}&report_end_date=${window.end}`
      );
      if (data && !Array.isArray(data)) {
        setReportApproval({
          status: data.status || "draft",
          prepared_by: data.prepared_by,
          prepared_at: data.prepared_at,
          finance_reviewed_by: data.finance_reviewed_by,
          finance_reviewed_at: data.finance_reviewed_at,
          fnb_approved_by: data.fnb_approved_by,
          fnb_approved_at: data.fnb_approved_at,
          gm_approved_by: data.gm_approved_by,
          gm_approved_at: data.gm_approved_at,
          locked_at: data.locked_at,
        });
      }
    } catch {
      setReportApproval({ status: "draft" });
    }
  }

  async function updateReportApproval(action: string) {
    if (reportApproval.status === "locked" && action !== "override") {
      alert("This F&B report is locked. Admin override is required.");
      return;
    }
    setApprovalLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/food-costing/reports/approval`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-PMS-User-Email": actorByRole[role] || "fnb@guzo.local",
        },
        body: JSON.stringify({
          property_code: DEFAULT_PROPERTY_CODE,
          report_period: reportPeriod,
          report_start_date: reportWindow.start,
          report_end_date: reportWindow.end,
          action,
          prepared_by: actorByRole[role] || "fnb@guzo.local",
          override_reason: action === "override" ? "Admin report unlock / correction" : undefined,
        }),
      });
      if (!res.ok) {
        const message = await res.text();
        throw new Error(message || "Report approval update failed.");
      }
      const data = await res.json();
      setReportApproval({ status: data.status || "draft", ...data });
    } catch (error) {
      alert(error instanceof Error ? error.message : "Report approval update failed.");
    } finally {
      setApprovalLoading(false);
    }
  }

  async function loadData() {
    setLoading(true);
    try {
      const i = await getJson(`/food-costing/ingredients?property_code=${DEFAULT_PROPERTY_CODE}`);
      const [suppliersData, r, po, grn, mov, req, sales, a] = await Promise.all([
        getJson(`/food-costing/suppliers?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/recipes?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/purchase-orders?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/goods-received?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/inventory-movements?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/kitchen-requisitions?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/pos-sales?property_code=${DEFAULT_PROPERTY_CODE}`),
        getJson(`/food-costing/alerts?property_code=${DEFAULT_PROPERTY_CODE}`),
      ]);

      setIngredients(Array.isArray(i) ? i : []);
      setSuppliers(Array.isArray(suppliersData) ? suppliersData : []);
      setRecipes(Array.isArray(r) ? r : []);
      setPurchaseOrders(Array.isArray(po) ? po : []);
      setGoodsReceived(Array.isArray(grn) ? grn : []);
      setInventoryMovements(Array.isArray(mov) ? mov : []);
      setKitchenRequisitions(Array.isArray(req) ? req : []);
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
        category: newIngredient.category || undefined,
        unit: newIngredient.unit,
        purchase_price: costPerUnit,
        cost_per_unit: costPerUnit,
        last_purchase_price: costPerUnit,
        average_cost: costPerUnit,
        supplier_name: newIngredient.supplier_name,
        reorder_level: newIngredient.reorder_level ? Number(newIngredient.reorder_level) : undefined,
        expiry_date: newIngredient.expiry_date || undefined,
        storage_location: newIngredient.storage_location || undefined,
      }),
    });

    setNewIngredient({
      name: "",
      category: "",
      unit: "",
      cost_per_unit: "",
      supplier_name: "",
      reorder_level: "",
      expiry_date: "",
      storage_location: "",
    });

    await loadData();
  }

  async function createSupplier(e: React.FormEvent) {
    e.preventDefault();
    if (!newSupplier.supplier_name.trim()) {
      alert("Supplier name is required.");
      return;
    }
    try {
      await sendJson("/food-costing/suppliers", "POST", {
        property_code: DEFAULT_PROPERTY_CODE,
        supplier_name: newSupplier.supplier_name.trim(),
        contact_name: newSupplier.contact_name.trim() || undefined,
        phone: newSupplier.phone.trim() || undefined,
        email: newSupplier.email.trim() || undefined,
        payment_terms: newSupplier.payment_terms.trim() || undefined,
      });
      setNewSupplier({
        supplier_name: "",
        contact_name: "",
        phone: "",
        email: "",
        payment_terms: "",
      });
      setShowSupplierForm(false);
      await loadData();
    } catch (error) {
      alert(error instanceof Error ? error.message : "Supplier could not be saved.");
    }
  }

  async function createPurchaseOrder(e: React.FormEvent) {
    e.preventDefault();
    if (!newPo.supplier_name || !newPo.ingredient_name || Number(newPo.quantity) <= 0 || Number(newPo.unit_price) <= 0) {
      alert("Supplier, item, quantity, and unit cost are required.");
      return;
    }
    try {
      await sendJson("/food-costing/purchase-orders", "POST", {
        property_code: DEFAULT_PROPERTY_CODE,
        supplier_name: newPo.supplier_name,
        ingredient_name: newPo.ingredient_name,
        quantity: Number(newPo.quantity),
        unit_price: Number(newPo.unit_price),
      });
      setNewPo({ supplier_name: "", ingredient_name: "Teff flour", quantity: "", unit_price: "" });
      await loadData();
    } catch (error) {
      alert(error instanceof Error ? error.message : "Purchase Order could not be saved.");
    }
  }

  async function approvePurchaseOrder(poId: number) {
    if (!window.confirm("Approve this Purchase Order for delivery receiving?")) return;
    try {
      await sendJson(`/food-costing/purchase-orders/${poId}/approval`, "PATCH", {
        property_code: DEFAULT_PROPERTY_CODE,
        approved_by: actorByRole[role] || "F&B Manager",
        action: "approve",
      });
      await loadData();
    } catch (error) {
      alert(error instanceof Error ? error.message : "Purchase Order approval failed.");
    }
  }

  async function createGoodsReceived(e: React.FormEvent) {
    e.preventDefault();
    const po = purchaseOrders.find((item) => String(item.id) === newGrn.purchase_order_id);
    if (!po || Number(newGrn.quantity_received) < 0 || Number(newGrn.rejected_qty) < 0) {
      alert("Choose an approved Purchase Order and enter accepted/rejected quantities.");
      return;
    }
    if (!window.confirm("Post this Goods Receiving Note and update Main Store Inventory?")) return;
    try {
      await sendJson("/food-costing/goods-received", "POST", {
        property_code: DEFAULT_PROPERTY_CODE,
        purchase_order_id: po.id,
        supplier_name: po.supplier_name,
        ingredient_name: po.ingredient_name,
        ordered_qty: Number(po.ordered_qty ?? po.quantity),
        quantity_received: Number(newGrn.quantity_received),
        rejected_qty: Number(newGrn.rejected_qty || 0),
        unit_cost: newGrn.unit_cost ? Number(newGrn.unit_cost) : Number(po.unit_cost || po.unit_price || 0),
        received_by: newGrn.received_by,
        invoice_number: newGrn.invoice_number || undefined,
      });
      setNewGrn({ purchase_order_id: "", quantity_received: "", rejected_qty: "0", unit_cost: "", received_by: "Storekeeper", invoice_number: "" });
      await loadData();
    } catch (error) {
      alert(error instanceof Error ? error.message : "Goods Receiving Note could not be posted.");
    }
  }

  async function createStoreRequisition(e: React.FormEvent) {
    e.preventDefault();
    if (!newRequisition.ingredient_name || Number(newRequisition.requested_qty) <= 0) {
      alert("Item and requested quantity are required.");
      return;
    }
    try {
      await sendJson("/food-costing/kitchen-requisitions", "POST", {
        property_code: DEFAULT_PROPERTY_CODE,
        ...newRequisition,
        requested_qty: Number(newRequisition.requested_qty),
      });
      setNewRequisition({ ...newRequisition, requested_qty: "", notes: "" });
      await loadData();
    } catch (error) {
      alert(error instanceof Error ? error.message : "Store Requisition could not be saved.");
    }
  }

  async function issueStoreRequisition(e: React.FormEvent) {
    e.preventDefault();
    if (!issueForm.requisition_id || Number(issueForm.issued_qty) <= 0) {
      alert("Choose a Store Requisition and enter the issued quantity.");
      return;
    }
    if (!window.confirm("Issue these items and deduct them from Main Store Inventory?")) return;
    try {
      await sendJson(`/food-costing/kitchen-requisitions/${issueForm.requisition_id}/issue`, "PATCH", {
        property_code: DEFAULT_PROPERTY_CODE,
        issued_qty: Number(issueForm.issued_qty),
        issued_by: issueForm.issued_by,
        manager_override: issueForm.manager_override,
        override_by: issueForm.override_by || undefined,
      });
      setIssueForm({ requisition_id: "", issued_qty: "", issued_by: "Storekeeper", manager_override: false, override_by: "" });
      await loadData();
    } catch (error) {
      alert(error instanceof Error ? error.message : "Store Requisition could not be issued.");
    }
  }

  async function approveStoreRequisition(requisitionId: number) {
    if (!window.confirm("Approve this Store Requisition for Main Store issue?")) return;
    try {
      await sendJson(`/food-costing/kitchen-requisitions/${requisitionId}/approval`, "PATCH", {
        property_code: DEFAULT_PROPERTY_CODE,
        approved_by: actorByRole[role] || "Executive Chef",
        action: "approve",
      });
      await loadData();
    } catch (error) {
      alert(error instanceof Error ? error.message : "Store Requisition approval failed.");
    }
  }

  async function createWasteRecord(e: React.FormEvent) {
    e.preventDefault();
    if (!newWaste.reason || Number(newWaste.quantity) <= 0) {
      alert("Waste quantity and reason are required.");
      return;
    }
    if (!window.confirm("Record this waste for manager approval?")) return;
    try {
      await sendJson("/food-costing/wastage", "POST", {
        property_code: DEFAULT_PROPERTY_CODE,
        ...newWaste,
        quantity: Number(newWaste.quantity),
      });
      setNewWaste({ ...newWaste, quantity: "", reason: "" });
      await loadData();
    } catch (error) {
      alert(error instanceof Error ? error.message : "Waste record could not be saved.");
    }
  }

  async function createStockCount(e: React.FormEvent) {
    e.preventDefault();
    if (!newStockCount.ingredient_name || newStockCount.system_qty === "" || newStockCount.physical_qty === "") {
      alert("Item, system quantity, and physical quantity are required.");
      return;
    }
    try {
      await sendJson("/food-costing/stock-counts", "POST", {
        property_code: DEFAULT_PROPERTY_CODE,
        ...newStockCount,
        system_qty: Number(newStockCount.system_qty),
        physical_qty: Number(newStockCount.physical_qty),
      });
      setNewStockCount({ ...newStockCount, system_qty: "", physical_qty: "", notes: "" });
      await loadData();
    } catch (error) {
      alert(error instanceof Error ? error.message : "Stock count could not be saved.");
    }
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

  const reportWindow = useMemo(
    () => reportRange(reportPeriod, reportDate),
    [reportPeriod, reportDate]
  );

  useEffect(() => {
    loadReportApproval(reportPeriod, reportWindow);
  }, [reportPeriod, reportWindow.start, reportWindow.end]);

  const reportSales = useMemo(
    () =>
      posSales.filter((sale) => {
        const saleDate = String(sale.business_date || "");
        return saleDate >= reportWindow.start && saleDate <= reportWindow.end;
      }),
    [posSales, reportWindow]
  );

  const reportRevenue = useMemo(
    () => reportSales.reduce((sum, sale) => sum + Number(sale.total_revenue || 0), 0),
    [reportSales]
  );

  const reportTax = useMemo(
    () => reportSales.reduce((sum, sale) => sum + Number(sale.tax_amount || 0), 0),
    [reportSales]
  );

  const reportService = useMemo(
    () => reportSales.reduce((sum, sale) => sum + Number(sale.service_charge_amount || 0), 0),
    [reportSales]
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
  const reportFoodCostPercent = reportRevenue > 0 ? (actualCost / reportRevenue) * 100 : 0;

  const lowStock = useMemo(
    () =>
      stockBalances.filter((stock) => {
        const ingredient = ingredients.find((item) => item.name === stock.ingredient);
        const reorderLevel = Number(ingredient?.reorder_level || 0);
        return reorderLevel > 0 && stock.closing <= reorderLevel;
      }),
    [stockBalances, ingredients]
  );

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

  const mainStoreLedger = useMemo(() => {
    return stockBalances.map((stock, index) => {
      const ingredient = ingredients.find((item) => item.name === stock.ingredient);
      const itemMovements = inventoryMovements.filter((movement) => movement.ingredient_name === stock.ingredient);
      const latestPurchase = itemMovements.find((movement) => movement.movement_type === "PURCHASE_RECEIVED");
      const latestIssue = itemMovements.find((movement) => movement.movement_type === "KITCHEN_ISSUE");
      const requisition = kitchenRequisitions.find((req) => req.ingredient_name === stock.ingredient);
      const openingBalance = itemMovements
        .filter((movement) => movement.movement_type === "OPENING")
        .reduce((sum, movement) => sum + Number(movement.quantity || 0), 0);
      const purchasedQuantity = itemMovements
        .filter((movement) => movement.movement_type === "PURCHASE_RECEIVED")
        .reduce((sum, movement) => sum + Number(movement.quantity || 0), 0);
      const issuedQuantity = stock.manualIssue + stock.posIssue + stock.wastage;
      const totalBalance = openingBalance + purchasedQuantity;
      const unitPrice = Number(ingredient?.average_cost || ingredient?.cost_per_unit || 0);
      const reorderLevel = Number(ingredient?.reorder_level || 0);
      const isExpired = ingredient?.expiry_date ? new Date(`${ingredient.expiry_date}T00:00:00`) < new Date(new Date().toDateString()) : false;
      const status =
        isExpired ? "Expired" :
        stock.closing < 0 ? "Negative stock" :
        !unitPrice ? "Missing unit price" :
        reorderLevel && stock.closing <= reorderLevel ? "Low stock" :
        "OK";

      return {
        serialNo: index + 1,
        date: String(latestPurchase?.reference || latestIssue?.reference || "-"),
        itemCode: ingredient ? `FNB-${String(ingredient.id).padStart(4, "0")}` : "-",
        itemName: stock.ingredient,
        category: ingredient?.category || "Food",
        unit: stock.unit,
        openingBalance,
        purchasedQuantity,
        totalBalance,
        issuedQuantity,
        balanceOnHand: stock.closing,
        unitPrice,
        totalValue: stock.closing * unitPrice,
        supplier: ingredient?.supplier_name || latestPurchase?.created_by || "-",
        grnNumber: latestPurchase?.reference || "-",
        storeRequisitionNumber: latestIssue?.reference || "-",
        departmentIssuedTo: requisition?.outlet_name || "-",
        minimumStockLevel: reorderLevel,
        reorderLevel,
        status,
        remarks: latestIssue?.notes || latestPurchase?.notes || "-",
      };
    });
  }, [stockBalances, ingredients, inventoryMovements, kitchenRequisitions]);

  const selectedRecipe = recipes.find((recipe) => recipe.id === Number(selectedRecipeId));

  const selectedRecipeTotalCost = selectedRecipe ? Number(selectedRecipe.total_cost || 0) : 0;
  const selectedRecipeSellingPrice = selectedRecipe ? Number(selectedRecipe.selling_price || 0) : 0;
  const selectedRecipeFoodCost =
    selectedRecipeSellingPrice > 0
      ? (selectedRecipeTotalCost / selectedRecipeSellingPrice) * 100
      : 0;

  const workflows: {
    id: string;
    label: string;
    detail: string;
    icon: LucideIcon;
    roles: string[];
  }[] = [
    {
      id: "ingredients",
      label: "Ingredients",
      detail: "Master and cost",
      icon: PackageSearch,
      roles: ["chef", "executive_chef", "storekeeper", "fb_controller", "fnb_manager", "admin"],
    },
    {
      id: "suppliers",
      label: "Suppliers",
      detail: "Vendor control",
      icon: Truck,
      roles: ["purchasing_manager", "fb_controller", "fnb_manager", "finance_manager", "admin"],
    },
    {
      id: "purchase-orders",
      label: "Purchase Orders",
      detail: "Order approval",
      icon: FileCheck2,
      roles: ["purchasing_manager", "fb_controller", "fnb_manager", "admin"],
    },
    {
      id: "receiving",
      label: "Receiving",
      detail: "GRN and invoice",
      icon: PackagePlus,
      roles: ["storekeeper", "purchasing_manager", "fb_controller", "fnb_manager", "admin"],
    },
    {
      id: "store-inventory",
      label: "Store Inventory",
      detail: "Stock ledger",
      icon: Boxes,
      roles: ["storekeeper", "fb_controller", "fnb_manager", "finance_manager", "admin"],
    },
    {
      id: "kitchen-requisition",
      label: "Kitchen Requisition",
      detail: "Issues to kitchen",
      icon: PackageMinus,
      roles: ["chef", "executive_chef", "storekeeper", "fb_controller", "fnb_manager", "admin"],
    },
    {
      id: "recipes",
      label: "Recipes",
      detail: "Portion costing",
      icon: ChefHat,
      roles: ["chef", "executive_chef", "fb_controller", "fnb_manager", "admin"],
    },
    {
      id: "menu-engineering",
      label: "Menu Engineering",
      detail: "Profit mix",
      icon: BarChart3,
      roles: ["general_manager", "executive_chef", "chef", "fb_controller", "fnb_manager", "finance_manager", "admin"],
    },
    {
      id: "pos-sales",
      label: "POS Sales",
      detail: "Outlet revenue",
      icon: WalletCards,
      roles: ["fb_controller", "fnb_manager", "finance_manager", "admin"],
    },
    {
      id: "wastage-spoilage",
      label: "Wastage / Spoilage",
      detail: "Approved waste",
      icon: AlertTriangle,
      roles: ["chef", "executive_chef", "storekeeper", "fb_controller", "fnb_manager", "admin"],
    },
    {
      id: "stock-count",
      label: "Stock Count",
      detail: "Physical count",
      icon: ClipboardList,
      roles: ["storekeeper", "fb_controller", "fnb_manager", "finance_manager", "admin"],
    },
    {
      id: "variance-report",
      label: "Variance Report",
      detail: "Actual vs theoretical",
      icon: ScrollText,
      roles: ["general_manager", "fb_controller", "fnb_manager", "finance_manager", "admin"],
    },
    {
      id: "fnb-dashboard",
      label: "F&B Dashboard",
      detail: "Revenue, cost, risk",
      icon: LayoutDashboard,
      roles: ["general_manager", "fb_controller", "fnb_manager", "admin"],
    },
  ];

  const visibleWorkflows = workflows.filter((w) => w.roles.includes(role));
  const activeWorkflowMeta =
    visibleWorkflows.find((workflow) => workflow.id === activeWorkflow) ||
    workflows.find((workflow) => workflow.id === activeWorkflow) ||
    workflows[0];
  const filterText = filters.search.trim().toLowerCase();
  const matchesText = (values: unknown[]) =>
    !filterText || values.some((value) => String(value ?? "").toLowerCase().includes(filterText));
  const matchesStatus = (status?: string | null) =>
    !filters.status || String(status || "").toLowerCase() === filters.status.toLowerCase();
  const filteredPurchaseOrders = purchaseOrders.filter(
    (po) =>
      matchesText([po.id, po.ingredient_name, po.supplier_name, po.status, po.approval_status]) &&
      (!filters.supplier || po.supplier_name === filters.supplier) &&
      (!filters.item || po.ingredient_name === filters.item) &&
      matchesStatus(po.approval_status || po.status)
  );
  const filteredGoodsReceived = goodsReceived.filter(
    (grn) =>
      matchesText([grn.id, grn.purchase_order_id, grn.ingredient_name, grn.supplier_name, grn.invoice_number, grn.received_by]) &&
      (!filters.supplier || grn.supplier_name === filters.supplier) &&
      (!filters.item || grn.ingredient_name === filters.item) &&
      matchesStatus(grn.approval_status || "received")
  );
  const filteredInventoryMovements = inventoryMovements.filter(
    (movement) =>
      matchesText([movement.ingredient_name, movement.movement_type, movement.reference, movement.notes, movement.created_by]) &&
      (!filters.item || movement.ingredient_name === filters.item) &&
      matchesStatus(movement.movement_type)
  );
  const filteredMainStoreLedger = mainStoreLedger.filter(
    (row) =>
      matchesText([row.itemCode, row.itemName, row.category, row.supplier, row.grnNumber, row.storeRequisitionNumber, row.departmentIssuedTo, row.status, row.remarks]) &&
      (!filters.item || row.itemName === filters.item) &&
      (!filters.supplier || row.supplier === filters.supplier) &&
      (!filters.department || row.departmentIssuedTo === filters.department) &&
      (!filters.category || row.category === filters.category) &&
      matchesStatus(row.status)
  );
  const filteredKitchenRequisitions = kitchenRequisitions.filter(
    (req) =>
      matchesText([req.id, req.ingredient_name, req.outlet_name, req.requested_by, req.issued_by, req.status]) &&
      (!filters.department || req.outlet_name === filters.department) &&
      (!filters.item || req.ingredient_name === filters.item) &&
      matchesStatus(req.status)
  );
  const filteredRecipes = recipes.filter(
    (recipe) =>
      matchesText([recipe.name, recipe.outlet_name, recipe.approval_status]) &&
      (!filters.department || recipe.outlet_name === filters.department) &&
      matchesStatus(recipe.approval_status || "draft")
  );
  const alaCarteRecipes = filteredRecipes.filter((recipe) => alaCarteRecipeMeta[recipe.name]);
  const recipeProfitStatus = (recipe: Recipe) => {
    const sellingPrice = Number(recipe.selling_price || 0);
    const totalCost = Number(recipe.total_cost || 0);
    const foodCostPercent = Number(recipe.food_cost_percentage || 0);
    const targetPercent = Number(recipe.target_cost_percentage || 35);
    if (sellingPrice <= 0 || sellingPrice - totalCost <= 0) return "loss";
    if (foodCostPercent > targetPercent) return "warning";
    return "profitable";
  };
  const filteredIngredients = ingredients.filter(
    (ingredient) =>
      matchesText([ingredient.name, ingredient.category, ingredient.unit, ingredient.supplier_name, ingredient.storage_location]) &&
      (!filters.supplier || ingredient.supplier_name === filters.supplier) &&
      (!filters.item || ingredient.name === filters.item)
  );
  const metricCards = [
    {
      id: "revenue",
      label: "POS Revenue",
      value: money(totalRevenue),
      hint: "Sales captured",
      icon: WalletCards,
      tone: "dark",
    },
    {
      id: "food-cost",
      label: "Avg Food Cost",
      value: `${avgFoodCost.toFixed(2)}%`,
      hint: avgFoodCost > 35 ? "Above target" : "Within range",
      icon: BarChart3,
      tone: avgFoodCost > 35 ? "danger" : "success",
    },
    {
      id: "actual-cost",
      label: "Actual Cost",
      value: money(actualCost),
      hint: "Issues and wastage",
      icon: Boxes,
      tone: "neutral",
    },
    {
      id: "variance",
      label: "Variance",
      value: money(variance),
      hint: variance > 0 ? "Needs review" : "Favorable",
      icon: AlertTriangle,
      tone: variance > 0 ? "danger" : "success",
    },
    {
      id: "stock",
      label: "Low Stock",
      value: String(lowStock.length),
      hint: "Reorder focus",
      icon: ClipboardList,
      tone: lowStock.length ? "warning" : "success",
    },
  ];
  const activeMetricCard = metricCards.find((metric) => metric.id === activeMetric) || metricCards[0];
  const canSubmitReport = ["chef", "executive_chef", "fb_controller", "fnb_manager", "admin"].includes(role);
  const canFinanceReview = ["finance_manager", "admin"].includes(role);
  const canFnbApprove = ["fb_controller", "fnb_manager", "admin"].includes(role);
  const canGmLock = ["admin", "general_manager"].includes(role);
  const canOverride = role === "admin";
  const approvalStatusLabel = reportApproval.status.replace(/_/g, " ");

  function exportSpreadsheet() {
    const stockRows = mainStoreLedger.map((row) => [
      row.serialNo,
      row.date,
      row.itemCode,
      row.itemName,
      row.category,
      row.unit,
      row.openingBalance.toFixed(3),
      row.purchasedQuantity.toFixed(3),
      row.totalBalance.toFixed(3),
      row.issuedQuantity.toFixed(3),
      row.balanceOnHand.toFixed(3),
      row.unitPrice.toFixed(2),
      row.totalValue.toFixed(2),
      row.supplier,
      row.grnNumber,
      row.storeRequisitionNumber,
      row.departmentIssuedTo,
      row.minimumStockLevel,
      row.reorderLevel,
      row.status,
      row.remarks,
    ]);
    const sections = [
      csvSection("F&B Report Summary", ["Property", "Period", "Start Date", "End Date", "Status", "POS Sales", "Service Charge", "VAT / Tax", "Actual Cost", "Theoretical Cost", "Variance", "Wastage"], [[
        DEFAULT_PROPERTY_CODE,
        reportWindow.label,
        reportWindow.start,
        reportWindow.end,
        approvalStatusLabel,
        reportRevenue.toFixed(2),
        reportService.toFixed(2),
        reportTax.toFixed(2),
        actualCost.toFixed(2),
        theoreticalCost.toFixed(2),
        variance.toFixed(2),
        wastageCost.toFixed(2),
      ]]),
      csvSection("F&B Dashboard", ["Metric", "Value", "Notes"], [
        ["POS Revenue", reportRevenue.toFixed(2), `${reportWindow.label} report window`],
        ["Service Charge", reportService.toFixed(2), "Posted from POS sales"],
        ["VAT / Tax", reportTax.toFixed(2), "Posted from POS sales"],
        ["Actual Cost", actualCost.toFixed(2), "Kitchen issues plus wastage"],
        ["Theoretical Cost", theoreticalCost.toFixed(2), "Recipe cost multiplied by POS quantity"],
        ["Food Cost %", `${reportFoodCostPercent.toFixed(2)}%`, "Actual cost divided by revenue"],
        ["Variance", variance.toFixed(2), "Actual minus theoretical"],
        ["Low Stock Items", lowStock.length, "Closing stock at or below PMS threshold"],
        ["Open Alerts", alerts.length + lowStock.length, "System alerts plus low stock"],
      ]),
      csvSection("Ingredients", ["ID", "Name", "Category", "Unit", "Last Purchase Price", "Average Cost", "Reorder Level", "Expiry Date", "Storage Location", "Supplier"], ingredients.map((item) => [
        item.id,
        item.name,
        item.category,
        item.unit,
        item.last_purchase_price || item.purchase_price || item.cost_per_unit,
        item.average_cost || item.cost_per_unit,
        item.reorder_level,
        item.expiry_date,
        item.storage_location,
        item.supplier_name,
      ])),
      csvSection("Suppliers", ["ID", "Supplier", "Contact", "Phone", "Email", "Payment Terms", "Status"], suppliers.map((supplier) => [
        supplier.id,
        supplier.supplier_name,
        supplier.contact_name,
        supplier.phone,
        supplier.email,
        supplier.payment_terms,
        supplier.is_active === false ? "Inactive" : "Active",
      ])),
      csvSection("Purchase Orders", ["PO", "Ingredient", "Supplier", "Ordered", "Received", "Rejected", "Unit Price", "Total", "Invoice", "Received By", "Approval", "Status"], purchaseOrders.map((po) => [
        po.id,
        po.ingredient_name,
        po.supplier_name,
        po.ordered_qty ?? po.quantity,
        po.received_qty ?? 0,
        po.rejected_qty ?? 0,
        po.unit_price,
        po.total_amount,
        po.invoice_number,
        po.received_by,
        po.approval_status,
        po.status,
      ])),
      csvSection("Receiving", ["GRN", "PO", "Ingredient", "Supplier", "Ordered", "Received", "Rejected", "Unit Cost", "Invoice", "Received By", "Approval"], goodsReceived.map((grn) => [
        grn.id,
        grn.purchase_order_id,
        grn.ingredient_name,
        grn.supplier_name,
        grn.ordered_qty,
        grn.quantity_received,
        grn.rejected_qty,
        grn.unit_cost,
        grn.invoice_number,
        grn.received_by,
        grn.approval_status,
      ])),
      csvSection("Main Store Ledger", ["Serial No", "Date", "Item Code", "Item Name", "Category", "Unit", "Forward Balance / Opening Balance", "Purchased Quantity", "Total Balance", "Issued Quantity", "Balance on Hand", "Unit Price", "Total Value", "Supplier", "GRN Number", "Store Requisition Number", "Department Issued To", "Minimum Stock Level", "Reorder Level", "Status", "Remarks"], stockRows),
      csvSection("Inventory Movements", ["ID", "Ingredient", "Type", "Quantity", "Unit", "Unit Cost", "Stock Value", "Reference", "Notes", "Created By"], inventoryMovements.map((movement) => [
        movement.id,
        movement.ingredient_name,
        movement.movement_type,
        movement.quantity,
        movement.unit,
        movement.unit_cost,
        movement.stock_value,
        movement.reference,
        movement.notes,
        movement.created_by,
      ])),
      csvSection("Kitchen Requisition", ["ID", "Ingredient", "Quantity", "Unit", "Unit Cost", "Stock Value", "Reference", "Notes", "Issued By"], inventoryMovements.filter((movement) => movement.movement_type === "KITCHEN_ISSUE").map((movement) => [
        movement.id,
        movement.ingredient_name,
        movement.quantity,
        movement.unit,
        movement.unit_cost,
        movement.stock_value,
        movement.reference,
        movement.notes,
        movement.created_by,
      ])),
      csvSection("Recipes", ["ID", "Menu Item", "Outlet", "Selling Price", "Recipe Cost", "Food Cost %", "Target %", "Profit Margin", "Approval"], recipes.map((recipe) => [
        recipe.id,
        recipe.name,
        recipe.outlet_name,
        recipe.selling_price,
        recipe.total_cost,
        recipe.food_cost_percentage,
        recipe.target_cost_percentage || 35,
        Number(recipe.selling_price || 0) - Number(recipe.total_cost || 0),
        recipe.approval_status,
      ])),
      csvSection("À La Carte Menu Costing", ["Menu Item", "Menu Type", "Department", "Portion", "Selling Price", "Recipe Cost", "Cost Per Portion", "Food Cost %", "Gross Profit", "Status"], recipes.filter((recipe) => alaCarteRecipeMeta[recipe.name]).map((recipe) => [
        recipe.name,
        alaCarteRecipeMeta[recipe.name].menuType,
        recipe.outlet_name,
        alaCarteRecipeMeta[recipe.name].portion,
        recipe.selling_price,
        recipe.total_cost,
        recipe.total_cost,
        recipe.food_cost_percentage,
        Number(recipe.selling_price || 0) - Number(recipe.total_cost || 0),
        recipeProfitStatus(recipe),
      ])),
      csvSection("Menu Engineering", ["Menu Item", "Quantity Sold", "Revenue", "Expected Cost", "Gross Profit", "Food Cost %", "Class"], posProfitability.map((item) => {
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
          item.revenue.toFixed(2),
          item.expectedCost.toFixed(2),
          item.grossProfit.toFixed(2),
          `${item.foodCostPercent.toFixed(2)}%`,
          classification,
        ];
      })),
      csvSection("POS Sales", ["ID", "Business Date", "Outlet", "Menu Item", "Quantity Sold", "Selling Price", "Sales Amount", "Service Charge", "VAT / Tax", "Payment Method", "Room Charge Booking ID"], posSales.map((sale) => [
        sale.id,
        sale.business_date,
        sale.outlet_name,
        sale.menu_item_name,
        sale.quantity_sold,
        sale.selling_price,
        sale.total_revenue,
        sale.service_charge_amount,
        sale.tax_amount,
        sale.payment_method,
        sale.room_charge_booking_id,
      ])),
      csvSection("Wastage / Spoilage", ["ID", "Ingredient", "Quantity", "Unit", "Cost", "Reason", "Approved / Recorded By"], inventoryMovements.filter((movement) => movement.movement_type === "WASTAGE").map((movement) => [
        movement.id,
        movement.ingredient_name,
        movement.quantity,
        movement.unit,
        movement.stock_value || Number(movement.quantity || 0) * Number(movement.unit_cost || 0),
        movement.notes,
        movement.created_by,
      ])),
      csvSection("Variance Report", ["Ingredient", "System Qty", "Physical Qty", "Variance Qty", "Variance Value", "Status"], varianceRows.map((row) => [
        row.ingredient,
        `${row.closing.toFixed(3)} ${row.unit}`,
        `${row.physical.toFixed(3)} ${row.unit}`,
        `${row.varianceQty.toFixed(3)} ${row.unit}`,
        row.value.toFixed(2),
        row.status,
      ])),
      csvSection("Alerts", ["ID", "Type", "Severity", "Message"], alerts.map((alert) => [
        alert.id,
        alert.alert_type,
        alert.severity,
        alert.message,
      ])),
      csvSection("Approval Workflow", ["Status", "Prepared By", "Prepared At", "Finance Reviewed By", "Finance Reviewed At", "F&B Approved By", "F&B Approved At", "GM Approved By", "GM Approved At", "Locked At"], [[
        approvalStatusLabel,
        reportApproval.prepared_by,
        reportApproval.prepared_at,
        reportApproval.finance_reviewed_by,
        reportApproval.finance_reviewed_at,
        reportApproval.fnb_approved_by,
        reportApproval.fnb_approved_at,
        reportApproval.gm_approved_by,
        reportApproval.gm_approved_at,
        reportApproval.locked_at,
      ]]),
    ];
    const csv = `\uFEFF${sections.join("\n")}`;
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `guzo-fnb-cost-control-${reportPeriod}-${reportWindow.start}-to-${reportWindow.end}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }


  return (
    <div className="fnb-page min-h-screen p-4 text-slate-900 sm:p-6">
      <div className="fnb-command mb-4 rounded-lg border border-amber-200 bg-[#fffaf0] p-5 text-slate-900 shadow-sm sm:p-6">
        <div className="fnb-command-header">
          <div className="fnb-command-title">
            <div className="fnb-command-icon bg-amber-100 text-amber-800">
              <Utensils aria-hidden="true" size={24} />
            </div>
            <div>
              <p className="fnb-kicker text-amber-700">Guzo F&B Control</p>
              <h1>Food & Beverage Control Center</h1>
              <p className="text-slate-600">
                Interactive purchasing, inventory, recipe costing, POS variance, and finance reporting.
              </p>
            </div>
          </div>

          <div className="fnb-command-actions print:hidden">
            <select
              className="rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm font-semibold text-slate-900"
              value={reportPeriod}
              onChange={(e) => setReportPeriod(e.target.value as ReportPeriod)}
              aria-label="Report period"
            >
              <option value="daily">Daily Report</option>
              <option value="weekly">Weekly Report</option>
              <option value="monthly">Monthly Report</option>
            </select>

            <input
              className="rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm font-semibold text-slate-900"
              type="date"
              value={reportDate}
              onChange={(e) => setReportDate(e.target.value)}
              aria-label="Report date"
            />

            <select
              className="rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm font-semibold text-slate-900"
              value={role}
              onChange={(e) => {
                setRole(e.target.value);
                setActiveWorkflow("fnb-dashboard");
              }}
            >
              <option value="general_manager">General Manager</option>
              <option value="storekeeper">Storekeeper</option>
              <option value="chef">Chef</option>
              <option value="executive_chef">Executive Chef</option>
              <option value="fnb_manager">F&B Manager</option>
              <option value="fb_controller">F&B Controller</option>
              <option value="purchasing_manager">Purchasing Manager</option>
              <option value="finance_manager">Finance Manager</option>
              <option value="admin">Admin</option>
            </select>

            <button
              onClick={loadData}
              className="fnb-icon-btn rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white"
            >
              <RefreshCw aria-hidden="true" size={16} />
              <span>{loading ? "Refreshing..." : "Refresh"}</span>
            </button>

            <button
              onClick={() => window.print()}
              className="fnb-icon-btn rounded-lg bg-amber-600 px-4 py-2 text-sm font-bold text-white"
            >
              <Download aria-hidden="true" size={16} />
                <span>Print / PDF</span>
              </button>

            <button
              onClick={exportSpreadsheet}
              className="fnb-icon-btn rounded-lg bg-emerald-700 px-4 py-2 text-sm font-bold text-white"
            >
              <Download aria-hidden="true" size={16} />
              <span>Spreadsheet</span>
            </button>
          </div>
        </div>

        <div className="fnb-command-strip">
          <div>
            <span>Role</span>
            <strong>{role.replace("_", " ")}</strong>
          </div>
          <div>
            <span>Recipes</span>
            <strong>{recipes.length}</strong>
          </div>
          <div>
            <span>Inventory Items</span>
            <strong>{stockBalances.length}</strong>
          </div>
          <div>
            <span>Open Alerts</span>
            <strong>{alerts.length + lowStock.length}</strong>
          </div>
          <div>
            <span>Report</span>
            <strong>{reportWindow.label}</strong>
          </div>
          <div>
            <span>Status</span>
            <strong>{approvalStatusLabel}</strong>
          </div>
        </div>

        <section className="mt-4 grid gap-3 rounded-lg border border-amber-200 bg-white p-4 print:hidden md:grid-cols-3 xl:grid-cols-7">
          <input
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
            placeholder="Search item, supplier, status"
            value={filters.search}
            onChange={(event) => setFilters({ ...filters, search: event.target.value })}
          />
          <input
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
            type="date"
            value={filters.date}
            onChange={(event) => setFilters({ ...filters, date: event.target.value })}
          />
          <select className="rounded-lg border border-slate-200 px-3 py-2 text-sm" value={filters.department} onChange={(event) => setFilters({ ...filters, department: event.target.value })}>
            <option value="">All departments</option>
            {hotelDepartments.map((department) => <option key={department} value={department}>{department}</option>)}
          </select>
          <select className="rounded-lg border border-slate-200 px-3 py-2 text-sm" value={filters.supplier} onChange={(event) => setFilters({ ...filters, supplier: event.target.value })}>
            <option value="">All suppliers</option>
            {[...new Set([...suppliers.map((s) => s.supplier_name), ...ingredients.map((i) => i.supplier_name || "").filter(Boolean)])].map((supplier) => <option key={supplier} value={supplier}>{supplier}</option>)}
          </select>
          <select className="rounded-lg border border-slate-200 px-3 py-2 text-sm" value={filters.category} onChange={(event) => setFilters({ ...filters, category: event.target.value })}>
            <option value="">All categories</option>
            {[...new Set(ingredients.map((item) => item.category || "Food"))].map((category) => <option key={category} value={category}>{category}</option>)}
          </select>
          <select className="rounded-lg border border-slate-200 px-3 py-2 text-sm" value={filters.item} onChange={(event) => setFilters({ ...filters, item: event.target.value })}>
            <option value="">All items</option>
            {[...new Set([...ethiopianItems, ...ingredients.map((item) => item.name)])].map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
          <select className="rounded-lg border border-slate-200 px-3 py-2 text-sm" value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
            <option value="">All status</option>
            {["OK", "Low stock", "Negative stock", "Expired", "Missing unit price", "pending", "approved", "received", "requested", "issued", "WASTAGE", "KITCHEN_ISSUE", "draft"].map((status) => <option key={status} value={status}>{status.replace(/_/g, " ")}</option>)}
          </select>
        </section>

        <section className="fnb-approval-panel mt-4 rounded-lg border border-amber-200 bg-white p-4 print:hidden">
          <div>
            <p className="text-xs font-black uppercase tracking-wide text-amber-700">Report Approval Workflow</p>
            <h2 className="mt-1 text-lg font-black capitalize text-slate-900">{approvalStatusLabel}</h2>
            <p className="mt-1 text-sm font-semibold text-slate-600">
              {reportWindow.label} F&B Cost Control Report | {reportWindow.start} to {reportWindow.end}
            </p>
          </div>

          <div className="fnb-approval-timeline">
            <span>Prepared: {reportApproval.prepared_by || "Pending"}</span>
            <span>Finance: {reportApproval.finance_reviewed_by || "Pending"}</span>
            <span>F&B: {reportApproval.fnb_approved_by || "Pending"}</span>
            <span>GM: {reportApproval.gm_approved_by || "Pending"}</span>
          </div>

          <div className="fnb-approval-actions">
            <button
              type="button"
              disabled={!canSubmitReport || approvalLoading || reportApproval.status === "locked"}
              onClick={() => updateReportApproval("submit")}
            >
              Submit Report
            </button>
            <button
              type="button"
              disabled={!canFinanceReview || approvalLoading || !["submitted", "finance_reviewed"].includes(reportApproval.status) || reportApproval.status === "locked"}
              onClick={() => updateReportApproval("finance_review")}
            >
              Finance Review
            </button>
            <button
              type="button"
              disabled={!canFnbApprove || approvalLoading || !["finance_reviewed", "fnb_manager_approved"].includes(reportApproval.status) || reportApproval.status === "locked"}
              onClick={() => updateReportApproval("fnb_approve")}
            >
              F&B Manager Approval
            </button>
            <button
              type="button"
              disabled={!canGmLock || approvalLoading || reportApproval.status !== "fnb_manager_approved"}
              onClick={() => updateReportApproval("gm_lock")}
            >
              GM Approval / Lock
            </button>
            {canOverride && (
              <button
                type="button"
                disabled={approvalLoading || reportApproval.status !== "locked"}
                onClick={() => updateReportApproval("override")}
              >
                Admin Override
              </button>
            )}
          </div>
        </section>
      </div>

      <section className="fnb-print-report hidden">
        <header className="fnb-print-header">
          <div>
            <p>Guzo PMS Ethiopia Hotel Operation</p>
            <h1>Food & Beverage Cost Control Report</h1>
            <span>Dream Big Hotel | Property {DEFAULT_PROPERTY_CODE}</span>
          </div>
          <div>
            <strong>{reportWindow.label}</strong>
            <span>{reportWindow.start} to {reportWindow.end}</span>
            <span>Generated {todayIso()}</span>
            <span>Status: {approvalStatusLabel}</span>
          </div>
        </header>

        <div className="fnb-print-kpis">
          <div><span>POS Sales</span><strong>{money(reportRevenue)}</strong></div>
          <div><span>Service Charge</span><strong>{money(reportService)}</strong></div>
          <div><span>VAT / Tax</span><strong>{money(reportTax)}</strong></div>
          <div><span>Actual Cost</span><strong>{money(actualCost)}</strong></div>
          <div><span>Theoretical Cost</span><strong>{money(theoreticalCost)}</strong></div>
          <div><span>Food Cost %</span><strong>{reportFoodCostPercent.toFixed(2)}%</strong></div>
          <div><span>Variance</span><strong>{money(variance)}</strong></div>
          <div><span>Wastage</span><strong>{money(wastageCost)}</strong></div>
        </div>

        <section className="fnb-print-section">
          <h2>Outlet Sales Summary</h2>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Outlet</th>
                <th>Menu Item</th>
                <th>Qty</th>
                <th>Sales</th>
                <th>Service</th>
                <th>VAT</th>
                <th>Payment</th>
              </tr>
            </thead>
            <tbody>
              {reportSales.length === 0 ? (
                <tr><td colSpan={8}>No POS sales recorded for this report period.</td></tr>
              ) : (
                reportSales.map((sale) => (
                  <tr key={sale.id}>
                    <td>{sale.business_date}</td>
                    <td>{sale.outlet_name}</td>
                    <td>{sale.menu_item_name}</td>
                    <td>{Number(sale.quantity_sold || 0).toFixed(2)}</td>
                    <td>{money(Number(sale.total_revenue || 0))}</td>
                    <td>{money(Number(sale.service_charge_amount || 0))}</td>
                    <td>{money(Number(sale.tax_amount || 0))}</td>
                    <td>{sale.payment_method || "cash"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </section>

        <section className="fnb-print-section">
          <h2>Recipe Cost and Menu Engineering</h2>
          <table>
            <thead>
              <tr>
                <th>Menu Item</th>
                <th>Selling Price</th>
                <th>Recipe Cost</th>
                <th>Food Cost %</th>
                <th>Target %</th>
                <th>Gross Margin</th>
              </tr>
            </thead>
            <tbody>
              {recipes.map((recipe) => (
                <tr key={recipe.id}>
                  <td>{recipe.name}</td>
                  <td>{money(Number(recipe.selling_price || 0))}</td>
                  <td>{money(Number(recipe.total_cost || 0))}</td>
                  <td>{Number(recipe.food_cost_percentage || 0).toFixed(2)}%</td>
                  <td>{Number(recipe.target_cost_percentage || 35).toFixed(2)}%</td>
                  <td>{money(Number(recipe.selling_price || 0) - Number(recipe.total_cost || 0))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="fnb-print-section">
          <h2>Inventory, Low Stock, and Wastage</h2>
          <table>
            <thead>
              <tr>
                <th>Ingredient</th>
                <th>Received/Open</th>
                <th>Issued</th>
                <th>POS Deducted</th>
                <th>Waste</th>
                <th>Closing</th>
                <th>Stock Value</th>
              </tr>
            </thead>
            <tbody>
              {stockBalances.map((stock) => {
                const ingredient = ingredients.find((item) => item.name === stock.ingredient);
                const unitCost = Number(ingredient?.average_cost || ingredient?.cost_per_unit || 0);
                return (
                  <tr key={stock.ingredient}>
                    <td>{stock.ingredient}</td>
                    <td>{stock.received.toFixed(3)} {stock.unit}</td>
                    <td>{stock.manualIssue.toFixed(3)} {stock.unit}</td>
                    <td>{stock.posIssue.toFixed(3)} {stock.unit}</td>
                    <td>{stock.wastage.toFixed(3)} {stock.unit}</td>
                    <td>{stock.closing.toFixed(3)} {stock.unit}</td>
                    <td>{money(stock.closing * unitCost)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>

        <section className="fnb-print-section">
          <h2>Purchasing and Receiving Control</h2>
          <table>
            <thead>
              <tr>
                <th>PO</th>
                <th>Supplier</th>
                <th>Ingredient</th>
                <th>Ordered</th>
                <th>Received</th>
                <th>Rejected</th>
                <th>Value</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {purchaseOrders.map((po) => (
                <tr key={po.id}>
                  <td>#{po.id}</td>
                  <td>{po.supplier_name}</td>
                  <td>{po.ingredient_name}</td>
                  <td>{po.ordered_qty ?? po.quantity}</td>
                  <td>{po.received_qty ?? 0}</td>
                  <td>{po.rejected_qty ?? 0}</td>
                  <td>{money(Number(po.total_amount || 0))}</td>
                  <td>{po.approval_status || po.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <footer className="fnb-print-footer">
          <span>Prepared: {reportApproval.prepared_by || "Pending"} {reportApproval.prepared_at ? `| ${reportApproval.prepared_at}` : ""}</span>
          <span>Finance: {reportApproval.finance_reviewed_by || "Pending"} {reportApproval.finance_reviewed_at ? `| ${reportApproval.finance_reviewed_at}` : ""}</span>
          <span>F&B Manager: {reportApproval.fnb_approved_by || "Pending"} {reportApproval.fnb_approved_at ? `| ${reportApproval.fnb_approved_at}` : ""}</span>
          <span>GM / Lock: {reportApproval.gm_approved_by || "Pending"} {reportApproval.gm_approved_at ? `| ${reportApproval.gm_approved_at}` : ""}</span>
        </footer>
      </section>

      <section className="fnb-workflow-ribbon mb-4 print:hidden" aria-label="F&B workflow navigation">
        <div className="fnb-workflow-heading">
          <div>
            <p>Workflow Navigation</p>
            <h2>{activeWorkflowMeta.label}</h2>
            <span>{activeWorkflowMeta.detail}</span>
          </div>
          <span className="fnb-workflow-count">{visibleWorkflows.length} modules</span>
        </div>

        <div className="fnb-workflow-grid">
          {visibleWorkflows.map((workflow) => {
            const Icon = workflow.icon;
            const isActive = activeWorkflow === workflow.id;
            return (
              <button
                key={workflow.id}
                type="button"
                aria-pressed={isActive}
                onClick={() => setActiveWorkflow(workflow.id)}
                className={`fnb-workflow-btn ${isActive ? "active" : ""}`}
              >
                <span className="fnb-workflow-icon">
                  <Icon aria-hidden="true" size={18} />
                </span>
                <span className="fnb-workflow-text">
                  <strong>{workflow.label}</strong>
                  <small>{workflow.detail}</small>
                </span>
              </button>
            );
          })}
        </div>
      </section>

      <div>
        <main className="space-y-6">
          <section className="fnb-metric-grid">
            {metricCards.map((metric) => {
              const Icon = metric.icon;
              return (
                <button
                  key={metric.id}
                  type="button"
                  onClick={() => setActiveMetric(metric.id)}
                  className={
                    `fnb-metric-card ${metric.tone} ` +
                    (activeMetric === metric.id ? "active" : "")
                  }
                >
                  <Icon aria-hidden="true" size={20} />
                  <span>{metric.label}</span>
                  <strong>{metric.value}</strong>
                  <small>{metric.hint}</small>
                </button>
              );
            })}
          </section>

          <section className="fnb-active-strip rounded-2xl border border-slate-200 bg-white p-4">
            <div>
              <span>Selected Focus</span>
              <strong>{activeMetricCard.label}: {activeMetricCard.value}</strong>
            </div>
            <div>
              <span>{activeWorkflow.replace("-", " ")}</span>
              <span>{role.replace("_", " ")}</span>
              <span>{loading ? "Refreshing" : "Live"}</span>
            </div>
          </section>

          {activeWorkflow === "fnb-dashboard" && (
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

          {["suppliers", "purchase-orders", "receiving"].includes(activeWorkflow) && (
            <section className="grid gap-6 xl:grid-cols-2">
              {activeWorkflow === "suppliers" && (
                <Panel title="Supplier Master">
                  <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-slate-600">
                      Manage approved food and beverage vendors for purchasing.
                    </p>
                    <button
                      type="button"
                      className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white"
                      onClick={() => setShowSupplierForm((current) => !current)}
                    >
                      {showSupplierForm ? "Close Supplier Form" : "New Supplier"}
                    </button>
                  </div>

                  {showSupplierForm && (
                    <form onSubmit={createSupplier} className="mb-4 grid gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 md:grid-cols-2">
                      <input
                        className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                        placeholder="Supplier name"
                        value={newSupplier.supplier_name}
                        onChange={(event) => setNewSupplier({ ...newSupplier, supplier_name: event.target.value })}
                      />
                      <input
                        className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                        placeholder="Contact person"
                        value={newSupplier.contact_name}
                        onChange={(event) => setNewSupplier({ ...newSupplier, contact_name: event.target.value })}
                      />
                      <input
                        className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                        placeholder="Phone"
                        value={newSupplier.phone}
                        onChange={(event) => setNewSupplier({ ...newSupplier, phone: event.target.value })}
                      />
                      <input
                        className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                        placeholder="Email"
                        value={newSupplier.email}
                        onChange={(event) => setNewSupplier({ ...newSupplier, email: event.target.value })}
                      />
                      <input
                        className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm md:col-span-2"
                        placeholder="Payment terms, e.g. 30 days"
                        value={newSupplier.payment_terms}
                        onChange={(event) => setNewSupplier({ ...newSupplier, payment_terms: event.target.value })}
                      />
                      <div className="flex flex-wrap gap-2 md:col-span-2">
                        <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white" type="submit">
                          Save Supplier
                        </button>
                        <button
                          className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700"
                          type="button"
                          onClick={() => setShowSupplierForm(false)}
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  )}

                  <DataTable
                    columns={["Supplier", "Contact", "Phone", "Email", "Terms", "Status"]}
                    rows={suppliers.map((supplier) => [
                      supplier.supplier_name,
                      supplier.contact_name || "-",
                      supplier.phone || "-",
                      supplier.email || "-",
                      supplier.payment_terms || "-",
                      supplier.is_active === false ? "Inactive" : "Active",
                    ])}
                  />
                </Panel>
              )}

              <Panel title="Purchase Orders">
                {activeWorkflow === "purchase-orders" && (
                  <form onSubmit={createPurchaseOrder} className="mb-4 grid gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 md:grid-cols-2">
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" placeholder="Supplier" value={newPo.supplier_name} onChange={(event) => setNewPo({ ...newPo, supplier_name: event.target.value })} />
                    <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" value={newPo.ingredient_name} onChange={(event) => setNewPo({ ...newPo, ingredient_name: event.target.value })}>
                      {[...new Set([...ethiopianItems, ...ingredients.map((item) => item.name)])].map((item) => <option key={item} value={item}>{item}</option>)}
                    </select>
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" type="number" step="0.001" min="0.001" placeholder="Ordered quantity" value={newPo.quantity} onChange={(event) => setNewPo({ ...newPo, quantity: event.target.value })} />
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" type="number" step="0.01" min="0.01" placeholder="Unit cost in ETB" value={newPo.unit_price} onChange={(event) => setNewPo({ ...newPo, unit_price: event.target.value })} />
                    <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white md:col-span-2" type="submit">Create Purchase Order</button>
                  </form>
                )}
                {activeWorkflow === "purchase-orders" && filteredPurchaseOrders.some((po) => String(po.approval_status || "").toLowerCase() === "pending") ? (
                  <div className="mb-4 grid gap-2">
                    {filteredPurchaseOrders.filter((po) => String(po.approval_status || "").toLowerCase() === "pending").map((po) => (
                      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3" key={po.id}>
                        <span className="text-sm font-semibold">PO #{po.id}: {po.ingredient_name} from {po.supplier_name}</span>
                        <button className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-bold text-white" type="button" onClick={() => approvePurchaseOrder(po.id)}>Approve</button>
                      </div>
                    ))}
                  </div>
                ) : null}
                <DataTable
                  columns={["PO", "Ingredient", "Supplier", "Ordered", "Received", "Rejected", "Total", "Approval"]}
                  rows={filteredPurchaseOrders.map((po) => [
                    `#${po.id}`,
                    po.ingredient_name,
                    po.supplier_name,
                    po.ordered_qty ?? po.quantity,
                    po.received_qty ?? 0,
                    po.rejected_qty ?? 0,
                    money(Number(po.total_amount || 0)),
                    po.approval_status || po.status,
                  ])}
                />
              </Panel>

              <Panel title="Goods Receiving">
                {activeWorkflow === "receiving" && (
                  <form onSubmit={createGoodsReceived} className="mb-4 grid gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 md:grid-cols-3">
                    <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" value={newGrn.purchase_order_id} onChange={(event) => setNewGrn({ ...newGrn, purchase_order_id: event.target.value })}>
                      <option value="">Choose approved Purchase Order</option>
                      {purchaseOrders.filter((po) => String(po.approval_status || "").toLowerCase() === "approved").map((po) => <option key={po.id} value={po.id}>PO #{po.id} - {po.ingredient_name}</option>)}
                    </select>
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" type="number" step="0.001" min="0" placeholder="Accepted quantity" value={newGrn.quantity_received} onChange={(event) => setNewGrn({ ...newGrn, quantity_received: event.target.value })} />
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" type="number" step="0.001" min="0" placeholder="Rejected quantity" value={newGrn.rejected_qty} onChange={(event) => setNewGrn({ ...newGrn, rejected_qty: event.target.value })} />
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" type="number" step="0.01" min="0" placeholder="Unit cost ETB" value={newGrn.unit_cost} onChange={(event) => setNewGrn({ ...newGrn, unit_cost: event.target.value })} />
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" placeholder="Received by" value={newGrn.received_by} onChange={(event) => setNewGrn({ ...newGrn, received_by: event.target.value })} />
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" placeholder="Invoice number" value={newGrn.invoice_number} onChange={(event) => setNewGrn({ ...newGrn, invoice_number: event.target.value })} />
                    <button className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-bold text-white md:col-span-3" type="submit">Post Goods Receiving Note</button>
                  </form>
                )}
                <DataTable
                  columns={["GRN", "PO", "Ingredient", "Received", "Rejected", "Unit Cost", "Invoice", "Received By"]}
                  rows={filteredGoodsReceived.map((g) => [
                    `#${g.id}`,
                    `PO #${g.purchase_order_id}`,
                    g.ingredient_name,
                    g.quantity_received,
                    g.rejected_qty ?? 0,
                    money(Number(g.unit_cost || 0)),
                    g.invoice_number || "-",
                    g.received_by,
                  ])}
                />
              </Panel>
            </section>
          )}

          {["store-inventory", "kitchen-requisition", "wastage-spoilage", "stock-count"].includes(activeWorkflow) && (
            <section className="grid gap-6">
              {activeWorkflow === "store-inventory" && (
                <Panel title="Store Control Actions">
                  <div className="grid gap-3 md:grid-cols-4">
                    <button className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-bold text-white" type="button" onClick={() => setActiveWorkflow("receiving")}>Receive Goods</button>
                    <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white" type="button" onClick={() => setActiveWorkflow("kitchen-requisition")}>Issue Stock</button>
                    <button className="rounded-lg border border-amber-200 bg-white px-4 py-2 text-sm font-bold text-slate-800" type="button">View Ledger</button>
                    <button className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-bold text-white" type="button" onClick={exportSpreadsheet}>Export</button>
                  </div>
                </Panel>
              )}

              {activeWorkflow === "kitchen-requisition" && (
                <Panel title="Kitchen Requisition Control">
                  <p className="text-sm leading-6 text-slate-600">
                    Chefs request ingredients, storekeepers issue approved stock, and every issue appears in the inventory movement audit trail.
                  </p>
                  <form onSubmit={createStoreRequisition} className="mt-4 grid gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 md:grid-cols-3">
                    <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" value={newRequisition.outlet_name} onChange={(event) => setNewRequisition({ ...newRequisition, outlet_name: event.target.value })}>
                      {hotelDepartments.map((department) => <option key={department} value={department}>{department}</option>)}
                    </select>
                    <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" value={newRequisition.ingredient_name} onChange={(event) => setNewRequisition({ ...newRequisition, ingredient_name: event.target.value })}>
                      {[...new Set([...ethiopianItems, ...ingredients.map((item) => item.name)])].map((item) => <option key={item} value={item}>{item}</option>)}
                    </select>
                    <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" value={newRequisition.unit} onChange={(event) => setNewRequisition({ ...newRequisition, unit: event.target.value })}>
                      {hotelUnits.map((unit) => <option key={unit} value={unit}>{unit}</option>)}
                    </select>
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" type="number" step="0.001" min="0.001" placeholder="Requested quantity" value={newRequisition.requested_qty} onChange={(event) => setNewRequisition({ ...newRequisition, requested_qty: event.target.value })} />
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" placeholder="Requested by" value={newRequisition.requested_by} onChange={(event) => setNewRequisition({ ...newRequisition, requested_by: event.target.value })} />
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" placeholder="Reason or menu production note" value={newRequisition.notes} onChange={(event) => setNewRequisition({ ...newRequisition, notes: event.target.value })} />
                    <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white md:col-span-3" type="submit">Create Store Requisition</button>
                  </form>
                  {filteredKitchenRequisitions.some((req) => String(req.status || "").toLowerCase() === "requested") && (
                    <div className="mt-4 grid gap-2">
                      {filteredKitchenRequisitions.filter((req) => String(req.status || "").toLowerCase() === "requested").map((req) => (
                        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3" key={req.id}>
                          <span className="text-sm font-semibold">Req #{req.id}: {req.outlet_name} needs {req.requested_qty} {req.unit} {req.ingredient_name}</span>
                          <button className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-bold text-white" type="button" onClick={() => approveStoreRequisition(req.id)}>Approve</button>
                        </div>
                      ))}
                    </div>
                  )}
                  <form onSubmit={issueStoreRequisition} className="mt-4 grid gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 md:grid-cols-3">
                    <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" value={issueForm.requisition_id} onChange={(event) => setIssueForm({ ...issueForm, requisition_id: event.target.value })}>
                      <option value="">Choose approved Store Requisition</option>
                      {kitchenRequisitions.filter((req) => String(req.status || "").toLowerCase() === "approved").map((req) => <option key={req.id} value={req.id}>#{req.id} - {req.outlet_name} - {req.ingredient_name}</option>)}
                    </select>
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" type="number" step="0.001" min="0.001" placeholder="Issued quantity" value={issueForm.issued_qty} onChange={(event) => setIssueForm({ ...issueForm, issued_qty: event.target.value })} />
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" placeholder="Issued by" value={issueForm.issued_by} onChange={(event) => setIssueForm({ ...issueForm, issued_by: event.target.value })} />
                    <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700">
                      <input type="checkbox" checked={issueForm.manager_override} onChange={(event) => setIssueForm({ ...issueForm, manager_override: event.target.checked })} />
                      Manager override
                    </label>
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" placeholder="Override by" value={issueForm.override_by} onChange={(event) => setIssueForm({ ...issueForm, override_by: event.target.value })} />
                    <button className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-bold text-white md:col-span-3" type="submit">Issue Approved Stock</button>
                  </form>
                  <div className="mt-4">
                    <DataTable
                      columns={["Req", "Department", "Item", "Requested", "Issued", "Status", "By"]}
                      rows={filteredKitchenRequisitions.map((req) => [
                        `#${req.id}`,
                        req.outlet_name || "-",
                        req.ingredient_name,
                        `${req.requested_qty} ${req.unit}`,
                        `${req.issued_qty || 0} ${req.unit}`,
                        req.status,
                        req.requested_by,
                      ])}
                    />
                  </div>
                </Panel>
              )}

              {activeWorkflow === "wastage-spoilage" && (
                <Panel title="Wastage / Spoilage Control">
                  <form onSubmit={createWasteRecord} className="mb-4 grid gap-3 rounded-lg border border-red-200 bg-red-50 p-4 md:grid-cols-3">
                    <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" value={newWaste.ingredient_name} onChange={(event) => setNewWaste({ ...newWaste, ingredient_name: event.target.value })}>
                      {[...new Set([...ethiopianItems, ...ingredients.map((item) => item.name)])].map((item) => <option key={item} value={item}>{item}</option>)}
                    </select>
                    <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" value={newWaste.unit} onChange={(event) => setNewWaste({ ...newWaste, unit: event.target.value })}>
                      {hotelUnits.map((unit) => <option key={unit} value={unit}>{unit}</option>)}
                    </select>
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" type="number" step="0.001" min="0.001" placeholder="Waste quantity" value={newWaste.quantity} onChange={(event) => setNewWaste({ ...newWaste, quantity: event.target.value })} />
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm md:col-span-2" placeholder="Reason, e.g. spoilage, trim loss, over-production" value={newWaste.reason} onChange={(event) => setNewWaste({ ...newWaste, reason: event.target.value })} />
                    <button className="rounded-lg bg-red-700 px-4 py-2 text-sm font-bold text-white" type="submit">Record Waste</button>
                  </form>
                  <DataTable
                    columns={["Ingredient", "Qty", "Value", "Reason / Reference", "Recorded By"]}
                    rows={filteredInventoryMovements
                      .filter((m) => m.movement_type === "WASTAGE")
                      .map((m) => [
                        m.ingredient_name,
                        `${m.quantity} ${m.unit}`,
                        money(Number(m.stock_value || 0)),
                        m.notes || m.reference || "-",
                        m.created_by,
                      ])}
                  />
                </Panel>
              )}

              {activeWorkflow === "stock-count" && (
                <Panel title="Stock Count Workpaper">
                  <form onSubmit={createStockCount} className="mb-4 grid gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 md:grid-cols-3">
                    <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" value={newStockCount.ingredient_name} onChange={(event) => setNewStockCount({ ...newStockCount, ingredient_name: event.target.value })}>
                      {[...new Set([...ethiopianItems, ...ingredients.map((item) => item.name)])].map((item) => <option key={item} value={item}>{item}</option>)}
                    </select>
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" type="number" step="0.001" min="0" placeholder="System quantity" value={newStockCount.system_qty} onChange={(event) => setNewStockCount({ ...newStockCount, system_qty: event.target.value })} />
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" type="number" step="0.001" min="0" placeholder="Physical quantity" value={newStockCount.physical_qty} onChange={(event) => setNewStockCount({ ...newStockCount, physical_qty: event.target.value })} />
                    <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" value={newStockCount.unit} onChange={(event) => setNewStockCount({ ...newStockCount, unit: event.target.value })}>
                      {hotelUnits.map((unit) => <option key={unit} value={unit}>{unit}</option>)}
                    </select>
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" placeholder="Counted by" value={newStockCount.counted_by} onChange={(event) => setNewStockCount({ ...newStockCount, counted_by: event.target.value })} />
                    <input className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" placeholder="Reason / note" value={newStockCount.notes} onChange={(event) => setNewStockCount({ ...newStockCount, notes: event.target.value })} />
                    <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white md:col-span-3" type="submit">Save Stock Count Variance</button>
                  </form>
                  <DataTable
                    columns={["Ingredient", "System", "Physical", "Variance", "Value", "Status"]}
                    rows={varianceRows.map((row) => [
                      row.ingredient,
                      `${row.closing.toFixed(3)} ${row.unit}`,
                      `${row.physical.toFixed(3)} ${row.unit}`,
                      `${row.varianceQty.toFixed(3)} ${row.unit}`,
                      money(row.value),
                      row.status,
                    ])}
                  />
                </Panel>
              )}

              <Panel title="Main Store Ledger">
                <DataTable
                  columns={["Serial No", "Item Code", "Item Name", "Category", "Unit", "Opening", "Purchased", "Total Balance", "Issued", "Balance on Hand", "Unit Price", "Total Value", "Supplier", "GRN", "Requisition", "Department", "Reorder", "Status"]}
                  rows={filteredMainStoreLedger.map((row) => [
                    row.serialNo,
                    row.itemCode,
                    row.itemName,
                    row.category,
                    row.unit,
                    row.openingBalance.toFixed(3),
                    row.purchasedQuantity.toFixed(3),
                    row.totalBalance.toFixed(3),
                    row.issuedQuantity.toFixed(3),
                    row.balanceOnHand.toFixed(3),
                    money(row.unitPrice),
                    money(row.totalValue),
                    row.supplier,
                    row.grnNumber,
                    row.storeRequisitionNumber,
                    row.departmentIssuedTo,
                    row.reorderLevel,
                    row.status,
                  ])}
                />
              </Panel>

              {activeWorkflow === "store-inventory" && (
                <section className="grid gap-6 xl:grid-cols-2">
                  <Panel title="Daily Receiving Report">
                    <DataTable
                      columns={["GRN", "Item", "Supplier", "Qty", "Unit Cost", "Value"]}
                      rows={filteredInventoryMovements.filter((m) => m.movement_type === "PURCHASE_RECEIVED").map((m) => [
                        m.reference || "-",
                        m.ingredient_name,
                        ingredients.find((item) => item.name === m.ingredient_name)?.supplier_name || "-",
                        `${m.quantity} ${m.unit}`,
                        money(Number(m.unit_cost || 0)),
                        money(Number(m.stock_value || 0)),
                      ])}
                    />
                  </Panel>

                  <Panel title="Daily Issue Report">
                    <DataTable
                      columns={["Requisition", "Item", "Department", "Qty", "Value"]}
                      rows={filteredInventoryMovements.filter((m) => m.movement_type === "KITCHEN_ISSUE").map((m) => [
                        m.reference || "-",
                        m.ingredient_name,
                        kitchenRequisitions.find((req) => m.reference === `Store Requisition #${req.id}`)?.outlet_name || "-",
                        `${m.quantity} ${m.unit}`,
                        money(Number(m.stock_value || 0)),
                      ])}
                    />
                  </Panel>

                  <Panel title="Low Stock Report">
                    <DataTable
                      columns={["Item", "Balance", "Reorder Level", "Status"]}
                      rows={filteredMainStoreLedger.filter((row) => row.status === "Low stock" || row.status === "Negative stock").map((row) => [
                        row.itemName,
                        `${row.balanceOnHand.toFixed(3)} ${row.unit}`,
                        row.reorderLevel,
                        row.status,
                      ])}
                    />
                  </Panel>

                  <Panel title="Inventory Valuation Report">
                    <DataTable
                      columns={["Item", "Balance", "Unit Price", "Total Value"]}
                      rows={filteredMainStoreLedger.map((row) => [
                        row.itemName,
                        `${row.balanceOnHand.toFixed(3)} ${row.unit}`,
                        money(row.unitPrice),
                        money(row.totalValue),
                      ])}
                    />
                  </Panel>

                  <Panel title="Supplier Purchase Report">
                    <DataTable
                      columns={["Supplier", "Item", "Purchased", "Value"]}
                      rows={filteredMainStoreLedger.filter((row) => row.purchasedQuantity > 0).map((row) => [
                        row.supplier,
                        row.itemName,
                        `${row.purchasedQuantity.toFixed(3)} ${row.unit}`,
                        money(row.purchasedQuantity * row.unitPrice),
                      ])}
                    />
                  </Panel>

                  <Panel title="Department Consumption Report">
                    <DataTable
                      columns={["Department", "Item", "Issued", "Value"]}
                      rows={filteredMainStoreLedger.filter((row) => row.issuedQuantity > 0).map((row) => [
                        row.departmentIssuedTo,
                        row.itemName,
                        `${row.issuedQuantity.toFixed(3)} ${row.unit}`,
                        money(row.issuedQuantity * row.unitPrice),
                      ])}
                    />
                  </Panel>

                  <Panel title="Expiry / Near Expiry Report">
                    <DataTable
                      columns={["Item", "Expiry Date", "Balance", "Status"]}
                      rows={filteredMainStoreLedger.filter((row) => row.status === "Expired").map((row) => {
                        const ingredient = ingredients.find((item) => item.name === row.itemName);
                        return [
                          row.itemName,
                          ingredient?.expiry_date || "-",
                          `${row.balanceOnHand.toFixed(3)} ${row.unit}`,
                          row.status,
                        ];
                      })}
                    />
                  </Panel>
                </section>
              )}

              <Panel title="Inventory Movement Audit Trail">
                <DataTable
                  columns={["Ingredient", "Type", "Qty", "Reference", "Created By"]}
                  rows={filteredInventoryMovements.map((m) => [
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

          {["ingredients", "recipes"].includes(activeWorkflow) && (
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
                {activeWorkflow === "recipes" && (
                <Panel title="Recipe Costing">
                  <DataTable
                    columns={["Recipe", "Selling", "Cost", "Food Cost %", "Target", "Margin", "Status"]}
                    rows={filteredRecipes.map((r) => [
                      r.name,
                      money(Number(r.selling_price || 0)),
                      money(Number(r.total_cost || 0)),
                      `${Number(r.food_cost_percentage || 0).toFixed(2)}%`,
                      `${Number(r.target_cost_percentage || 35).toFixed(2)}%`,
                      money(Number(r.selling_price || 0) - Number(r.total_cost || 0)),
                      r.approval_status || "draft",
                    ])}
                  />
                </Panel>
                )}

                {activeWorkflow === "recipes" && (
                <Panel title="À La Carte Menu Costing">
                  <DataTable
                    columns={["Menu Item", "Menu Type", "Department", "Portion", "Selling", "Cost / Portion", "Food Cost %", "Gross Profit", "Status"]}
                    rows={alaCarteRecipes.map((recipe) => [
                      recipe.name,
                      alaCarteRecipeMeta[recipe.name].menuType,
                      recipe.outlet_name || "Main Kitchen",
                      alaCarteRecipeMeta[recipe.name].portion,
                      money(Number(recipe.selling_price || 0)),
                      money(Number(recipe.total_cost || 0)),
                      `${Number(recipe.food_cost_percentage || 0).toFixed(2)}%`,
                      money(Number(recipe.selling_price || 0) - Number(recipe.total_cost || 0)),
                      recipeProfitStatus(recipe),
                    ])}
                  />
                </Panel>
                )}

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
                        placeholder="Category, e.g. food, beverage"
                        value={newIngredient.category}
                        onChange={(e) =>
                          setNewIngredient({
                            ...newIngredient,
                            category: e.target.value,
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
                        type="number"
                        step="0.001"
                        min="0"
                        placeholder="Reorder level"
                        value={newIngredient.reorder_level}
                        onChange={(e) =>
                          setNewIngredient({
                            ...newIngredient,
                            reorder_level: e.target.value,
                          })
                        }
                      />

                      <input
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                        type="date"
                        value={newIngredient.expiry_date}
                        onChange={(e) =>
                          setNewIngredient({
                            ...newIngredient,
                            expiry_date: e.target.value,
                          })
                        }
                      />

                      <input
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                        placeholder="Storage location"
                        value={newIngredient.storage_location}
                        onChange={(e) =>
                          setNewIngredient({
                            ...newIngredient,
                            storage_location: e.target.value,
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
                    columns={["Ingredient", "Category", "Unit", "Last Price", "Average Cost", "Reorder", "Expiry", "Storage", "Supplier"]}
                    rows={filteredIngredients.map((i) => [
                      i.name,
                      i.category || "-",
                      i.unit,
                      money(Number(i.last_purchase_price || i.purchase_price || i.cost_per_unit || 0)),
                      money(Number(i.cost_per_unit || 0)),
                      i.reorder_level || "-",
                      i.expiry_date || "-",
                      i.storage_location || "-",
                      i.supplier_name || "-",
                    ])}
                  />
                </Panel>
              </section>
            </section>
          )}

          {["menu-engineering", "pos-sales", "variance-report"].includes(activeWorkflow) && (
            <section className="grid gap-6">
              {activeWorkflow === "pos-sales" && (
                <Panel title="POS / Outlet Sales and Room Charge Control">
                  <DataTable
                    columns={["Outlet", "Menu Item", "Qty Sold", "Sales", "Service", "VAT", "Payment", "Room Booking"]}
                    rows={posSales.map((sale) => [
                      sale.outlet_name,
                      sale.menu_item_name,
                      sale.quantity_sold,
                      money(Number(sale.total_revenue || 0)),
                      money(Number(sale.service_charge_amount || 0)),
                      money(Number(sale.tax_amount || 0)),
                      sale.payment_method || "cash",
                      sale.room_charge_booking_id ? `Booking #${sale.room_charge_booking_id}` : "-",
                    ])}
                  />
                </Panel>
              )}

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
    dark: "fnb-kpi-dark border-slate-900 bg-slate-900 text-white",
    danger: "border-red-200 bg-red-50 text-red-900",
    success: "border-emerald-200 bg-emerald-50 text-emerald-900",
    warning: "border-amber-200 bg-amber-50 text-amber-900",
    neutral: "border-slate-200 bg-white text-slate-900",
  };

  return (
    <div className={`fnb-kpi rounded-lg border p-5 shadow-sm ${toneMap[tone]}`}>
      <p className="text-xs font-bold uppercase tracking-wide opacity-70">{label}</p>
      <p className="mt-2 text-2xl font-black">{value}</p>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="fnb-panel rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-black text-slate-900">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function RiskItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs font-bold uppercase text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-black text-slate-900">{value}</p>
    </div>
  );
}

function DataTable({ columns, rows }: { columns: string[]; rows: (string | number)[][] }) {
  return (
    <div className="fnb-ledger-table overflow-hidden rounded-lg border border-amber-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="fnb-empty-cell">
                  No records found.
                </td>
              </tr>
            ) : (
              rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {row.map((cell, cellIndex) => {
                    const columnName = columns[cellIndex] || "";
                    const isLabelCell = cellIndex === 0;
                    const isBadgeCell = ["status", "class"].includes(columnName.toLowerCase());

                    return (
                      <td
                        key={cellIndex}
                        data-label={columnName}
                        className={isLabelCell ? "fnb-primary-cell" : ""}
                      >
                        {isBadgeCell ? (
                          <span className={`fnb-table-badge fnb-table-badge-${String(cell).toLowerCase().replace(/\s+/g, "-")}`}>
                            {cell}
                          </span>
                        ) : (
                          cell
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
