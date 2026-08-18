import { Eta, Legs } from "./types";
import { daysBetween, fmtDate } from "./format";

export function etaNote(legs: Legs, eta: Eta | null, slaRisk: boolean): string {
  if (legs.DELHI_WAREHOUSE) {
    const t = legs.MFG_DISPATCH ? daysBetween(legs.MFG_DISPATCH, legs.DELHI_WAREHOUSE) : null;
    return `Landed in Delhi on ${fmtDate(legs.DELHI_WAREHOUSE)}${t !== null ? `, ${t} days from manufacturer dispatch` : ""}. Every order in this box moved to the Delhi warehouse stage.`;
  }
  if (!eta) return "No dispatch date yet, so there is nothing to estimate from.";
  const base = `Delhi arrival estimated ${fmtDate(eta.p50_date)} to ${fmtDate(eta.p80_date)}, from ${eta.sample_n} recent shipment${eta.sample_n === 1 ? "" : "s"}${eta.confidence === "low" ? " (low confidence — not enough history yet)" : ""}.`;
  const tail = slaRisk
    ? " The late end of that range puts the oldest order in this box past the 14 day promise. Worth a heads-up message before the customer asks."
    : " Inside the 14 day promise for every order in this box.";
  return base + tail;
}
