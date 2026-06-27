import { Building2 } from "lucide-react";
import { usePmsContext } from "../context/PmsContext";

export default function PropertySwitcher() {
  const { propertyCode, propertyOptions, setPropertyCode } = usePmsContext();

  return (
    <label className="shell-control" title="Active property">
      <Building2 aria-hidden="true" size={16} />
      <select
        value={propertyCode}
        onChange={(event) => setPropertyCode(event.target.value)}
        aria-label="Active property"
      >
        {propertyOptions.map((item) => (
          <option key={item.code} value={item.code}>
            {item.code} - {item.name}{item.isActive ? "" : " (inactive)"}
          </option>
        ))}
      </select>
    </label>
  );
}
