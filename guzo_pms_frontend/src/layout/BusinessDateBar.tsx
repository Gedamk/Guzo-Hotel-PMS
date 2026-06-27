import { CalendarDays } from "lucide-react";
import { usePmsContext } from "../context/PmsContext";

export default function BusinessDateBar() {
  const { businessDate, setBusinessDate } = usePmsContext();

  return (
    <label className="shell-control" title="Business date">
      <CalendarDays aria-hidden="true" size={16} />
      <input
        type="date"
        value={businessDate}
        onChange={(event) => setBusinessDate(event.target.value)}
        aria-label="Business date"
      />
    </label>
  );
}
