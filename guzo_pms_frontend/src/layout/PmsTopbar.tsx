import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import {
  BarChart3,
  BedDouble,
  CalendarDays,
  Clock,
  CreditCard,
  DollarSign,
  Grid3X3,
  Hand,
  PlaneLanding,
  RefreshCw,
  ShoppingCart,
  UserCircle2,
} from "lucide-react";
import { getRoleLabel } from "../auth/accessControl";
import { usePmsContext } from "../context/PmsContext";
import BusinessDateBar from "./BusinessDateBar";
import PropertySwitcher from "./PropertySwitcher";
import type { UserSession } from "../types/pms";

type PmsTopbarProps = {
  session: UserSession;
};

const quickModules = [
  { label: "Status", path: "/dashboard", icon: BarChart3 },
  { label: "Availability", path: "/reservations", icon: BedDouble },
  { label: "Rate Quote", path: "/reservations", icon: CreditCard },
  { label: "Rack", path: "/housekeeping", icon: Grid3X3 },
  { label: "Reservation", path: "/reservations", icon: PlaneLanding },
  { label: "Front Desk", path: "/frontdesk", icon: CalendarDays },
  { label: "Cashier", path: "/finance", icon: DollarSign },
  { label: "Booking Hub", path: "/booking-hub", icon: Hand },
  { label: "F&B Control", path: "/food-costing", icon: ShoppingCart },
  { label: "Store", path: "/store-control", icon: Grid3X3 },
  { label: "Tasks", path: "/night-audit", icon: Clock },
  { label: "Reports", path: "/reports", icon: BarChart3 },
];

export default function PmsTopbar({ session }: PmsTopbarProps) {
  const { propertyName, refreshData } = usePmsContext();
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <header className="pms-topbar">
      <div className="easypms-module-rail" aria-label="Main PMS shortcuts">
        {quickModules.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink key={item.label} to={item.path} className="easypms-module-link">
              <Icon aria-hidden="true" size={30} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </div>
      <div className="pms-topbar-actions">
        <PropertySwitcher />
        <BusinessDateBar />
        <div className="shell-control" title="Current time">
          <Clock aria-hidden="true" size={16} />
          <span>
            {new Intl.DateTimeFormat("en-US", {
              hour: "numeric",
              minute: "2-digit",
            }).format(now)}
          </span>
        </div>
        <button
          type="button"
          className="icon-text-btn"
          onClick={refreshData}
          aria-label="Refresh PMS data"
          title="Refresh PMS data"
        >
          <RefreshCw aria-hidden="true" size={16} />
          <span>Refresh</span>
        </button>
        <div className="language-box">EN</div>
        <div className="user-orb" title={`${session.username} | ${getRoleLabel(session.role)}`}>
          <UserCircle2 aria-hidden="true" size={30} />
        </div>
      </div>
      <div className="easypms-property-line">
        <strong>{propertyName}</strong>
        <span>{session.username} | {getRoleLabel(session.role)}</span>
      </div>
    </header>
  );
}
