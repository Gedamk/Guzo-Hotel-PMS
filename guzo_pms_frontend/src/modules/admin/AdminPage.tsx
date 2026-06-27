import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import PageHeader from "../../components/PageHeader";
import KpiCard from "../../components/KpiCard";
import DataTable from "../../components/DataTable";
import { LoadingState } from "../../components/ui/LoadingState";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { usePmsContext } from "../../context/PmsContext";
import type { HotelProperty, RoomStatusItem } from "../../types/pms";
import { fetchRoomStatusBoard } from "../../services/pmsService";
import {
  createAdminUser,
  disableAdminUser,
  fetchAdminOverview,
  fetchAdminPermissions,
  fetchAdminRoles,
  fetchAdminUsers,
  fetchPmsAuditLogs,
  fetchPropertyGoLiveCheck,
  fetchRateConfiguration,
  assignAdminToProperty,
  resetAdminUserPassword,
  resetPropertyDemoRooms,
  activateLiveProperty,
  seedPropertyDemoRooms,
  updateRateConfiguration,
  type AdminOverview,
  type AdminPermissionRow,
  type AdminRole,
  type AdminUser,
  type PmsAuditLog,
  type PropertyGoLiveCheck,
  type RateConfiguration,
} from "../../services/adminService";
import { getErrorMessage } from "../../services/http";
type PaymentMethodRow = {
  method: string;
  category: string;
  status: "enabled" | "disabled";
};

type PropertyMode = "view" | "edit" | "add" | "onboard";

const emptyPropertyForm: HotelProperty = {
  name: "",
  code: "",
  address: "",
  city: "",
  country: "",
  timezone: "Africa/Addis_Ababa",
  currency: "ETB",
  phone: "",
  email: "",
  isActive: true,
  onboardingStatus: "not_started",
};

const onboardingSections = [
  { key: "room_types", title: "Room Types", detail: "Define sellable room categories, occupancy, and bedding." },
  { key: "rooms", title: "Rooms", detail: "Create room numbers, floors, features, and service status." },
  { key: "rate_plans", title: "BAR / Corporate / Group / Weekend Rates", detail: "Build core sellable rate plans and approval rules." },
  { key: "tax_deposit", title: "Tax, Service Charge & Deposit", detail: "Configure VAT, service charge, deposit, and cancellation policy." },
  { key: "users_roles", title: "Users / Roles", detail: "Invite Admin, GM, Front Desk, Housekeeping, Finance, F&B, and Store teams." },
  { key: "fnb_store", title: "F&B Store Items", detail: "Seed items, units, opening balance, unit price, and reorder level." },
  { key: "night_audit", title: "Night Audit Setup", detail: "Review business date, posting controls, and end-of-day readiness." },
  { key: "go_live", title: "Run Go-Live Check", detail: "Validate required setup before activating live operations." },
];

const propertyWorkflowSteps = [
  "Save Property",
  "Start Onboarding",
  "Manage Rooms",
  "Manage Rates",
  "Manage Tax & Deposit",
  "Manage Users",
  "Manage Store Items",
  "Night Audit Setup",
  "Run Go-Live Check",
  "Activate Live Property",
  "Open Dashboard",
];

type AdminTab =
  | "overview"
  | "users"
  | "permissions"
  | "property"
  | "rooms"
  | "rates"
  | "payments"
  | "business_date"
  | "reports"
  | "integrations"
  | "notifications"
  | "audit_logs"
  | "security"
  | "backup";

const adminTabs: Record<AdminTab, string> = {
  overview: "System Overview",
  users: "Users & Roles",
  permissions: "Permissions",
  property: "Property Setup",
  rooms: "Rooms & Inventory",
  rates: "Rates & Taxes",
  payments: "Payment Methods",
  business_date: "Business Date",
  reports: "Reports Setup",
  integrations: "Integrations",
  notifications: "Notification Outbox",
  audit_logs: "Audit Logs",
  security: "Security",
  backup: "Backup",
};

const adminTabByHash: Record<string, AdminTab> = {
  overview: "overview",
  "system-health": "overview",
  users: "users",
  roles: "users",
  "users-roles": "users",
  permissions: "permissions",
  property: "property",
  "property-setup": "property",
  rooms: "rooms",
  "room-setup": "rooms",
  rates: "rates",
  "rate-configuration": "rates",
  "tax-service-rules": "rates",
  payments: "payments",
  "business-date": "business_date",
  "night-audit-setup": "business_date",
  reports: "reports",
  integrations: "integrations",
  interfaces: "integrations",
  notifications: "notifications",
  "audit-logs": "audit_logs",
  security: "security",
  backup: "backup",
};

function roomTypeFromNumber(roomNumber: string) {
  const n = Number(roomNumber);
  if (!Number.isFinite(n)) return "Standard";
  if (n >= 300) return "Suite";
  if (n >= 200) return "Deluxe";
  return "Standard";
}

