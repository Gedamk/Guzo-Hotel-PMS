import { Suspense, lazy, type ComponentType } from "react";
import { Navigate, type RouteObject } from "react-router-dom";
import { LoadingState } from "../components/ui/LoadingState";

const DashboardPage = lazy(() => import("../modules/dashboard/DashboardPage"));
const ReservationDepartmentPage = lazy(
  () => import("../modules/reservations/ReservationDepartmentPage")
);
const FrontDeskCommandCenter = lazy(
  () => import("../modules/frontdesk/FrontDeskCommandCenter")
);
const HousekeepingCommandCenter = lazy(
  () => import("../modules/housekeeping/HousekeepingCommandCenter")
);
const GuestFeedbackPage = lazy(() => import("../modules/guestfeedback/GuestFeedbackPage"));
const GuestProfilesPage = lazy(() => import("../modules/guestprofiles/GuestProfilesPage"));
const FinanceDashboard = lazy(() => import("../modules/finance/FinanceDashboard"));
const ReportsPage = lazy(() => import("../modules/reports/ReportsPage"));
const NightAuditPage = lazy(() => import("../modules/nightaudit/NightAuditPage"));
const AdminPage = lazy(() => import("../modules/admin/AdminPage"));
const BookingAssistantPage = lazy(
  () => import("../modules/booking/BookingAssistantPage")
);
const AgentHarnessPage = lazy(() => import("../modules/agentharness/AgentHarnessPage"));
const CentralBookingHubPage = lazy(
  () => import("../modules/booking/CentralBookingHubPage")
);
const HotelBookingPage = lazy(() => import("../modules/booking/HotelBookingPage"));
const FoodCostingPage = lazy(() => import("../modules/foodcosting/FoodCostingPage"));
const ComingSoonPage = lazy(() => import("../modules/comingsoon/ComingSoonPage"));

function lazyElement(Page: ComponentType, label: string) {
  return (
    <Suspense fallback={<LoadingState label={`Loading ${label}...`} />}>
      <Page />
    </Suspense>
  );
}

export const pmsWorkflowRoutes: RouteObject[] = [
  { path: "/dashboard", element: lazyElement(DashboardPage, "Dashboard") },
  { path: "/frontdesk", element: lazyElement(FrontDeskCommandCenter, "Front Desk") },
  { path: "/frontdesk/:section", element: lazyElement(FrontDeskCommandCenter, "Front Desk") },
  {
    path: "/reservations",
    element: lazyElement(ReservationDepartmentPage, "Reservations"),
  },
  {
    path: "/reservations/:section",
    element: lazyElement(ReservationDepartmentPage, "Reservations"),
  },
  {
    path: "/housekeeping",
    element: lazyElement(HousekeepingCommandCenter, "Housekeeping"),
  },
  { path: "/guest-feedback", element: lazyElement(GuestFeedbackPage, "Guest Feedback") },
  { path: "/guest-profiles", element: lazyElement(GuestProfilesPage, "Guest Profiles") },
  { path: "/folio", element: lazyElement(FinanceDashboard, "Finance") },
  { path: "/food-costing", element: lazyElement(FoodCostingPage, "Food Costing") },
  { path: "/reports", element: lazyElement(ReportsPage, "Reports") },
  { path: "/night-audit", element: lazyElement(NightAuditPage, "Night Audit") },
  { path: "/booking", element: lazyElement(CentralBookingHubPage, "Booking Hub") },
  { path: "/booking/guest", element: lazyElement(HotelBookingPage, "Guest Booking") },
  { path: "/guest-ai", element: lazyElement(HotelBookingPage, "Guest AI") },
  {
    path: "/booking-assistant",
    element: lazyElement(BookingAssistantPage, "Booking Assistant"),
  },
  { path: "/agent-harness", element: lazyElement(AgentHarnessPage, "AI Assistant") },
  { path: "/admin", element: lazyElement(AdminPage, "Admin") },
  { path: "/coming-soon", element: lazyElement(ComingSoonPage, "Coming Soon") },
];

export const pmsCompatibilityRoutes: RouteObject[] = [
  { path: "/booking-hub", element: <Navigate to="/booking" replace /> },
  { path: "/finance", element: <Navigate to="/folio" replace /> },
  { path: "/store-control", element: lazyElement(FoodCostingPage, "Store Control") },
  { path: "/feedback", element: <Navigate to="/guest-feedback" replace /> },
  { path: "/service-recovery", element: <Navigate to="/guest-feedback" replace /> },
];
