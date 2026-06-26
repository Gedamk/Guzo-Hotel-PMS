import { NavLink } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { canAccessPath, getRoleLabel } from "../auth/accessControl";
import { HOTEL_NAME, NAV_ITEMS } from "../config/pms";
import { usePmsContext } from "../context/PmsContext";
import type { UserSession } from "../types/pms";

type PmsSidebarProps = {
  onLogout?: () => void;
  session: UserSession;
};

const NAV_GROUP_LABELS = {
  operations: "Operations",
  commercial: "Booking & Rates",
  controls: "Controls",
};

export default function PmsSidebar({ onLogout, session }: PmsSidebarProps) {
  const { propertyName, propertyCode, businessDate } = usePmsContext();
  const navGroups = Object.entries(NAV_GROUP_LABELS).map(([group, label]) => ({
    group,
    label,
    items: NAV_ITEMS.filter(
      (item) => item.group === group && canAccessPath(session, item.path)
    ),
  }));

  return (
    <aside className="sidebar">
      <div className="brand-block">
        <h1 className="brand-title">{HOTEL_NAME}</h1>
        <div className="brand-subtitle">Hotel Operations Console</div>
        <div className="sidebar-menu-toggle" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <div className="brand-property">{propertyName}</div>
        <div className="brand-property">Property: {propertyCode}</div>
        <div className="brand-property">Business Date: {businessDate}</div>
        <div className="brand-property">
          Access: {getRoleLabel(session.role)}
        </div>
      </div>

      <div className="sidebar-search" aria-label="Search in menu">
        Search In Menu
      </div>

      <div className="nav-group">
        {navGroups.map((section) =>
          section.items.length > 0 ? (
          <div className="nav-section" key={section.group}>
            <div className="nav-section-label">{section.label}</div>
            {section.items.map((item) => {
              const Icon = item.icon;

              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    isActive ? "nav-btn active" : "nav-btn"
                  }
                >
                  <Icon aria-hidden="true" className="nav-icon" size={18} />
                  <span>{item.label}</span>
                  <ChevronDown aria-hidden="true" className="nav-chevron" size={18} />
                </NavLink>
              );
            })}
          </div>
          ) : null
        )}
      </div>

      {onLogout ? (
        <button className="logout-btn" onClick={onLogout}>
          Sign Out
        </button>
      ) : null}
    </aside>
  );
}
