import PmsSidebar from "./PmsSidebar";
import PmsStatusRibbon from "./PmsStatusRibbon";
import PmsTopbar from "./PmsTopbar";
import type { ReactNode } from "react";
import type { UserSession } from "../types/pms";

type PmsShellProps = {
  children: ReactNode;
  onLogout?: () => void;
  session: UserSession;
};

export default function PmsShell({ children, onLogout, session }: PmsShellProps) {
  return (
    <div className="app-shell" data-testid="pms-app-shell">
      <PmsSidebar onLogout={onLogout} session={session} />

      <div className="main-panel">
        <PmsTopbar session={session} />
        <div className="page-content">
          <PmsStatusRibbon />
          {children}
        </div>
      </div>
    </div>
  );
}
