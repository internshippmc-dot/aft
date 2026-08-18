import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Me, SyncState, SyncSummary } from "../lib/types";
import { api, ApiError } from "../lib/api";
import { useToast } from "../components/Toast";
import { SearchBar } from "../components/SearchBar";
import { ConsolidationStrip } from "../components/ConsolidationStrip";
import { BoxListAside } from "../components/BoxListAside";
import { NewBoxDrawer } from "../components/NewBoxDrawer";
import { BoxDetailView } from "./BoxDetailView";
import { OrderDetailView } from "./OrderDetailView";

type View = { type: "box"; aft: string } | { type: "order"; orderNumber: string } | null;
type Filter = "all" | "transit" | "queue";

export function Shell({ me }: { me: Me }) {
  const [view, setView] = useState<View>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [newBoxOpen, setNewBoxOpen] = useState(false);
  const queryClient = useQueryClient();
  const toast = useToast();

  const { data: syncStatus } = useQuery({
    queryKey: ["integrations", "status"],
    queryFn: () => api.get<Record<string, SyncState | null>>("/integrations/status"),
    enabled: me.role === "owner",
  });
  const syncShopify = useMutation({
    mutationFn: () => api.post<SyncSummary>("/integrations/shopify/sync"),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["integrations", "status"] });
      if (result.error) {
        toast(`Shopify sync failed: ${result.error}`);
      } else {
        queryClient.invalidateQueries({ queryKey: ["boxes"] });
        toast(`Shopify sync done — ${result.created} new, ${result.updated} updated.`);
      }
    },
    onError: (err) => toast(err instanceof ApiError ? err.message : "Could not run the Shopify sync."),
  });

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const typing = /input|textarea|select/i.test((document.activeElement?.tagName as string) || "");
      if (e.key === "n" && !typing) {
        e.preventDefault();
        setNewBoxOpen(true);
      }
      if (e.key === "Escape") {
        setNewBoxOpen(false);
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  async function logout() {
    await api.post("/auth/logout");
    queryClient.clear();
  }

  return (
    <div id="app">
      <header>
        <div className="wordmark">
          Actually Fair <span>/ Ops</span>
        </div>
        <SearchBar
          onPickOrder={(no) => setView({ type: "order", orderNumber: no })}
          onPickBox={(aft) => setView({ type: "box", aft })}
        />
        <div className="spacer" />
        {me.role === "owner" && (
          <button
            className="btn ghost"
            disabled={syncShopify.isPending}
            title={syncStatus?.shopify?.last_success_at ? `Last synced ${new Date(syncStatus.shopify.last_success_at).toLocaleString()}` : "Never synced"}
            onClick={() => syncShopify.mutate()}
          >
            {syncShopify.isPending ? "Syncing…" : "Sync Shopify"}
          </button>
        )}
        {(me.role === "owner" || me.role === "ops") && (
          <button className="btn ghost" onClick={() => setNewBoxOpen(true)}>
            New box <span className="mono faint">n</span>
          </button>
        )}
        <div className="who">
          <span className="avatar">{me.full_name.slice(0, 1).toUpperCase()}</span>
          <span className="dim">{me.full_name}</span>
          <button className="btn ghost" onClick={logout} style={{ padding: "4px 8px" }}>
            Sign out
          </button>
        </div>
      </header>

      <ConsolidationStrip />

      <main>
        <BoxListAside
          current={view?.type === "box" ? view.aft : null}
          onSelect={(aft) => setView({ type: "box", aft })}
          filter={filter}
          onFilterChange={setFilter}
        />
        <section className="detail">
          {view === null && (
            <div className="empty">
              <h3>Pick a box to get started</h3>
              <p>Select a box from the list, or search for an order, customer, phone number, AWB, or AFT number above.</p>
            </div>
          )}
          {view?.type === "box" && (
            <BoxDetailView
              aft={view.aft}
              onBack={() => setView(null)}
              onSelectOrder={(no) => setView({ type: "order", orderNumber: no })}
            />
          )}
          {view?.type === "order" && (
            <OrderDetailView orderNumber={view.orderNumber} onSelectBox={(aft) => setView({ type: "box", aft })} me={me} />
          )}
        </section>
      </main>

      <NewBoxDrawer
        open={newBoxOpen}
        onClose={() => setNewBoxOpen(false)}
        onSaved={(box) => setView({ type: "box", aft: box.aft_number })}
      />
    </div>
  );
}
