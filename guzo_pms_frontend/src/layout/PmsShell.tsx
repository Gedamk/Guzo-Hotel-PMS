import { NavLink } from "react-router-dom";
import { HOTEL_NAME, NAV_ITEMS } from "../config/pms";
import { usePmsContext } from "../context/PmsContext";
import PmsToolbar from "../components/PmsToolbar";

type PmsShellProps = {
  children: React.ReactNode;
  onLogout?: () => void;
};

export default function PmsShell({ children, onLogout }: PmsShellProps) {
  const { propertyName, propertyCode, businessDate } = usePmsContext();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <h1 className="brand-title">{HOTEL_NAME}</h1>
          <div className="brand-subtitle">Global hotel operations platform</div>
          <div className="brand-property">{propertyName}</div>
          <div className="brand-property">Property: {propertyCode}</div>
          <div className="brand-property">Business Date: {businessDate}</div>
        </div>

        <div className="nav-group">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                isActive ? "nav-btn active" : "nav-btn"
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>

        {onLogout ? (
          <button className="logout-btn" onClick={onLogout}>
            Sign Out
          </button>
        ) : null}
      </aside>

      <div className="main-panel">
        <div className="page-content">
          <PmsToolbar />
          {children}
        </div>
      </div>
    </div>
  );
}
