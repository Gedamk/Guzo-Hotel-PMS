import { RefreshCw } from "lucide-react";
import { usePmsContext } from "../context/PmsContext";

export default function PmsToolbar() {
  const {
    propertyCode,
    propertyOptions,
    businessDate,
    setPropertyCode,
    setBusinessDate,
    refreshData,
  } = usePmsContext();

  return (
    <div className="card pms-toolbar">
      <div className="toolbar-grid">
        <div className="field">
          <label>Property</label>
          <select
            value={propertyCode}
            onChange={(e) => setPropertyCode(e.target.value)}
          >
            {propertyOptions.map((item) => (
              <option key={item.code} value={item.code}>
                {item.code} - {item.name}{item.isActive ? "" : " (inactive)"}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>Business Date</label>
          <input
            type="date"
            value={businessDate}
            onChange={(e) => setBusinessDate(e.target.value)}
          />
        </div>

        <button
          type="button"
          className="primary-btn"
          onClick={refreshData}
          aria-label="Refresh PMS data"
        >
          <RefreshCw aria-hidden="true" size={17} />
          <span>Refresh</span>
        </button>
      </div>
    </div>
  );
}