export default function AdminPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const {
    propertyCode,
    businessDate,
    propertyName,
    propertyOptions,
    activeProperty,
    setPropertyCode,
    saveProperty,
    updateProperty,
    syncProperty,
    refreshKey,
  } = usePmsContext();

  const [rooms, setRooms] = useState<RoomStatusItem[]>([]);
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([]);
  const [adminRoles, setAdminRoles] = useState<AdminRole[]>([]);
  const [permissions, setPermissions] = useState<AdminPermissionRow[]>([]);
  const [auditLogs, setAuditLogs] = useState<PmsAuditLog[]>([]);
  const [rateConfig, setRateConfig] = useState<RateConfiguration | null>(null);
  const [activeTab, setActiveTab] = useState<AdminTab>("overview");
  const [propertyMode, setPropertyMode] = useState<PropertyMode>("view");
  const [selectedPropertyCode, setSelectedPropertyCode] = useState(propertyCode);
  const [propertyForm, setPropertyForm] = useState<HotelProperty>(activeProperty);
  const [goLiveChecks, setGoLiveChecks] = useState<Record<string, PropertyGoLiveCheck>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [workflowNextAction, setWorkflowNextAction] = useState("Start Onboarding");
  const [userForm, setUserForm] = useState({
    full_name: "",
    email: "",
    role_key: "frontdesk_agent",
  });

  useEffect(() => {
    const hashKey = location.hash.replace(/^#/, "");
    const tab = adminTabByHash[hashKey];
    if (tab) setActiveTab(tab);
  }, [location.hash]);

  const [paymentMethods] = useState<PaymentMethodRow[]>([
    { method: "cash", category: "cashier", status: "enabled" },
    { method: "card", category: "electronic", status: "enabled" },
    { method: "bank_transfer", category: "electronic", status: "enabled" },
    { method: "mobile_transfer", category: "electronic", status: "enabled" },
    { method: "city_ledger", category: "credit", status: "disabled" },
  ]);

  async function loadRooms() {
    try {
      setLoading(true);
      setError("");
      const [data, overviewData, usersData, rolesData, permissionsData, auditData, rateConfigData] = await Promise.all([
        fetchRoomStatusBoard(propertyCode, businessDate),
        fetchAdminOverview(propertyCode, businessDate),
        fetchAdminUsers(propertyCode),
        fetchAdminRoles(propertyCode),
        fetchAdminPermissions(propertyCode),
        fetchPmsAuditLogs(propertyCode),
        fetchRateConfiguration(propertyCode),
      ]);
      setRooms(data);
      setOverview(overviewData);
      setAdminUsers(usersData);
      setAdminRoles(rolesData);
      setPermissions(permissionsData);
      setAuditLogs(auditData);
      setRateConfig(rateConfigData);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRooms();
  }, [propertyCode, businessDate, refreshKey]);

  useEffect(() => {
    const selected =
      propertyOptions.find((property) => property.code === selectedPropertyCode) ||
      activeProperty;
    if (propertyMode === "view" || propertyMode === "onboard") {
      setPropertyForm(selected);
    }
  }, [activeProperty, propertyMode, propertyOptions, selectedPropertyCode]);

  const activeUsers = useMemo(
    () => adminUsers.filter((user) => user.is_active).length,
    [adminUsers]
  );

  const activeRooms = useMemo(
    () =>
      rooms.filter((room) => {
        const s = String(room.hk_status || "").toLowerCase();
        return s !== "out_of_order" && s !== "out_of_service";
      }).length,
    [rooms]
  );

  const enabledPayments = useMemo(
    () => paymentMethods.filter((method) => method.status === "enabled").length,
    [paymentMethods]
  );

  const systemHealthCards = useMemo(() => {
    const integrations = overview?.integrations || [];
    const integrationByKey = (key: string) =>
      integrations.find((row) => String(row.key || "").toLowerCase() === key);
    const integrationReady = (key: string) => {
      const status = String(integrationByKey(key)?.status || "").toLowerCase();
      return status === "online" || status === "configured" || status === "active";
    };
    const statusClass = (ready: boolean, warning = false) =>
      ready ? "success" : warning ? "warning" : "danger";

    const nightAuditReady = overview?.night_audit_status === "ready";
    const nightAuditKnown = Boolean(overview?.night_audit_status);
    const reportsReady = integrationReady("reports") || Number(overview?.report_archive_count || 0) > 0;
    const auditLogsReady = (overview?.audit_logs?.length || auditLogs.length) > 0;

    return [
      {
        label: "Backend API",
        value: overview?.backend_status === "online" ? "Online" : "Offline",
        detail: "FastAPI service",
        tone: statusClass(overview?.backend_status === "online"),
      },
      {
        label: "PostgreSQL",
        value: integrationReady("postgresql") || overview?.database_status === "online" ? "Connected" : "Disconnected",
        detail: "Primary PMS database",
        tone: statusClass(integrationReady("postgresql") || overview?.database_status === "online"),
      },
      {
        label: "Telegram",
        value: integrationReady("telegram") ? "Connected" : "Not configured",
        detail: "Controlled booking channel",
        tone: statusClass(integrationReady("telegram"), true),
      },
      {
        label: "Email",
        value: integrationReady("email") ? "Connected" : "Not configured",
        detail: "Guest notification delivery",
        tone: statusClass(integrationReady("email"), true),
      },
      {
        label: "Reports",
        value: reportsReady ? "Active" : "Not started",
        detail: `${overview?.report_archive_count ?? 0} archived / ${overview?.scheduled_reports_count ?? 0} scheduled`,
        tone: statusClass(reportsReady, true),
      },
      {
        label: "Night Audit",
        value: nightAuditReady ? "Ready" : nightAuditKnown ? "Not Ready" : "Unknown",
        detail: `${overview?.night_audit_blocking ?? 0} blocking / ${overview?.night_audit_warnings ?? 0} warnings`,
        tone: nightAuditReady ? "success" : "warning",
      },
      {
        label: "Audit Logs",
        value: auditLogsReady ? "Active" : "No activity",
        detail: `${overview?.audit_logs?.length || auditLogs.length} recent event(s)`,
        tone: statusClass(auditLogsReady, true),
      },
    ];
  }, [auditLogs.length, overview]);

  const selectedProperty = useMemo(
    () =>
      propertyOptions.find((property) => property.code === selectedPropertyCode) ||
      activeProperty,
    [activeProperty, propertyOptions, selectedPropertyCode]
  );

  async function handleCreateUser() {
    try {
      setActionMessage("");
      setError("");
      await createAdminUser({
        ...userForm,
        property_code: propertyCode,
        is_active: true,
      });
      setUserForm({ full_name: "", email: "", role_key: "frontdesk_agent" });
      setActionMessage("PMS user created and audit log recorded.");
      await loadRooms();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleDisableUser(userId: number) {
    try {
      setActionMessage("");
      setError("");
      await disableAdminUser(userId);
      setActionMessage("PMS user disabled and audit log recorded.");
      await loadRooms();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleResetPassword(userId: number) {
    try {
      setActionMessage("");
      setError("");
      const result = await resetAdminUserPassword(userId);
      setActionMessage(result.message);
      await loadRooms();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleSaveRateConfiguration() {
    if (!rateConfig) return;
    try {
      setActionMessage("");
      setError("");
      const saved = await updateRateConfiguration({
        ...rateConfig,
        property_code: propertyCode,
      });
      setRateConfig(saved);
      setActionMessage("Rate, tax, season, and deposit configuration saved with audit log.");
      const [permissionsData, auditData] = await Promise.all([
        fetchAdminPermissions(propertyCode),
        fetchPmsAuditLogs(propertyCode),
      ]);
      setPermissions(permissionsData);
      setAuditLogs(auditData);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  function selectProperty(property: HotelProperty, mode: PropertyMode) {
    setSelectedPropertyCode(property.code);
    setPropertyForm(property);
    setPropertyMode(mode);
    setPropertyCode(property.code);
    setActionMessage("");
    setWorkflowNextAction(mode === "onboard" ? "Manage Rooms" : "Start Onboarding");
    setError("");
  }

  function startAddProperty() {
    setPropertyMode("add");
    setPropertyForm(emptyPropertyForm);
    setActionMessage("");
    setWorkflowNextAction("Save Property");
    setError("");
  }

  function updatePropertyForm<K extends keyof HotelProperty>(key: K, value: HotelProperty[K]) {
    setPropertyForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSaveProperty() {
    const code = propertyForm.code.trim().toUpperCase().replace(/\s+/g, "");
    const requiredFields: Array<keyof HotelProperty> = [
      "name",
      "code",
      "address",
      "city",
      "country",
      "timezone",
      "currency",
      "phone",
      "email",
    ];
    const missing = requiredFields.find((field) => !String(propertyForm[field] || "").trim());

    setActionMessage("");
    setError("");

    if (missing) {
      setError(`Property ${String(missing).replace(/([A-Z])/g, " $1").toLowerCase()} is required.`);
      return;
    }

    const duplicate = propertyOptions.some(
      (property) =>
        property.code.toUpperCase() === code &&
        !(propertyMode === "edit" && property.code === selectedPropertyCode)
    );

    if (duplicate) {
      setError(`Property code ${code} already exists. Use a unique code.`);
      return;
    }

    try {
      const saved = await saveProperty({
        ...propertyForm,
        code,
        currency: propertyForm.currency.trim().toUpperCase(),
        onboardingStatus:
          propertyForm.onboardingStatus || (propertyMode === "add" ? "not_started" : "in_progress"),
      });
      setSelectedPropertyCode(saved.code);
      setPropertyCode(saved.code);
      setActiveTab("property");
      setPropertyMode("view");
      setWorkflowNextAction("Start Onboarding");
      setActionMessage(`${saved.name} saved and added to the property selector. Next: Start Onboarding.`);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function togglePropertyStatus(property: HotelProperty) {
    const nextStatus = !property.isActive;
    try {
      await updateProperty(property.code, { isActive: nextStatus });
      setSelectedPropertyCode(property.code);
      setActionMessage(`${property.name} ${nextStatus ? "activated" : "deactivated"}.`);
      setError("");
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  function startOnboarding(property: HotelProperty) {
    setPropertyCode(property.code);
    setSelectedPropertyCode(property.code);
    setPropertyForm(property);
    setActiveTab("property");
    setPropertyMode("onboard");
    setWorkflowNextAction("Manage Rooms");
    setActionMessage(`Onboarding started for ${property.name}. Next: Manage Rooms.`);
    setError("");
  }

  async function handleOnboardingStep(sectionKey: string) {
    const targetBySection: Record<string, AdminTab> = {
      room_types: "rooms",
      rooms: "rooms",
      rate_plans: "rates",
      tax_deposit: "rates",
      users_roles: "users",
      night_audit: "business_date",
    };
    if (sectionKey === "fnb_store") {
      openStoreItemsSetup(selectedProperty);
      return;
    }
    if (sectionKey === "go_live") {
      await runGoLiveCheck(selectedProperty);
      return;
    }
    const target = targetBySection[sectionKey];
    if (target) setActiveTab(target);
    try {
      await updateProperty(selectedPropertyCode, { onboardingStatus: "in_progress" });
      const nextBySection: Record<string, string> = {
        room_types: "Manage Rooms",
        rooms: "Manage Rates",
        rate_plans: "Manage Tax & Deposit",
        tax_deposit: "Manage Users",
        users_roles: "Manage Store Items",
        night_audit: "Run Go-Live Check",
      };
      setWorkflowNextAction(nextBySection[sectionKey] || "Manage Rooms");
      setActionMessage("Onboarding section opened. Continue setup in the active Admin workflow.");
      setError("");
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  function openPropertyDashboard(property: HotelProperty) {
    setPropertyCode(property.code);
    navigate("/dashboard");
  }

  function managePropertyTab(property: HotelProperty, tab: AdminTab) {
    setPropertyCode(property.code);
    setSelectedPropertyCode(property.code);
    setActiveTab(tab);
    setPropertyMode("view");
    setWorkflowNextAction(tab === "rooms" ? "Manage Rates" : tab === "rates" ? "Manage Users" : "Manage Store Items");
    const setupMessages: Partial<Record<AdminTab, string>> = {
      rooms: "Room setup opened. Room inventory backend is connected; room type management is currently represented through room inventory until the full room-type backend is connected.",
      rates: "Rate setup opened. BAR, Corporate, Group, Weekend, tax, service, deposit, and cancellation policy rules use the backend rate configuration when available.",
      users: "Users and roles setup opened. Supports Admin, GM, Front Desk, Housekeeping, Finance/Cashier, F&B Controller, and Storekeeper roles where seeded in backend permissions.",
    };
    setActionMessage(setupMessages[tab] || `${adminTabs[tab]} opened for ${property.name}.`);
    setError("");
  }

  function openStoreItemsSetup(property: HotelProperty) {
    setPropertyCode(property.code);
    setSelectedPropertyCode(property.code);
    setActiveTab("property");
    setPropertyMode("view");
    setWorkflowNextAction("Night Audit Setup");
    setActionMessage("F&B/store setup opened. Store item backend setup supports ingredients, units, unit price, and reorder controls from F&B Cost Control. Next: Night Audit Setup.");
    setError("");
  }

  function openTaxDepositSetup(property: HotelProperty) {
    setPropertyCode(property.code);
    setSelectedPropertyCode(property.code);
    setActiveTab("rates");
    setPropertyMode("view");
    setWorkflowNextAction("Manage Users");
    setActionMessage("Tax, service charge, deposit, and cancellation policy setup opened in Rates & Taxes. Next: Manage Users.");
    setError("");
  }

  function openNightAuditSetup(property: HotelProperty) {
    setPropertyCode(property.code);
    setSelectedPropertyCode(property.code);
    setActiveTab("business_date");
    setPropertyMode("view");
    setWorkflowNextAction("Run Go-Live Check");
    setActionMessage("Night Audit / Business Date setup opened. Backend night audit tables are used when available. Next: Run Go-Live Check.");
    setError("");
  }

  async function runGoLiveCheck(property: HotelProperty) {
    if (!property.id) {
      setError("Save this property to the backend before running Go-Live Check.");
      return;
    }
    try {
      setError("");
      const result = await fetchPropertyGoLiveCheck(property.id);
      setGoLiveChecks((current) => ({ ...current, [property.code]: result }));
      setSelectedPropertyCode(property.code);
      setActiveTab("property");
      setPropertyMode("view");
      setWorkflowNextAction(result.ready ? "Activate Live Property" : "Manage Rooms");
      setActionMessage(
        result.ready
          ? `${property.name}: ${result.label}. Next: Activate Live Property.`
          : `${property.name}: ${result.label}. ${result.blockers[0] || result.warnings[0] || "Review setup checks."}`
      );
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function activateLive(property: HotelProperty) {
    if (!property.id) {
      setError("Save this property to the backend before activating live operation.");
      return;
    }
    try {
      setError("");
      const result = await activateLiveProperty(property.id);
      syncProperty(result.property);
      setGoLiveChecks((current) => ({ ...current, [property.code]: result.go_live_check }));
      setSelectedPropertyCode(result.property.code);
      setActiveTab("property");
      setPropertyMode("view");
      setWorkflowNextAction("Open Dashboard");
      setActionMessage(`${result.property.name} is live and ready for hotel operations. Next: Open Dashboard.`);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function seedDemoRooms(property: HotelProperty) {
    if (!property.id) {
      setError("Save this property to the backend before adding rooms.");
      return;
    }
    try {
      setError("");
      const result = await seedPropertyDemoRooms(property.id);
      setPropertyCode(property.code);
      setSelectedPropertyCode(property.code);
      setActiveTab("rooms");
      setPropertyMode("view");
      setWorkflowNextAction("Manage Rates");
      setActionMessage(
        `${result.room_count} configured room(s) now exist for ${property.code}. Next: Manage Rates. Seeded: ${result.rooms
          .map((room) => `${room.room_number} ${room.room_type}`)
          .join(", ")}.`
      );
      setRooms(await fetchRoomStatusBoard(property.code, businessDate));
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function resetDemoRooms(property: HotelProperty) {
    if (!property.id) {
      setError("Save this property to the backend before resetting demo rooms.");
      return;
    }
    try {
      setError("");
      const result = await resetPropertyDemoRooms(property.id);
      setPropertyCode(property.code);
      setSelectedPropertyCode(property.code);
      setActiveTab("rooms");
      setPropertyMode("view");
      setWorkflowNextAction("Manage Rates");
      setActionMessage(
        `Demo room inventory reset for ${property.code}. ${result.room_count} demo room(s) remain for this property only.`
      );
      setRooms(await fetchRoomStatusBoard(property.code, businessDate));
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function assignAdmin(property: HotelProperty) {
    if (!property.id) {
      setError("Save this property to the backend before assigning user access.");
      return;
    }
    try {
      setError("");
      const result = await assignAdminToProperty(property.id);
      setWorkflowNextAction("Start Onboarding");
      setActionMessage(
        `${result.user_email} assigned to ${property.name}. User access is now valid for ${result.property_code}. Next: Start Onboarding.`
      );
      await loadRooms();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function continueWorkflow(action: string, property = selectedProperty) {
    if (action === "Start Onboarding") {
      startOnboarding(property);
      return;
    }
    if (action === "Manage Rooms") {
      managePropertyTab(property, "rooms");
      return;
    }
    if (action === "Manage Rates") {
      managePropertyTab(property, "rates");
      return;
    }
    if (action === "Manage Tax & Deposit") {
      openTaxDepositSetup(property);
      return;
    }
    if (action === "Manage Users") {
      managePropertyTab(property, "users");
      return;
    }
    if (action === "Manage Store Items") {
      openStoreItemsSetup(property);
      return;
    }
    if (action === "Night Audit Setup") {
      openNightAuditSetup(property);
      return;
    }
    if (action === "Run Go-Live Check") {
      await runGoLiveCheck(property);
      return;
    }
    if (action === "Activate Live Property") {
      await activateLive(property);
      return;
    }
    if (action === "Open Dashboard") {
      openPropertyDashboard(property);
    }
  }

  function WorkflowNextButton({ label, property = selectedProperty }: { label: string; property?: HotelProperty }) {
    return (
      <button className="primary-btn" type="button" onClick={() => continueWorkflow(label, property)}>
        Next: {label}
      </button>
    );
  }

  function updateRateConfigList<K extends keyof RateConfiguration>(
    key: K,
    index: number,
    field: string,
    value: string | number | boolean
  ) {
    if (!rateConfig) return;
    const rows = [...((rateConfig[key] as Array<Record<string, any>>) || [])];
    rows[index] = { ...rows[index], [field]: value };
    setRateConfig({ ...rateConfig, [key]: rows });
  }

  function exportAuditCsv() {
    const headers = ["created_at", "module", "action", "user_email", "record_type", "record_id"];
    const csv = [
      headers.join(","),
      ...auditLogs.map((row) =>
        headers
          .map((key) => `"${String((row as any)[key] ?? "").replace(/"/g, '""')}"`)
          .join(",")
      ),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `guzo-admin-audit-${propertyCode}-${businessDate}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="page-grid admin-command">
      <PageHeader
        title="Admin Command Center"
        subtitle="System control, security, configuration, audit, integrations, and governance."
        metadata={`${propertyCode} • ${propertyName} • ${businessDate}`}
        rightSlot={
          <>
            <div className="pill">{propertyCode}</div>
            <div className="pill">{propertyName}</div>
            <button className="small-btn" onClick={loadRooms}>Refresh</button>
          </>
        }
      />

      {loading ? (
        <LoadingState label="Loading admin configuration..." />
      ) : (
        <>
          {error ? <div className="error-box">{error}</div> : null}

          <div className="kpi-grid">
            <KpiCard label="System Health" value={overview?.system_health || "online"} />
            <KpiCard label="Business Date" value={businessDate} />
            <KpiCard label="Active Users" value={String(overview?.active_users ?? activeUsers)} />
            <KpiCard label="Failed Logins" value={String(overview?.failed_logins ?? 0)} />
            <KpiCard label="Admin Alerts" value={String(overview?.open_admin_alerts ?? 0)} />
            <KpiCard label="Integrations" value={`${overview?.integrations?.filter((row) => row.status === "online" || row.status === "configured").length ?? 0}/${overview?.integrations?.length ?? 0}`} />
            <KpiCard label="Reports Scheduled" value={String(overview?.scheduled_reports_count ?? 0)} />
            <KpiCard label="Notification Failures" value={String(overview?.notification_failures ?? 0)} />
            <KpiCard label="Night Audit" value={overview?.night_audit_status || "loading"} />
            <KpiCard label="Configured Rooms" value={String(rooms.length)} />
            <KpiCard label="Sellable Rooms" value={String(activeRooms)} />
            <KpiCard label="Enabled Payment Methods" value={String(enabledPayments)} />
          </div>

          <section className="admin-health-grid" aria-label="System health">
            {systemHealthCards.map((card) => (
              <div className={`admin-health-card ${card.tone}`} key={card.label}>
                <div>
                  <span>{card.label}</span>
                  <strong>{card.value}</strong>
                </div>
                <p>{card.detail}</p>
              </div>
            ))}
          </section>

          <div className="workflow-tabs">
            {(Object.keys(adminTabs) as AdminTab[]).map((tab) => (
              <button
                className={`tab-btn ${activeTab === tab ? "active" : ""}`}
                key={tab}
                onClick={() => setActiveTab(tab)}
                type="button"
              >
                {adminTabs[tab]}
              </button>
            ))}
          </div>

          {activeTab === "overview" ? (
            <div className="page-grid two-col">
              <div className="card">
                <h2 style={{ marginTop: 0 }}>Daily Admin Health Check</h2>
                <div className="muted" style={{ marginBottom: "14px" }}>
                  Admin confirms the PMS is configured, secure, and ready for hotel operations.
                </div>
                <div className="workflow-list">
                  {(overview?.admin_alerts || []).map((alert, index) => (
                    <div className="workflow-row" key={`${alert.message}-${index}`}>
                      <div>
                        <strong>{alert.message}</strong>
                        <div className="muted">{alert.action}</div>
                      </div>
                      <span className={`pill ${alert.severity === "critical" ? "pill-danger" : "pill-warning"}`}>
                        {alert.severity}
                      </span>
                    </div>
                  ))}
                  {overview?.admin_alerts?.length ? null : <div className="muted">No open admin alerts.</div>}
                </div>
              </div>

              <div className="card">
                <h2 style={{ marginTop: 0 }}>System Status</h2>
                <div className="dashboard-metric-strip compact-four">
                  <div><span>Backend</span><strong>{overview?.backend_status || "online"}</strong></div>
                  <div><span>Database</span><strong>{overview?.database_status || "online"}</strong></div>
                  <div><span>Frontend</span><strong>{overview?.frontend_status || "online"}</strong></div>
                  <div><span>Business Date</span><strong>{overview?.business_date_status || "open"}</strong></div>
                </div>
              </div>
            </div>
          ) : null}

          {activeTab === "users" ? (
          <div className="page-grid two-col">
            <div className="card">
              <h2 style={{ marginTop: 0 }}>User Access Control</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Role-based access control for hotel operations. Sensitive changes are written to PMS audit logs.
              </div>
              {actionMessage ? <div className="notice-box" style={{ marginBottom: "14px" }}>{actionMessage}</div> : null}
              <div className="dashboard-metric-strip compact-four" style={{ marginBottom: "14px" }}>
                <div><span>Active Users</span><strong>{activeUsers}</strong></div>
                <div><span>Roles</span><strong>{adminRoles.length}</strong></div>
                <div><span>Property</span><strong>{propertyCode}</strong></div>
                <div><span>Audit</span><strong>Enabled</strong></div>
              </div>

              <DataTable
                rows={adminUsers}
                emptyMessage="No users configured."
                columns={[
                  {
                    key: "full_name",
                    header: "Full Name",
                    render: (row) => row.full_name,
                  },
                  {
                    key: "email",
                    header: "Email",
                    render: (row) => row.email,
                  },
                  {
                    key: "role_key",
                    header: "Role",
                    render: (row) => {
                      const role = adminRoles.find((item) => item.role_key === row.role_key);
                      return (
                        <div>
                          <strong>{role?.role_name || row.role_key}</strong>
                          <div className="muted">{row.role_key}</div>
                        </div>
                      );
                    },
                  },
                  {
                    key: "is_active",
                    header: "Status",
                    render: (row) => (
                      <StatusBadge status={row.is_active ? "active" : "inactive"} />
                    ),
                  },
                  {
                    key: "actions",
                    header: "Actions",
                    render: (row) => (
                      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                        <button className="small-btn" type="button" onClick={() => handleResetPassword(row.id)}>
                          Reset
                        </button>
                        <button
                          className="small-btn"
                          disabled={!row.is_active}
                          type="button"
                          onClick={() => handleDisableUser(row.id)}
                        >
                          Disable
                        </button>
                      </div>
                    ),
                  },
                ]}
              />
            </div>

            <div className="card">
              <h2 style={{ marginTop: 0 }}>Create PMS User</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Use named user accounts only. Shared operational logins are not five-star audit standard.
              </div>

              <div className="pms-form-stack" style={{ marginBottom: "18px" }}>
                <input
                  aria-label="Full name"
                  placeholder="Full name"
                  value={userForm.full_name}
                  onChange={(event) => setUserForm((current) => ({ ...current, full_name: event.target.value }))}
                />
                <input
                  aria-label="Email"
                  placeholder="email@example.com"
                  value={userForm.email}
                  onChange={(event) => setUserForm((current) => ({ ...current, email: event.target.value }))}
                />
                <select
                  aria-label="Role"
                  value={userForm.role_key}
                  onChange={(event) => setUserForm((current) => ({ ...current, role_key: event.target.value }))}
                >
                  {adminRoles.map((role) => (
                    <option key={role.role_key} value={role.role_key}>
                      {role.role_name} ({role.role_key})
                    </option>
                  ))}
                </select>
                <button
                  className="small-btn"
                  disabled={!userForm.full_name.trim() || !userForm.email.trim()}
                  type="button"
                  onClick={handleCreateUser}
                >
                  Add User
                </button>
              </div>

              <h3>Hotel Roles</h3>
              <DataTable
                rows={adminRoles}
                emptyMessage="No roles configured."
                columns={[
                  { key: "role_name", header: "Role", render: (row) => row.role_name },
                  { key: "role_key", header: "Key", render: (row) => row.role_key },
                  { key: "description", header: "Purpose", render: (row) => row.description || "-" },
                ]}
              />

              <div style={{ display: "grid", gap: "12px" }}>
                <div
                  className="card"
                  style={{ padding: "14px", background: "rgba(2,6,23,0.35)" }}
                >
                  <div className="muted" style={{ fontSize: "13px" }}>
                    Property Name
                  </div>
                  <div style={{ fontSize: "18px", fontWeight: 700, marginTop: "6px" }}>
                    {propertyName}
                  </div>
                </div>

                <div
                  className="card"
                  style={{ padding: "14px", background: "rgba(2,6,23,0.35)" }}
                >
                  <div className="muted" style={{ fontSize: "13px" }}>
                    Property Code
                  </div>
                  <div style={{ fontSize: "18px", fontWeight: 700, marginTop: "6px" }}>
                    {propertyCode}
                  </div>
                </div>

                <div
                  className="card"
                  style={{ padding: "14px", background: "rgba(2,6,23,0.35)" }}
                >
                  <div className="muted" style={{ fontSize: "13px" }}>
                    Business Date Context
                  </div>
                  <div style={{ fontSize: "18px", fontWeight: 700, marginTop: "6px" }}>
                    {businessDate}
                  </div>
                </div>

                <div
                  className="card"
                  style={{ padding: "14px", background: "rgba(2,6,23,0.35)" }}
                >
                  <div className="muted" style={{ fontSize: "13px" }}>Admin Scope</div>
                  <div style={{ marginTop: "8px", lineHeight: "1.7" }}>
                    • Users and roles
                    <br />
                    • Room inventory
                    <br />
                    • Payment method setup
                    <br />
                    • Hotel operations standards
                  </div>
                </div>
              </div>
              <div className="workflow-next-row">
                <WorkflowNextButton label="Manage Store Items" />
              </div>
            </div>
            </div>
          ) : null}

          {activeTab === "property" ? (
            <div className="page-grid">
              <div className="card">
                <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center", marginBottom: "14px", flexWrap: "wrap" }}>
                  <div>
                    <h2 style={{ marginTop: 0, marginBottom: "4px" }}>Property Command Center</h2>
                    <div className="muted">
                      Create, activate, onboard, and route each hotel property into daily PMS operations.
                    </div>
                  </div>
                  <button className="primary-btn" type="button" onClick={startAddProperty}>
                    Add Property
                  </button>
                </div>

                {actionMessage ? <div className="notice-box" style={{ marginBottom: "14px" }}>{actionMessage}</div> : null}

                <div className="dashboard-metric-strip compact-four">
                  <div><span>Properties</span><strong>{propertyOptions.length}</strong></div>
                  <div><span>Active</span><strong>{propertyOptions.filter((property) => property.isActive).length}</strong></div>
                  <div><span>Selected</span><strong>{selectedProperty.code}</strong></div>
                  <div><span>Currency</span><strong>{selectedProperty.currency}</strong></div>
                </div>
                <div className="workflow-step-strip" aria-label="New property onboarding flow">
                  {propertyWorkflowSteps.map((step, index) => (
                    <button
                      className="workflow-step"
                      key={step}
                      type="button"
                      onClick={() => continueWorkflow(step)}
                      disabled={step === "Save Property"}
                    >
                      <span>{index + 1}</span>
                      <strong>{step}</strong>
                    </button>
                  ))}
                </div>
              </div>

              <div className="property-command-grid">
                {propertyOptions.map((property) => (
                  <div className="card property-command-card" key={property.code}>
                    {(() => {
                      const goLive = goLiveChecks[property.code];
                      return (
                        <>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "flex-start" }}>
                      <div>
                        <div className="muted" style={{ fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.08em" }}>{property.code}</div>
                        <h3 style={{ margin: "5px 0 6px" }}>{property.name}</h3>
                        <div className="muted">{property.city}, {property.country} | {property.timezone}</div>
                      </div>
                      <StatusBadge status={property.isActive ? "active" : "inactive"} />
                    </div>

                    <div className="dashboard-metric-strip compact-four" style={{ marginTop: "14px" }}>
                      <div><span>Rooms</span><strong>{property.code === propertyCode ? rooms.length : "-"}</strong></div>
                      <div><span>Onboarding</span><strong>{property.onboardingStatus?.replace("_", " ") || "not started"}</strong></div>
                      <div><span>Phone</span><strong>{property.phone || "-"}</strong></div>
                      <div><span>Email</span><strong>{property.email || "-"}</strong></div>
                    </div>

                    {goLive ? (
                      <div className={`go-live-result ${goLive.status}`}>
                        <strong>{goLive.label}</strong>
                        <span>
                          {goLive.blockers[0] || goLive.warnings[0] || "All required setup checks passed."}
                        </span>
                      </div>
                    ) : null}

                    <div className="property-action-grid" aria-label={`${property.name} property actions`}>
                      <button className="small-btn" type="button" onClick={() => selectProperty(property, "view")}>View Property</button>
                      <button className="small-btn" type="button" onClick={() => selectProperty(property, "edit")}>Edit Property</button>
                      <button className="small-btn" type="button" onClick={() => togglePropertyStatus(property)}>
                        {property.isActive ? "Deactivate" : "Activate"}
                      </button>
                      <button className="small-btn" type="button" onClick={() => startOnboarding(property)}>Start Onboarding</button>
                      <button className="small-btn" type="button" onClick={() => openPropertyDashboard(property)}>Open Dashboard</button>
                      <button className="small-btn" type="button" onClick={() => managePropertyTab(property, "rooms")}>Manage Rooms</button>
                      <button className="small-btn" type="button" onClick={() => assignAdmin(property)}>Assign Admin to Property</button>
                      <button className="small-btn" type="button" onClick={() => seedDemoRooms(property)}>Seed Demo Rooms</button>
                      <button className="small-btn" type="button" onClick={() => resetDemoRooms(property)}>Reset Demo Rooms for Selected Property</button>
                      <button className="small-btn" type="button" onClick={() => managePropertyTab(property, "rates")}>Manage Rates</button>
                      <button className="small-btn" type="button" onClick={() => openTaxDepositSetup(property)}>Manage Tax & Deposit</button>
                      <button className="small-btn" type="button" onClick={() => managePropertyTab(property, "users")}>Manage Users</button>
                      <button className="small-btn" type="button" onClick={() => openStoreItemsSetup(property)}>Manage Store Items</button>
                      <button className="small-btn" type="button" onClick={() => openNightAuditSetup(property)}>Night Audit Setup</button>
                      <button className="small-btn" type="button" onClick={() => runGoLiveCheck(property)}>Run Go-Live Check</button>
                      <button className="small-btn" type="button" onClick={() => activateLive(property)}>Activate Live Property</button>
                    </div>
                    </>
                      );
                    })()}
                  </div>
                ))}
              </div>

              {propertyMode === "add" || propertyMode === "edit" ? (
                <div className="card">
                  <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center", marginBottom: "14px", flexWrap: "wrap" }}>
                    <div>
                      <h2 style={{ marginTop: 0, marginBottom: "4px" }}>
                        {propertyMode === "add" ? "Add Hotel Property" : `Edit ${propertyForm.name}`}
                      </h2>
                      <div className="muted">Required property profile used by selectors, admin routing, reports, and operations context.</div>
                    </div>
                    <button className="small-btn" type="button" onClick={() => setPropertyMode("view")}>Close</button>
                  </div>

                  <div className="property-form-grid">
                    <label className="field"><span>Hotel Name</span><input value={propertyForm.name} onChange={(event) => updatePropertyForm("name", event.target.value)} /></label>
                    <label className="field"><span>Property Code</span><input value={propertyForm.code} disabled={propertyMode === "edit"} onChange={(event) => updatePropertyForm("code", event.target.value.toUpperCase())} /></label>
                    <label className="field"><span>Address</span><input value={propertyForm.address} onChange={(event) => updatePropertyForm("address", event.target.value)} /></label>
                    <label className="field"><span>City</span><input value={propertyForm.city} onChange={(event) => updatePropertyForm("city", event.target.value)} /></label>
                    <label className="field"><span>Country</span><input value={propertyForm.country} onChange={(event) => updatePropertyForm("country", event.target.value)} /></label>
                    <label className="field"><span>Timezone</span><input value={propertyForm.timezone} onChange={(event) => updatePropertyForm("timezone", event.target.value)} /></label>
                    <label className="field"><span>Currency</span><input maxLength={3} value={propertyForm.currency} onChange={(event) => updatePropertyForm("currency", event.target.value.toUpperCase())} /></label>
                    <label className="field"><span>Phone</span><input value={propertyForm.phone} onChange={(event) => updatePropertyForm("phone", event.target.value)} /></label>
                    <label className="field"><span>Email</span><input type="email" value={propertyForm.email} onChange={(event) => updatePropertyForm("email", event.target.value)} /></label>
                    <label className="field property-active-toggle">
                      <span>Active Status</span>
                      <select value={propertyForm.isActive ? "active" : "inactive"} onChange={(event) => updatePropertyForm("isActive", event.target.value === "active")}>
                        <option value="active">Active</option>
                        <option value="inactive">Inactive</option>
                      </select>
                    </label>
                  </div>

                  <div style={{ display: "flex", gap: "10px", marginTop: "16px", flexWrap: "wrap" }}>
                    <button className="primary-btn" type="button" onClick={handleSaveProperty}>Save Property</button>
                    <button className="small-btn" type="button" onClick={() => setPropertyMode("view")}>Cancel</button>
                  </div>
                </div>
              ) : null}

              {propertyMode === "view" ? (
                <div className="card">
                  <h2 style={{ marginTop: 0 }}>Property Detail</h2>
                  <div className="source-matrix">
                    <div className="source-row"><strong>Hotel</strong><span>{selectedProperty.name}</span></div>
                    <div className="source-row"><strong>Code</strong><span>{selectedProperty.code}</span></div>
                    <div className="source-row"><strong>Address</strong><span>{selectedProperty.address}, {selectedProperty.city}, {selectedProperty.country}</span></div>
                    <div className="source-row"><strong>Timezone / Currency</strong><span>{selectedProperty.timezone} / {selectedProperty.currency}</span></div>
                    <div className="source-row"><strong>Contact</strong><span>{selectedProperty.phone} / {selectedProperty.email}</span></div>
                  </div>
                  <div className="workflow-next-row">
                    <WorkflowNextButton label={workflowNextAction} />
                  </div>
                </div>
              ) : null}

              {propertyMode === "onboard" ? (
                <div className="card">
                  <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center", marginBottom: "14px", flexWrap: "wrap" }}>
                    <div>
                      <h2 style={{ marginTop: 0, marginBottom: "4px" }}>Onboard {selectedProperty.name}</h2>
                      <div className="muted">Complete the operating setup before the hotel goes live in daily PMS workflows.</div>
                    </div>
                    <button
                      className="small-btn"
                      type="button"
                      onClick={async () => {
                        try {
                          await updateProperty(selectedProperty.code, { onboardingStatus: "complete" });
                          setActionMessage(`${selectedProperty.name} onboarding marked complete.`);
                          setError("");
                        } catch (err) {
                          setError(getErrorMessage(err));
                        }
                      }}
                    >
                      Mark Complete
                    </button>
                  </div>
                  <div className="onboarding-grid">
                    {onboardingSections.map((section) => (
                      <button className="onboarding-card" key={section.key} type="button" onClick={() => handleOnboardingStep(section.key)}>
                        <strong>{section.title}</strong>
                        <span>{section.detail}</span>
                      </button>
                    ))}
                  </div>
                  <div className="workflow-next-row">
                    <WorkflowNextButton label="Manage Rooms" />
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}

          {activeTab === "permissions" ? (
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Permissions Matrix</h2>
              <DataTable
                rows={permissions.length ? permissions : (overview?.permissions_matrix as AdminPermissionRow[]) || []}
                emptyMessage="No permissions configured."
                columns={[
                  { key: "role_name", header: "Role", render: (row) => row.role_name || row.role_key },
                  { key: "role_key", header: "Key", render: (row) => row.role_key },
                  { key: "permissions", header: "Allowed Permissions", render: (row) => (row.permissions || []).join(", ") },
                ]}
              />
            </div>
          ) : null}

          {activeTab === "rooms" ? (
          <div className="card">
            <h2 style={{ marginTop: 0 }}>Room Inventory Setup</h2>
            <div className="muted" style={{ marginBottom: "14px" }}>
              Live inventory and room operational availability for {propertyName} / {propertyCode}. Demo/dev rows are scoped by property code and can be reset from Property Setup without touching other properties.
            </div>

            <DataTable
              rows={rooms}
              emptyMessage="No room inventory configured."
              columns={[
                {
                  key: "room_number",
                  header: "Room",
                  render: (row) => row.room_number,
                },
                {
                  key: "floor",
                  header: "Floor",
                  render: (row) => row.floor,
                },
                {
                  key: "room_type",
                  header: "Room Type",
                  render: (row) => roomTypeFromNumber(row.room_number),
                },
                {
                  key: "hk_status",
                  header: "Status",
                  render: (row) => <StatusBadge status={row.hk_status} />,
                },
                {
                  key: "occupied",
                  header: "Occupied",
                  render: (row) => (row.is_occupied ? "Yes" : "No"),
                },
              ]}
            />
            <div className="workflow-next-row">
              <button className="small-btn" type="button" onClick={() => seedDemoRooms(selectedProperty)}>
                Add Demo Rooms
              </button>
              <WorkflowNextButton label="Manage Rates" />
            </div>
          </div>
          ) : null}

          {activeTab === "payments" ? (
          <div className="card">
            <h2 style={{ marginTop: 0 }}>Payment Method Configuration</h2>
            <div className="muted" style={{ marginBottom: "14px" }}>
              Finance configuration for cashier and folio operations
            </div>

            <DataTable
              rows={paymentMethods}
              emptyMessage="No payment methods configured."
              columns={[
                {
                  key: "method",
                  header: "Method",
                  render: (row) => row.method,
                },
                {
                  key: "category",
                  header: "Category",
                  render: (row) => row.category,
                },
                {
                  key: "status",
                  header: "Status",
                  render: (row) => <StatusBadge status={row.status} />,
                },
              ]}
            />
          </div>
          ) : null}

          {activeTab === "rates" ? (
            <div className="page-grid">
              <div className="card">
                <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center", marginBottom: "14px" }}>
                  <div>
                    <h2 style={{ marginTop: 0, marginBottom: "4px" }}>Rates, Taxes & Charges</h2>
                    <div className="muted">
                      Manager-controlled pricing rules used by Booking Hub quotes and public request conversion.
                    </div>
                  </div>
                  <button className="primary-btn" type="button" onClick={handleSaveRateConfiguration} disabled={!rateConfig}>
                    Save Rate Rules
                  </button>
                </div>
                {actionMessage ? <div className="notice-box" style={{ marginBottom: "14px" }}>{actionMessage}</div> : null}
                <div className="dashboard-metric-strip compact-four">
                  <div><span>Rate Plans</span><strong>{rateConfig?.rate_plans.length ?? 0}</strong></div>
                  <div><span>Room Rates</span><strong>{rateConfig?.room_type_rates.length ?? 0}</strong></div>
                  <div><span>Tax Rules</span><strong>{rateConfig?.tax_service_rules.length ?? 0}</strong></div>
                  <div><span>Deposit Policies</span><strong>{rateConfig?.deposit_policies.length ?? 0}</strong></div>
                </div>
              </div>

              <div className="page-grid two-col">
                <div className="card">
                  <h3 style={{ marginTop: 0 }}>Room Type Rates</h3>
                  <div className="source-matrix">
                    {(rateConfig?.room_type_rates || []).map((row, index) => (
                      <div className="source-row" key={row.room_type}>
                        <strong>{row.room_type}</strong>
                        <input
                          aria-label={`${row.room_type} base rate`}
                          min="0"
                          type="number"
                          value={row.base_rate_etb}
                          onChange={(event) =>
                            updateRateConfigList("room_type_rates", index, "base_rate_etb", Number(event.target.value))
                          }
                        />
                      </div>
                    ))}
                  </div>
                </div>

                <div className="card">
                  <h3 style={{ marginTop: 0 }}>Rate Plans</h3>
                  <div className="source-matrix">
                    {(rateConfig?.rate_plans || []).map((row, index) => (
                      <div className="source-row" key={row.code}>
                        <div>
                          <strong>{row.code}</strong>
                          <div className="muted">{row.name}</div>
                        </div>
                        <input
                          aria-label={`${row.code} multiplier`}
                          min="0"
                          step="0.01"
                          type="number"
                          value={row.multiplier}
                          onChange={(event) =>
                            updateRateConfigList("rate_plans", index, "multiplier", Number(event.target.value))
                          }
                        />
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="page-grid two-col">
                <div className="card">
                  <h3 style={{ marginTop: 0 }}>Tax / Service Rules</h3>
                  <div className="source-matrix">
                    {(rateConfig?.tax_service_rules || []).map((row, index) => (
                      <div className="source-row" key={row.rule_name}>
                        <strong>{row.rule_name}</strong>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                          <input
                            aria-label={`${row.rule_name} service charge`}
                            min="0"
                            step="0.01"
                            type="number"
                            value={row.service_charge_percent}
                            onChange={(event) =>
                              updateRateConfigList("tax_service_rules", index, "service_charge_percent", Number(event.target.value))
                            }
                          />
                          <input
                            aria-label={`${row.rule_name} tax`}
                            min="0"
                            step="0.01"
                            type="number"
                            value={row.tax_percent}
                            onChange={(event) =>
                              updateRateConfigList("tax_service_rules", index, "tax_percent", Number(event.target.value))
                            }
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="card">
                  <h3 style={{ marginTop: 0 }}>Season / Weekend Rules</h3>
                  <div className="source-matrix">
                    {(rateConfig?.season_rules || []).map((row, index) => (
                      <div className="source-row" key={`${row.id}-${row.rule_name}`}>
                        <div>
                          <strong>{row.rule_name}</strong>
                          <div className="muted">Months {row.start_month} to {row.end_month}</div>
                        </div>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                          <input
                            aria-label={`${row.rule_name} seasonal surcharge`}
                            min="0"
                            step="0.01"
                            type="number"
                            value={row.surcharge_percent}
                            onChange={(event) =>
                              updateRateConfigList("season_rules", index, "surcharge_percent", Number(event.target.value))
                            }
                          />
                          <input
                            aria-label={`${row.rule_name} weekend surcharge`}
                            min="0"
                            step="0.01"
                            type="number"
                            value={row.weekend_surcharge_percent}
                            onChange={(event) =>
                              updateRateConfigList("season_rules", index, "weekend_surcharge_percent", Number(event.target.value))
                            }
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="card">
                <h3 style={{ marginTop: 0 }}>Deposit Policies & Cancellation Text</h3>
                <div className="source-matrix">
                  {(rateConfig?.deposit_policies || []).map((row, index) => (
                    <div className="source-row" key={row.rate_code}>
                      <div>
                        <strong>{row.rate_code}</strong>
                        <label style={{ display: "flex", gap: "8px", alignItems: "center", marginTop: "8px" }}>
                          <input
                            checked={row.guarantee_required}
                            type="checkbox"
                            onChange={(event) =>
                              updateRateConfigList("deposit_policies", index, "guarantee_required", event.target.checked)
                            }
                          />
                          <span>Guarantee required</span>
                        </label>
                      </div>
                      <div style={{ display: "grid", gap: "8px" }}>
                        <input
                          aria-label={`${row.rate_code} deposit percent`}
                          min="0"
                          step="0.01"
                          type="number"
                          value={row.deposit_percent}
                          onChange={(event) =>
                            updateRateConfigList("deposit_policies", index, "deposit_percent", Number(event.target.value))
                          }
                        />
                        <textarea
                          aria-label={`${row.rate_code} policy text`}
                          value={row.policy_text || ""}
                          onChange={(event) =>
                            updateRateConfigList("deposit_policies", index, "policy_text", event.target.value)
                          }
                        />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="workflow-next-row">
                  <WorkflowNextButton label="Manage Users" />
                </div>
              </div>
            </div>
          ) : null}

          {activeTab === "business_date" ? (
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Business Date & Night Audit Control</h2>
              <div className="dashboard-metric-strip compact-four">
                <div><span>Business Date</span><strong>{businessDate}</strong></div>
                <div><span>Night Audit</span><strong>{overview?.night_audit_status}</strong></div>
                <div><span>Blocking</span><strong>{overview?.night_audit_blocking ?? 0}</strong></div>
                <div><span>Warnings</span><strong>{overview?.night_audit_warnings ?? 0}</strong></div>
              </div>
              <div className="workflow-next-row">
                <WorkflowNextButton label="Run Go-Live Check" />
              </div>
            </div>
          ) : null}

          {activeTab === "reports" ? (
            <div className="page-grid two-col">
              <div className="card">
                <h2 style={{ marginTop: 0 }}>Report Archive</h2>
                <DataTable
                  rows={overview?.report_archive || []}
                  emptyMessage="No archived reports found."
                  columns={[
                    { key: "report_name", header: "Report", render: (row: any) => row.report_name },
                    { key: "status", header: "Status", render: (row: any) => row.status },
                    { key: "generated_at", header: "Generated", render: (row: any) => row.generated_at || "-" },
                  ]}
                />
              </div>
              <div className="card">
                <h2 style={{ marginTop: 0 }}>Scheduled Reports</h2>
                <DataTable
                  rows={overview?.scheduled_reports || []}
                  emptyMessage="No scheduled reports found."
                  columns={[
                    { key: "report_name", header: "Report", render: (row: any) => row.report_name },
                    { key: "recipient_email", header: "Recipient", render: (row: any) => row.recipient_email },
                    { key: "schedule_time", header: "Time", render: (row: any) => row.schedule_time || "-" },
                  ]}
                />
              </div>
            </div>
          ) : null}

          {activeTab === "integrations" ? (
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Integrations</h2>
              <DataTable
                rows={overview?.integrations || []}
                emptyMessage="No integrations configured."
                columns={[
                  { key: "name", header: "Integration", render: (row: any) => row.name },
                  { key: "status", header: "Status", render: (row: any) => <StatusBadge status={row.status} /> },
                  { key: "secret", header: "Secret Present", render: (row: any) => row.secret_present ? "Yes" : "No" },
                ]}
              />
            </div>
          ) : null}

          {activeTab === "notifications" ? (
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Notification Outbox</h2>
              <div className="dashboard-metric-strip compact-four">
                <div><span>Pending</span><strong>{overview?.notification_outbox?.pending ?? 0}</strong></div>
                <div><span>Failed</span><strong>{overview?.notification_outbox?.failed ?? 0}</strong></div>
              </div>
            </div>
          ) : null}

          {activeTab === "audit_logs" ? (
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center", marginBottom: "14px" }}>
                <div>
                  <h2 style={{ marginTop: 0, marginBottom: "4px" }}>Audit Logs</h2>
                  <div className="muted">Traceable PMS control actions for security, finance, reservations, and Admin governance.</div>
                </div>
                <button className="small-btn" type="button" onClick={exportAuditCsv}>
                  Export CSV
                </button>
              </div>
              <DataTable
                rows={auditLogs.length ? auditLogs : (overview?.audit_logs as PmsAuditLog[]) || []}
                emptyMessage="No audit logs found."
                columns={[
                  { key: "created_at", header: "Created", render: (row) => row.created_at || "-" },
                  { key: "module", header: "Module", render: (row) => row.module || "-" },
                  { key: "action", header: "Action", render: (row) => row.action || "-" },
                  { key: "user_email", header: "User", render: (row) => row.user_email || "-" },
                  { key: "entity", header: "Record", render: (row) => `${row.record_type || "-"} #${row.record_id || "-"}` },
                ]}
              />
            </div>
          ) : null}

          {activeTab === "security" ? (
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Security & Compliance</h2>
              <div className="sop-list">
                <div className="sop-item"><span className="pill pill-success">standard</span> Unique user accounts required for audit traceability.</div>
                <div className="sop-item"><span className="pill pill-warning">policy</span> Do not expose API keys, Telegram tokens, or passwords in logs.</div>
                <div className="sop-item"><span className="pill pill-warning">policy</span> Passport/ID capture belongs at secure Front Desk Check-In, not Telegram chat.</div>
              </div>
            </div>
          ) : null}

          {activeTab === "backup" ? (
            <div className="card">
              <h2 style={{ marginTop: 0 }}>Backup / Export</h2>
              <div className="dashboard-metric-strip compact-four">
                <div><span>Status</span><strong>{overview?.backup?.status || "manual_export_ready"}</strong></div>
                <div><span>Last Backup</span><strong>{overview?.backup?.last_backup_at || "Not configured"}</strong></div>
              </div>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
