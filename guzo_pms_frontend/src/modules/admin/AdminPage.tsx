import { useEffect, useMemo, useState } from "react";
import PageHeader from "../../components/PageHeader";
import KpiCard from "../../components/KpiCard";
import DataTable from "../../components/DataTable";
import { usePmsContext } from "../../context/PmsContext";
import { fetchRoomStatusBoard } from "../../services/pmsService";
import { getErrorMessage } from "../../services/http";
import type { RoomStatusItem } from "../../types/pms";

type UserRow = {
  username: string;
  fullName: string;
  role: "admin" | "manager" | "frontdesk" | "housekeeping" | "finance";
  status: "active" | "inactive";
};

type PaymentMethodRow = {
  method: string;
  category: string;
  status: "enabled" | "disabled";
};

function pillClass(status: string) {
  const s = String(status || "").toLowerCase();
  if (
    s === "active" ||
    s === "enabled" ||
    s === "vacant_clean" ||
    s === "vacant_inspected" ||
    s === "occupied_clean"
  ) {
    return "pill pill-success";
  }
  if (s === "inactive" || s === "disabled") return "pill pill-muted";
  if (s === "out_of_order" || s === "out_of_service") return "pill pill-warning";
  if (s.includes("dirty")) return "pill pill-danger";
  return "pill";
}

function roomTypeFromNumber(roomNumber: string) {
  const n = Number(roomNumber);
  if (!Number.isFinite(n)) return "Standard";
  if (n >= 300) return "Suite";
  if (n >= 200) return "Deluxe";
  return "Standard";
}

export default function AdminPage() {
  const { propertyCode, businessDate, propertyName, refreshKey } = usePmsContext();

  const [rooms, setRooms] = useState<RoomStatusItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [users] = useState<UserRow[]>([
    {
      username: "admin",
      fullName: "System Administrator",
      role: "admin",
      status: "active",
    },
    {
      username: "manager",
      fullName: "Duty Manager",
      role: "manager",
      status: "active",
    },
    {
      username: "frontdesk1",
      fullName: "Front Desk Agent",
      role: "frontdesk",
      status: "active",
    },
    {
      username: "housekeeping1",
      fullName: "Housekeeping Supervisor",
      role: "housekeeping",
      status: "active",
    },
    {
      username: "finance1",
      fullName: "Finance Cashier",
      role: "finance",
      status: "inactive",
    },
  ]);

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
      const data = await fetchRoomStatusBoard(propertyCode, businessDate);
      setRooms(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRooms();
  }, [propertyCode, businessDate, refreshKey]);

  const activeUsers = useMemo(
    () => users.filter((user) => user.status === "active").length,
    [users]
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

  return (
    <div className="page-grid">
      <PageHeader
        title="Admin"
        subtitle={`Property setup and governance for ${propertyCode} on ${businessDate}`}
        rightSlot={
          <>
            <div className="pill">{propertyCode}</div>
            <div className="pill">{propertyName}</div>
          </>
        }
      />

      {loading ? (
        <div className="card">Loading admin configuration...</div>
      ) : (
        <>
          {error ? <div className="error-box">{error}</div> : null}

          <div className="kpi-grid">
            <KpiCard label="Active Users" value={String(activeUsers)} />
            <KpiCard label="Configured Rooms" value={String(rooms.length)} />
            <KpiCard label="Sellable Rooms" value={String(activeRooms)} />
            <KpiCard label="Enabled Payment Methods" value={String(enabledPayments)} />
          </div>

          <div className="page-grid two-col">
            <div className="card">
              <h2 style={{ marginTop: 0 }}>User Access Control</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Role-based access control for hotel operations
              </div>

              <DataTable
                rows={users}
                emptyMessage="No users configured."
                columns={[
                  {
                    key: "username",
                    header: "Username",
                    render: (row) => row.username,
                  },
                  {
                    key: "fullName",
                    header: "Full Name",
                    render: (row) => row.fullName,
                  },
                  {
                    key: "role",
                    header: "Role",
                    render: (row) => row.role,
                  },
                  {
                    key: "status",
                    header: "Status",
                    render: (row) => (
                      <span className={pillClass(row.status)}>{row.status}</span>
                    ),
                  },
                ]}
              />
            </div>

            <div className="card">
              <h2 style={{ marginTop: 0 }}>Property Configuration</h2>
              <div className="muted" style={{ marginBottom: "14px" }}>
                Core setup summary for the selected property context
              </div>

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
            </div>
          </div>

          <div className="card">
            <h2 style={{ marginTop: 0 }}>Room Inventory Setup</h2>
            <div className="muted" style={{ marginBottom: "14px" }}>
              Live inventory and room operational availability from backend room board
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
                  render: (row) => (
                    <span className={pillClass(row.hk_status)}>{row.hk_status}</span>
                  ),
                },
                {
                  key: "occupied",
                  header: "Occupied",
                  render: (row) => (row.is_occupied ? "Yes" : "No"),
                },
              ]}
            />
          </div>

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
                  render: (row) => (
                    <span className={pillClass(row.status)}>{row.status}</span>
                  ),
                },
              ]}
            />
          </div>
        </>
      )}
    </div>
  );
}
