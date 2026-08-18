import { Eta, Legs } from "../lib/types";
import { dateRange, fmtDate } from "../lib/format";

const LEG_KEYS: (keyof Legs)[] = ["MFG_DISPATCH", "CN_WAREHOUSE", "FLIGHT", "DELHI_WAREHOUSE"];
const LEG_LABELS: Record<keyof Legs, string> = {
  MFG_DISPATCH: "Dispatch",
  CN_WAREHOUSE: "CN warehouse",
  FLIGHT: "Flight",
  DELHI_WAREHOUSE: "Delhi",
};

export function LegBar({ legs, eta, size = "" }: { legs: Legs; eta: Eta | null; size?: "mini" | "lg" | "" }) {
  const doneCount = LEG_KEYS.filter((k) => legs[k]).length;
  // Compare ISO dates as strings — new Date("2026-08-14") parses as UTC
  // midnight, which is "before now" on the same day and would wrongly mark
  // a box late while today is still inside its promised range.
  const todayStr = new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD, local
  const isLate = eta ? eta.p80_date < todayStr : false;

  return (
    <div className={`legbar ${size}`.trim()}>
      {LEG_KEYS.map((key, i) => {
        let state = "";
        let date = "—";
        if (legs[key]) {
          state = "done";
          date = fmtDate(legs[key]);
        } else if (i === doneCount && eta) {
          state = "pred";
          date = dateRange(eta.p50_date, eta.p80_date);
        } else if (eta) {
          state = "pred";
          date = "";
        }
        if (state === "pred" && isLate && i === LEG_KEYS.length - 1) state = "late";
        return (
          <div key={key} className={`leg ${state}`.trim()}>
            <div className="bar" />
            <div className="lbl">{LEG_LABELS[key]}</div>
            <div className="dt">{date}</div>
          </div>
        );
      })}
    </div>
  );
}
