import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import PmsShell from "./layout/PmsShell";
import LoginPage from "./auth/LoginPage";
import DashboardPage from "./modules/dashboard/DashboardPage";
import ReservationsPage from "./modules/reservations/ReservationsPage";
import FrontDeskPage from "./modules/frontdesk/FrontDeskPage";
import HousekeepingPage from "./modules/housekeeping/HousekeepingPage";
import FinanceDashboard from "./modules/finance/FinanceDashboard";
import ReportsPage from "./modules/reports/ReportsPage";
import NightAuditPage from "./modules/nightaudit/NightAuditPage";
import AdminPage from "./modules/admin/AdminPage";
import BookingAssistantPage from "./modules/booking/BookingAssistantPage";
import type { UserSession } from "./types/pms";
import FoodCostingPage from "./modules/foodcosting/FoodCostingPage";
function LoginRoute() {
  const navigate = useNavigate();

  function handleLogin(_session: UserSession) {
    navigate("/dashboard", { replace: true });
  }

  return <LoginPage onLogin={handleLogin} />;
}

export default function App() {
  return (
    <PmsShell>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/login" element={<LoginRoute />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/reservations" element={<ReservationsPage />} />
        <Route path="/frontdesk" element={<FrontDeskPage />} />
        <Route path="/housekeeping" element={<HousekeepingPage />} />
        <Route path="/finance" element={<FinanceDashboard />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/night-audit" element={<NightAuditPage />} />
        <Route path="/booking-assistant" element={<BookingAssistantPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
        <Route path="/food-costing" element={<FoodCostingPage />} />
      </Routes>
    </PmsShell>
  );
}
