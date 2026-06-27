import { useEffect, useMemo, useRef, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { Bell, Bot, ChevronDown, Menu, Search } from "lucide-react";
import { canAccessPath, getRoleLabel } from "../auth/accessControl";
import { PMS_NAV_GROUPS, type PmsNavGroup } from "../config/pms";
import { usePmsContext } from "../context/PmsContext";
import { fetchGlobalSearch } from "../services/pmsService";
import { getErrorMessage } from "../services/http";
import BusinessDateBar from "./BusinessDateBar";
import PropertySwitcher from "./PropertySwitcher";
import type { GlobalSearchResponse, UserSession } from "../types/pms";

type PmsTopbarProps = {
  session: UserSession;
};

export default function PmsTopbar({ session }: PmsTopbarProps) {
  const { propertyCode } = usePmsContext();
  const navigate = useNavigate();
  const location = useLocation();
  const searchRef = useRef<HTMLDivElement | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const notificationRef = useRef<HTMLDivElement | null>(null);
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [openTopGroup, setOpenTopGroup] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [searchResults, setSearchResults] = useState<GlobalSearchResponse | null>(null);
  const [avatarFailed, setAvatarFailed] = useState(false);
  const userDisplayName = session.full_name || session.username || session.email || "PMS User";
  const userInitials = getUserInitials(userDisplayName);
  const avatarSrc = session.avatar_url || "/user-avatar.svg";

  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      if (!searchRef.current?.contains(event.target as Node)) {
        setSearchOpen(false);
      }
      if (!notificationRef.current?.contains(event.target as Node)) {
        setNotificationsOpen(false);
      }
    };
    window.addEventListener("mousedown", onPointerDown);
    return () => window.removeEventListener("mousedown", onPointerDown);
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchInputRef.current?.focus();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    setAvatarFailed(false);
  }, [avatarSrc]);

  useEffect(() => {
    const trimmed = query.trim();
    setSearchError("");
    if (trimmed.length < 2) {
      setSearchResults(null);
      setSearching(false);
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        setSearching(true);
        const data = await fetchGlobalSearch(trimmed, propertyCode);
        if (!cancelled) {
          setSearchResults(data);
          setSearchOpen(true);
        }
      } catch (err) {
        if (!cancelled) {
          setSearchError(getErrorMessage(err));
          setSearchResults(null);
          setSearchOpen(true);
        }
      } finally {
        if (!cancelled) setSearching(false);
      }
    }, 280);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [propertyCode, query]);

  const totalResults = useMemo(
    () => searchResults?.groups.reduce((sum, group) => sum + group.results.length, 0) || 0,
    [searchResults]
  );
  const activeFeature = new URLSearchParams(location.search).get("feature");
  const activeRoute = `${location.pathname}${location.search}${location.hash}`;
  const navGroups = useMemo(() => {
    return PMS_NAV_GROUPS.map((group) => {
      const canOpenParent = canAccessPath(session, group.path);
      const items = group.items.filter((item) =>
        item.comingSoon ? canOpenParent : canAccessPath(session, item.path)
      );
      return { ...group, canOpenParent, items };
    }).filter((group) => group.canOpenParent || group.items.length > 0);
  }, [session]);

  function groupIsActive(group: PmsNavGroup) {
    return (
      group.activePaths.some(
        (path) => location.pathname === path || location.pathname.startsWith(`${path}/`)
      ) ||
      (location.pathname === "/coming-soon" &&
        group.items.some((item) => item.comingSoon && item.label === activeFeature))
    );
  }

  function childIsActive(path: string, label: string) {
    if (path.startsWith("/coming-soon")) {
      return location.pathname === "/coming-soon" && activeFeature === label;
    }
    if (path.includes("?") || path.includes("#")) {
      return activeRoute === path;
    }
    return location.pathname === path;
  }

  function openResult(targetRoute: string) {
    setSearchOpen(false);
    setQuery("");
    navigate(targetRoute || "/coming-soon?feature=Search Result");
  }

  async function runSearchNow() {
    const trimmed = query.trim();
    setSearchOpen(true);
    searchInputRef.current?.focus();

    if (trimmed.length < 2) {
      setSearchResults(null);
      setSearchError("Type at least 2 characters to search PMS records.");
      return;
    }

    try {
      setSearching(true);
      setSearchError("");
      const data = await fetchGlobalSearch(trimmed, propertyCode);
      setSearchResults(data);
    } catch (err) {
      setSearchResults(null);
      setSearchError(getErrorMessage(err));
    } finally {
      setSearching(false);
    }
  }

  return (
    <header className="pms-topbar pms-topbar-simple">
      <PropertySwitcher />

      <div className="topbar-search-wrap" ref={searchRef}>
        <div className="topbar-search" role="search">
          <Search aria-hidden="true" size={18} />
          <input
            ref={searchInputRef}
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setSearchOpen(true);
            }}
            onFocus={() => setSearchOpen(true)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void runSearchNow();
              }
            }}
            placeholder="Search PMS..."
            aria-label="Search Guzo PMS"
          />
          <button
            type="button"
            className="topbar-search-submit"
            onClick={() => void runSearchNow()}
            aria-label="Run PMS search"
            title="Search"
          >
            <Search aria-hidden="true" size={16} />
          </button>
        </div>

        {searchOpen && (query.trim().length >= 2 || searchError) ? (
          <div className="global-search-dropdown" role="listbox" aria-label="Global search results">
            {searching ? <div className="global-search-state">Searching Guzo PMS...</div> : null}
            {searchError ? <div className="global-search-state error">{searchError}</div> : null}
            {!searching && !searchError && searchResults && totalResults === 0 ? (
              <div className="global-search-state">No matching PMS records found.</div>
            ) : null}
            {!searching && !searchError && searchResults?.groups.map((group) =>
              group.results.length ? (
                <section className="global-search-group" key={group.key}>
                  <h3>{group.label}</h3>
                  {group.results.map((result) => (
                    <button
                      key={result.id}
                      type="button"
                      className="global-search-result"
                      onClick={() => openResult(result.target_route)}
                    >
                      <span>
                        <strong>{result.title}</strong>
                        <small>{result.subtitle}</small>
                      </span>
                      {result.status ? <em>{result.status.replace(/_/g, " ")}</em> : null}
                    </button>
                  ))}
                </section>
              ) : null
            )}
          </div>
        ) : null}
      </div>

      <div className="pms-topbar-main">
        <button
          type="button"
          className="pms-mobile-menu-btn"
          onClick={() => setMobileMenuOpen((current) => !current)}
          aria-expanded={mobileMenuOpen}
        >
          <Menu aria-hidden="true" size={18} />
          PMS Workflow
        </button>
        <nav className={`opera-topnav ${mobileMenuOpen ? "mobile-open" : ""}`} aria-label="PMS workflow navigation">
          {navGroups.map((group) => {
            const Icon = group.icon;
            const isActive = groupIsActive(group);
            return (
              <div className={`opera-topnav-group ${isActive ? "active" : ""}`} key={group.key}>
                {group.items.length ? (
                  <button
                    type="button"
                    className="opera-topnav-button"
                    onClick={() => setOpenTopGroup((current) => (current === group.key ? null : group.key))}
                    aria-expanded={openTopGroup === group.key}
                  >
                    <Icon aria-hidden="true" size={18} />
                    <span>{group.label}</span>
                    <ChevronDown aria-hidden="true" size={14} />
                  </button>
                ) : (
                  <NavLink className="opera-topnav-button" to={group.path}>
                    <Icon aria-hidden="true" size={18} />
                    <span>{group.label}</span>
                    <ChevronDown aria-hidden="true" size={14} />
                  </NavLink>
                )}
                {group.items.length ? (
                  <div className={`opera-topnav-menu ${openTopGroup === group.key ? "open" : ""}`}>
                    {group.items.map((item) => (
                      <NavLink
                        key={`${group.key}-${item.label}`}
                        to={item.path}
                        className={
                          childIsActive(item.path, item.label)
                            ? "opera-topnav-item active"
                            : "opera-topnav-item"
                        }
                        onClick={() => {
                          setMobileMenuOpen(false);
                          setOpenTopGroup(null);
                        }}
                      >
                        <span>{item.label}</span>
                        {item.comingSoon ? <small>Soon</small> : null}
                      </NavLink>
                    ))}
                  </div>
                ) : null}
              </div>
            );
          })}
        </nav>
      </div>

      <div className="pms-topbar-actions">
        <div className="business-date-topbar">
          <BusinessDateBar />
        </div>
        <div className="topbar-notification-wrap" ref={notificationRef}>
          <button
            type="button"
            className={`topbar-icon-button ${notificationsOpen ? "active" : ""}`}
            aria-label="Open active notifications"
            aria-expanded={notificationsOpen}
            title="Notifications"
            onClick={() => setNotificationsOpen((current) => !current)}
          >
            <Bell aria-hidden="true" size={19} />
            <span>3</span>
          </button>
          {notificationsOpen ? (
            <div className="topbar-notification-menu" role="menu" aria-label="Active notifications">
              <div>
                <strong>Active Notifications</strong>
                <span>3 open items</span>
              </div>
              <Link to="/frontdesk" onClick={() => setNotificationsOpen(false)}>
                <strong>Arrivals need review</strong>
                <span>Check room readiness and registration cards.</span>
              </Link>
              <Link to="/housekeeping" onClick={() => setNotificationsOpen(false)}>
                <strong>Housekeeping alerts</strong>
                <span>Dirty and inspected room status changed.</span>
              </Link>
              <Link to="/night-audit" onClick={() => setNotificationsOpen(false)}>
                <strong>Night Audit readiness</strong>
                <span>Review blockers before end of day.</span>
              </Link>
            </div>
          ) : null}
        </div>
        <Link className="topbar-ai-button" to="/booking-assistant">
          <Bot aria-hidden="true" size={18} />
          <span>AI Assistant</span>
        </Link>
        <div className="user-identity" title={`${userDisplayName} | ${getRoleLabel(session.role)}`}>
          <div className="user-avatar" aria-hidden="true">
            {!avatarFailed ? (
              <img src={avatarSrc} alt="" onError={() => setAvatarFailed(true)} />
            ) : (
              <span>{userInitials}</span>
            )}
          </div>
          <div className="user-meta">
            <strong>{userDisplayName}</strong>
            <span>{getRoleLabel(session.role)}</span>
          </div>
        </div>
      </div>
    </header>
  );
}

function getUserInitials(label: string) {
  const parts = label
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (!parts.length) return "GU";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}
