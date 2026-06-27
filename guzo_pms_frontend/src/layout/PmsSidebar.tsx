import { useEffect, useMemo, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { canAccessPath } from "../auth/accessControl";
import { HOTEL_NAME, PMS_NAV_GROUPS, type PmsNavGroup } from "../config/pms";
import type { UserSession } from "../types/pms";

type PmsSidebarProps = {
  onLogout?: () => void;
  session: UserSession;
};

function pathMatches(currentPath: string, candidates: string[]) {
  return candidates.some((path) => currentPath === path || currentPath.startsWith(`${path}/`));
}

function currentRoute(location: ReturnType<typeof useLocation>) {
  return `${location.pathname}${location.search}${location.hash}`;
}

function groupIsActive(group: PmsNavGroup, currentPath: string, activeFeature: string | null) {
  return (
    pathMatches(currentPath, group.activePaths) ||
    (currentPath === "/coming-soon" &&
      group.items.some((item) => item.comingSoon && item.label === activeFeature))
  );
}

function visibleGroups(session: UserSession) {
  return PMS_NAV_GROUPS.map((group) => {
    const canOpenParent = canAccessPath(session, group.path);
    const items = group.items.filter((item) =>
      item.comingSoon ? canOpenParent : canAccessPath(session, item.path)
    );
    return { ...group, canOpenParent, items };
  }).filter((group) => group.canOpenParent || group.items.length > 0);
}

export default function PmsSidebar({ onLogout, session }: PmsSidebarProps) {
  const location = useLocation();
  const route = currentRoute(location);
  const navGroups = useMemo(() => visibleGroups(session), [session]);
  const activeFeature = new URLSearchParams(location.search).get("feature");
  const initialOpen = useMemo(() => {
    const active = navGroups.find((group) => groupIsActive(group, location.pathname, activeFeature));
    return new Set(active ? [active.key] : navGroups.slice(0, 3).map((group) => group.key));
  }, [activeFeature, location.pathname, navGroups]);
  const [openGroups, setOpenGroups] = useState<Set<PmsNavGroup["key"]>>(initialOpen);

  useEffect(() => {
    const active = navGroups.find((group) => groupIsActive(group, location.pathname, activeFeature));
    if (!active) return;
    setOpenGroups((current) => {
      if (current.has(active.key)) return current;
      const next = new Set(current);
      next.add(active.key);
      return next;
    });
  }, [activeFeature, location.pathname, navGroups]);

  function toggleGroup(key: PmsNavGroup["key"]) {
    setOpenGroups((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function childIsActive(section: PmsNavGroup, itemPath: string, label: string, index: number) {
    if (itemPath.startsWith("/coming-soon")) {
      return location.pathname === "/coming-soon" && activeFeature === label;
    }
    if (itemPath.includes("?") || itemPath.includes("#")) {
      return route === itemPath;
    }
    if (location.pathname !== itemPath) return false;
    return section.items.findIndex((item) => item.path === itemPath && !item.comingSoon) === index;
  }

  return (
    <aside className="sidebar">
      <NavLink className="brand-block" to="/dashboard" aria-label="Open Guzo PMS dashboard">
        <span className="brand-mark" aria-hidden="true">G</span>
        <span className="brand-title">{HOTEL_NAME}</span>
      </NavLink>

      <div className="nav-group">
        {navGroups.map((section) => {
          const Icon = section.icon;
          const isOpen = openGroups.has(section.key);
          const isActive = groupIsActive(section, location.pathname, activeFeature);
          return (
            <div className="nav-section pms-menu-section" key={section.key}>
              <div className={`nav-btn-row ${isActive ? "active" : ""}`}>
                <NavLink
                  to={section.path}
                  className={`nav-btn pms-menu-parent ${isActive ? "active" : ""}`}
                  aria-current={isActive ? "page" : undefined}
                >
                  <Icon aria-hidden="true" className="nav-icon" size={22} />
                  <span>{section.label}</span>
                </NavLink>
                {section.items.length ? (
                  <button
                    type="button"
                    className="nav-chevron-btn"
                    onClick={() => toggleGroup(section.key)}
                    aria-label={`${isOpen ? "Collapse" : "Expand"} ${section.label} menu`}
                    aria-expanded={isOpen}
                  >
                    <ChevronDown aria-hidden="true" className="nav-chevron" size={16} />
                  </button>
                ) : null}
              </div>
              {isOpen ? (
                <div className="pms-submenu">
                  {section.items.length ? (
                    section.items.map((item, index) => (
                      <NavLink
                        key={`${section.key}-${item.label}`}
                        to={item.path}
                        className={
                          childIsActive(section, item.path, item.label, index)
                            ? `nav-subitem ${item.comingSoon ? "nav-subitem-soon " : ""}active`
                            : `nav-subitem ${item.comingSoon ? "nav-subitem-soon" : ""}`
                        }
                      >
                        <span>{item.label}</span>
                        {item.comingSoon ? <small>Soon</small> : null}
                      </NavLink>
                    ))
                  ) : (
                    <NavLink
                      to={section.path}
                      className={({ isActive: childActive }) =>
                        childActive ? "nav-subitem active" : "nav-subitem"
                      }
                    >
                      <span>Open {section.label}</span>
                    </NavLink>
                  )}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      {onLogout ? (
        <button className="logout-btn" onClick={onLogout}>
          Sign Out
        </button>
      ) : null}
    </aside>
  );
}
