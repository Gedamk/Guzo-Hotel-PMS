import { Navigate, Route, Routes } from "react-router-dom";
import PmsShell from "./layout/PmsShell";
import LoginPage from "./auth/LoginPage";
import DashboardPage from "./modules/dashboard/DashboardPage";
import ReservationsPage from "./modules/reservations/ReservationsPage";
import FrontDeskPage from "./modules/frontdesk/FrontDeskPage";
import HousekeepingPage from "./modules/housekeeping/HousekeepingPage";
import FinanceDashboard from "./modules/finance/FinanceDashboard";
import ReportsPage from "./modules/reports/ReportsPage";
import AdminPage from "./modules/admin/AdminPage";

export default function App() {
  return (
    <PmsShell>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/reservations" element={<ReservationsPage />} />
        <Route path="/frontdesk" element={<FrontDeskPage />} />
        <Route path="/housekeeping" element={<HousekeepingPage />} />
        <Route path="/finance" element={<FinanceDashboard />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </PmsShell>
  );
}
