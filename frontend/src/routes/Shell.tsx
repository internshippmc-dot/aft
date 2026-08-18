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
import { PaymentsView } from "./PaymentsView";
import { ReturnsView } from "./ReturnsView";
import { TasksView } from "./TasksView";
import { ResourcesView } from "./ResourcesView";
import { MessagesView } from "./MessagesView";
import { WorkflowView } from "./WorkflowView";
import { ControlTowerView } from "./ControlTowerView";

type View = { type: "box"; aft: string } | { type: "order"; orderNumber: string } | null;
type Filter = "all" | "transit" | "queue";

type Section = "dashboard" | "batches" | "control" | "tasks" | "orders" | "messages" | "payments" | "returns" | "resources" | "settings";

const NAV: { label: string; groups: { label: string; section: Section; icon: string; badge?: string }[] }[] = [
  { label: "Home", groups: [{ label: "Dashboard", section: "dashboard", icon: "⌂" }] },
  {
    label: "Logistics",
    groups: [
      { label: "AFT Batches", section: "batches", icon: "▣" },
      { label: "China Control Tower", section: "control", icon: "⇄" },
      { label: "Tasks & Reminders", section: "tasks", icon: "◷" },
    ],
  },
  {
    label: "Orders",
    groups: [
      { label: "All Orders", section: "orders", icon: "☷" },
      { label: "Customer Messages", section: "messages", icon: "✉" },
    ],
  },
  {
    label: "Finance & After Sales",
    groups: [
      { label: "Payments", section: "payments", icon: "₹" },
      { label: "Returns & Exchanges", section: "returns", icon: "↩" },
    ],
  },
  {
    label: "System",
    groups: [
      { label: "Resources & SOPs", section: "resources", icon: "↗" },
      { label: "Workflow & SLA", section: "settings", icon: "⚙" },
    ],
  },
];

const COMING_SOON: Partial<Record<Section, { title: string; body: string }>> = {
  dashboard: { title: "Dashboard", body: "A rollup view is on the roadmap — for now, AFT Batches is the working view." },
  orders: { title: "All Orders", body: "A full order table is on the roadmap — use search above to jump to a specific order." },
};

export function Shell({ me }: { me: Me }) {
  const [section, setSection] = useState<Section>("batches");
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

  function pickBox(aft: string) {
    setSection("batches");
    setView({ type: "box", aft });
  }
  function pickOrder(orderNumber: string) {
    setSection("batches");
    setView({ type: "order", orderNumber });
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">AF</div>
          <div>
            <h1>Actually Fair</h1>
            <p>Ops Console</p>
          </div>
        </div>
        {NAV.map((group) => (
          <div className="navgroup" key={group.label}>
            <div className="navlabel">{group.label}</div>
            {group.groups.map((item) => (
              <button
                key={item.section}
                className={`navitem ${section === item.section ? "active" : ""}`}
                onClick={() => setSection(item.section)}
              >
                <span aria-hidden>{item.icon}</span> {item.label}
              </button>
            ))}
          </div>
        ))}
      </aside>

      <div className="main">
        <header>
          <SearchBar onPickOrder={pickOrder} onPickBox={pickBox} />
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
          {section === "batches" && (me.role === "owner" || me.role === "ops") && (
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

        <div className="content">
          {section === "batches" ? (
            <div className="split">
              <BoxListAside
                current={view?.type === "box" ? view.aft : null}
                onSelect={pickBox}
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
                  <BoxDetailView aft={view.aft} onBack={() => setView(null)} onSelectOrder={pickOrder} />
                )}
                {view?.type === "order" && (
                  <OrderDetailView orderNumber={view.orderNumber} onSelectBox={pickBox} me={me} />
                )}
              </section>
            </div>
          ) : section === "payments" ? (
            <section className="detail">
              <PaymentsView me={me} />
            </section>
          ) : section === "returns" ? (
            <section className="detail">
              <ReturnsView me={me} />
            </section>
          ) : section === "tasks" ? (
            <section className="detail">
              <TasksView me={me} />
            </section>
          ) : section === "resources" ? (
            <section className="detail">
              <ResourcesView me={me} />
            </section>
          ) : section === "messages" ? (
            <section className="detail">
              <MessagesView me={me} />
            </section>
          ) : section === "settings" ? (
            <section className="detail">
              <WorkflowView />
            </section>
          ) : section === "control" ? (
            <section className="detail">
              <ControlTowerView me={me} onOpenBox={pickBox} />
            </section>
          ) : (
            <section className="detail">
              <div className="empty">
                <h3>{COMING_SOON[section]!.title}</h3>
                <p>{COMING_SOON[section]!.body}</p>
              </div>
            </section>
          )}
        </div>
      </div>

      <NewBoxDrawer open={newBoxOpen} onClose={() => setNewBoxOpen(false)} onSaved={(box) => pickBox(box.aft_number)} />
    </div>
  );
}
