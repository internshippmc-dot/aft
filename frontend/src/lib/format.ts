export function fmtDate(d: string | null | undefined): string {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

export function inr(n: string | number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  const num = typeof n === "string" ? parseFloat(n) : n;
  return "₹" + num.toLocaleString("en-IN");
}

export function daysBetween(a: string, b: string | Date): number {
  return Math.round((new Date(b).getTime() - new Date(a).getTime()) / 864e5);
}

export function dateRange(a: string, b: string): string {
  const A = fmtDate(a);
  const B = fmtDate(b);
  return A.slice(3) === B.slice(3) ? A.slice(0, 2) + "–" + B : A + " – " + B;
}
