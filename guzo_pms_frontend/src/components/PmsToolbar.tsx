import { PROPERTY_OPTIONS } from "../config/pms";
import { usePmsContext } from "../context/PmsContext";

export default function PmsToolbar() {
  const {
    propertyCode,
    businessDate,
    setPropertyCode,
    setBusinessDate,
    refreshData,
  } = usePmsContext();

  return (
    <div className="card" style={{ marginBottom: "18px" }}>
      <div
        style={{
          display: "grid",
          gap: "14px",
          gridTemplateColumns: "1fr 1fr auto",
          alignItems: "end",
        }}
      >
        <div className="field">
          <label>Property</label>
          <select
            value={propertyCode}
            onChange={(e) => setPropertyCode(e.target.value)}
          >
            {PROPERTY_OPTIONS.map((item) => (
              <option key={item.code} value={item.code}>
                {item.code} - {item.name}
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
          style={{ minWidth: "140px" }}
        >
          Refresh
        </button>
      </div>
    </div>
  );
}
