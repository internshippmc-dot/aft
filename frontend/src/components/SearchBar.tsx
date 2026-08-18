import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { SearchResults } from "../lib/types";

export function SearchBar({ onPickOrder, onPickBox }: { onPickOrder: (orderNumber: string) => void; onPickBox: (aft: string) => void }) {
  const [raw, setRaw] = useState("");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const t = window.setTimeout(() => setQ(raw.trim()), 180);
    return () => window.clearTimeout(t);
  }, [raw]);

  const { data } = useQuery({
    queryKey: ["search", q],
    queryFn: () => api.get<SearchResults>(`/search?q=${encodeURIComponent(q)}`),
    enabled: q.length > 0,
  });

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("click", onDocClick);
    return () => document.removeEventListener("click", onDocClick);
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const typing = /input|textarea/i.test((document.activeElement?.tagName as string) || "");
      if (e.key === "/" && !typing) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const hasResults = data && (data.orders.length > 0 || data.boxes.length > 0);

  function pickOrder(no: string) {
    setOpen(false);
    setRaw("");
    onPickOrder(no);
  }
  function pickBox(aft: string) {
    setOpen(false);
    setRaw("");
    onPickBox(aft);
  }

  return (
    <div className="search-wrap" ref={wrapRef}>
      <span className="mag">⌕</span>
      <input
        ref={inputRef}
        placeholder="Order no, customer, phone, AWB, or AFT box"
        autoComplete="off"
        value={raw}
        onChange={(e) => {
          setRaw(e.target.value);
          setOpen(true);
        }}
        onFocus={() => raw && setOpen(true)}
      />
      <span className="slash">/</span>
      <div className={`results ${open && q ? "on" : ""}`}>
        {q && data && !hasResults && (
          <>
            <div className="grp">
              <div className="eyebrow">No match</div>
            </div>
            <div style={{ padding: "6px 10px 12px" }} className="dim">
              Nothing matches that. Search by order number, customer name, phone, AWB, or AFT number.
            </div>
          </>
        )}
        {data && data.orders.length > 0 && (
          <>
            <div className="grp">
              <span className="eyebrow">Orders</span>
            </div>
            {data.orders.map((o) => (
              <button className="res" key={o.order_number} onClick={() => pickOrder(o.order_number)}>
                <span>
                  <span className="mono">{o.order_number}</span> · {o.customer_name || "—"}
                </span>
                <span className="dim mono">{o.aft_number || "unboxed"}</span>
              </button>
            ))}
          </>
        )}
        {data && data.boxes.length > 0 && (
          <>
            <div className="grp">
              <span className="eyebrow">Boxes and consignments</span>
            </div>
            {data.boxes.map((b) => (
              <button className="res" key={b.aft_number} onClick={() => pickBox(b.aft_number)}>
                <span className="mono">{b.aft_number}</span>
                <span className="dim">
                  {b.order_count} orders · {b.stage}
                </span>
              </button>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
