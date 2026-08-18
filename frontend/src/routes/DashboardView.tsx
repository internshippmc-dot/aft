import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { ControlTowerCard, CustomerMessage, Me, OrderListItem, Task } from "../lib/types";
import { fmtDate, inr } from "../lib/format";
import { AddPaymentDrawer } from "../components/AddPaymentDrawer";
import { NewBoxDrawer } from "../components/NewBoxDrawer";
import { useToast } from "../components/Toast";

const FLOW_STAGES = ["Manufacturer → Hexalog", "Sitting in Hexalog", "On Flight", "Delhi Warehouse", "In Transit"];
const PAGE_SIZE = 8;

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function dueBadge(dueOn: string | null): { label: string; cls: string } {
  if (!dueOn) return { label: "—", cls: "grey" };
  const today = new Date().toLocaleDateString("en-CA");
  const tomorrow = new Date(Date.now() + 86400000).toLocaleDateString("en-CA");
  if (dueOn < today) return { label: "Overdue", cls: "red" };
  if (dueOn === today) return { label: "Today", cls: "amber" };
  if (dueOn === tomorrow) return { label: "Tomorrow", cls: "blue" };
  return { label: fmtDate(dueOn), cls: "grey" };
}

export function DashboardView({
  me,
  onNavigate,
  onOpenBox,
}: {
  me: Me;
  onNavigate: (section: "control" | "messages" | "tasks") => void;
  onOpenBox: (aft: string) => void;
}) {
  const [page, setPage] = useState(0);
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [batchOpen, setBatchOpen] = useState(false);
  const queryClient = useQueryClient();
  const toast = useToast();
  const canWrite = me.role === "owner" || me.role === "ops";

  const { data: orders } = useQuery({ queryKey: ["orders", ""], queryFn: () => api.get<OrderListItem[]>("/orders") });
  const { data: cards } = useQuery({ queryKey: ["control-tower"], queryFn: () => api.get<ControlTowerCard[]>("/control-tower") });
  const { data: tasks } = useQuery({ queryKey: ["tasks", "Open"], queryFn: () => api.get<Task[]>("/tasks?status_filter=Open") });
  const { data: messages } = useQuery({ queryKey: ["messages"], queryFn: () => api.get<CustomerMessage[]>("/messages") });

  const complete = useMutation({
    mutationFn: (id: number) => api.patch<Task>(`/tasks/${id}/complete`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      toast("Task completed.");
    },
    onError: (err) => toast(err instanceof ApiError ? err.message : "Could not complete the task."),
  });

  const unbatched = (orders || []).filter((o) => !o.box_aft_number).length;
  const activeBatches = (cards || []).filter((c) => c.pipeline_stage !== "Closed");
  const pendingMessages = (messages || []).filter((m) => m.status === "Pending");

  const kpis = [
    { label: "Confirmed / Unbatched", value: unbatched, sub: "Ready for next manufacturer batch" },
    { label: "Active AFT Batches", value: activeBatches.length, sub: "China → India pipeline" },
    { label: "At Hexalog", value: (cards || []).filter((c) => c.pipeline_stage === "Sitting in Hexalog").length, sub: "Packing list / flight planning" },
    { label: "China → India", value: (cards || []).filter((c) => c.pipeline_stage === "On Flight").length, sub: "Cross-border" },
    { label: "Last Mile", value: (cards || []).filter((c) => c.pipeline_stage === "In Transit").length, sub: "India fulfillment" },
    { label: "Messages Due", value: pendingMessages.length, sub: "Customer updates pending" },
  ];

  const openTasks = tasks || [];
  const pageCount = Math.max(1, Math.ceil(openTasks.length / PAGE_SIZE));
  const pageTasks = openTasks.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

  const messagesByType = useMemo(() => {
    const counts = new Map<string, number>();
    for (const m of pendingMessages) counts.set(m.type, (counts.get(m.type) || 0) + 1);
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [pendingMessages]);

  const flowCounts = FLOW_STAGES.map((stage) => ({
    stage,
    count: (cards || []).filter((c) => c.pipeline_stage === stage).length,
  }));

  return (
    <>
      <div className="h-row">
        <div>
          <h2 className="title">
            {greeting()} 👋
          </h2>
          <div className="sub">
            {new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" })} · Here's what needs attention
            today.
          </div>
        </div>
        {canWrite && (
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn ghost" onClick={() => setPaymentOpen(true)}>
              + Payment
            </button>
            <button className="btn primary" onClick={() => setBatchOpen(true)}>
              + Create AFT Batch
            </button>
          </div>
        )}
      </div>

      <div className="facts" style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)" }}>
        {kpis.map((k) => (
          <div className="fact" key={k.label}>
            <div className="k">{k.label}</div>
            <div className="v" style={{ fontSize: 22 }}>
              {k.value}
            </div>
            <div className="faint" style={{ fontSize: 10, marginTop: 3 }}>
              {k.sub}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 16, margin: "20px 0" }}>
        <div className="panel-legs">
          <div className="h-row" style={{ marginBottom: 8 }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: 13 }}>Action required</div>
              <div className="dim" style={{ fontSize: 11 }}>
                Overdue and due-today operational tasks
              </div>
            </div>
            <span className="pill red">{openTasks.length} open</span>
          </div>
          {pageTasks.length === 0 ? (
            <div className="dim" style={{ padding: "16px 0", fontSize: 12 }}>
              Nothing open.
            </div>
          ) : (
            pageTasks.map((t) => {
              const due = dueBadge(t.due_on);
              return (
                <div key={t.id} style={{ display: "flex", gap: 10, alignItems: "center", padding: "9px 0", borderBottom: "1px solid var(--rule-soft)" }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, fontSize: 12 }}>{t.title}</div>
                    <div className="faint" style={{ fontSize: 10 }}>
                      {t.entity_id ? `${t.entity_id} · ` : ""}
                      {t.priority}
                    </div>
                  </div>
                  <span className={`pill ${due.cls}`}>{due.label}</span>
                  {canWrite && (
                    <button className="btn small ghost" disabled={complete.isPending} onClick={() => complete.mutate(t.id)}>
                      ✓ Done
                    </button>
                  )}
                </div>
              );
            })
          )}
          {pageCount > 1 && (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10 }}>
              <span className="faint" style={{ fontSize: 11 }}>
                {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, openTasks.length)} of {openTasks.length}
              </span>
              <div style={{ display: "flex", gap: 6 }}>
                <button className="btn small ghost" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                  ←
                </button>
                <button className="btn small ghost" disabled={page >= pageCount - 1} onClick={() => setPage((p) => p + 1)}>
                  →
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="panel-legs">
          <div className="h-row" style={{ marginBottom: 8 }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: 13 }}>Customer messages due</div>
              <div className="dim" style={{ fontSize: 11 }}>
                Queued from Order Detail, grouped by template
              </div>
            </div>
            <button className="btn small ghost" onClick={() => onNavigate("messages")}>
              Open inbox
            </button>
          </div>
          {messagesByType.length === 0 ? (
            <div className="dim" style={{ padding: "16px 0", fontSize: 12 }}>
              Nothing pending.
            </div>
          ) : (
            messagesByType.map(([type, count]) => (
              <div key={type} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--rule-soft)" }}>
                <span style={{ fontSize: 12 }}>{type}</span>
                <span className="pill purple">{count} waiting</span>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="panel-legs">
        <div className="h-row" style={{ marginBottom: 8 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 13 }}>Active package flow</div>
            <div className="dim" style={{ fontSize: 11 }}>
              Where your AFT batches are right now
            </div>
          </div>
          <button className="btn small ghost" onClick={() => onNavigate("control")}>
            Open control tower
          </button>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: `repeat(${FLOW_STAGES.length}, 1fr)`, gap: 10 }}>
          {flowCounts.map((f) => (
            <div key={f.stage} className="fact" style={{ border: "1px solid var(--rule)", borderRadius: 10, padding: "10px 12px" }}>
              <div className="v" style={{ fontSize: 20 }}>
                {f.count}
              </div>
              <div className="faint" style={{ fontSize: 10, marginTop: 2 }}>
                {f.stage}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ margin: "20px 0 40px" }}>
        <div className="h-row" style={{ marginBottom: 10 }}>
          <div>
            <h2 className="title" style={{ fontSize: 16 }}>
              Active AFT batches
            </h2>
            <div className="sub">Recent China → India packages</div>
          </div>
          <button className="btn small ghost" onClick={() => onNavigate("control")}>
            View all
          </button>
        </div>
        {activeBatches.length === 0 ? (
          <div className="empty">
            <h3>No active batches</h3>
            <p>Batches will show up here once created.</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th style={{ width: 80 }}>AFT</th>
                <th>MF / Orders</th>
                <th>Manufacturer</th>
                <th className="num" style={{ width: 100 }}>Amount</th>
                <th style={{ width: 150 }}>Stage</th>
                <th style={{ width: 120 }}>CN Tracking</th>
                <th style={{ width: 70 }}>PL</th>
                <th>Next Action</th>
              </tr>
            </thead>
            <tbody>
              {activeBatches.slice(0, 10).map((c) => (
                <tr key={c.aft_number} className="clickable" onClick={() => onOpenBox(c.aft_number)}>
                  <td className="mono strong">
                    {c.flagged && <span style={{ color: "var(--red)", marginRight: 4 }}>⚑</span>}
                    {c.aft_number}
                  </td>
                  <td className="mono dim">
                    {c.mf_number || "—"} · {c.order_count} orders
                  </td>
                  <td className="dim">{c.manufacturer || "—"}</td>
                  <td className="num">{inr(c.amount_paid_inr)}</td>
                  <td>
                    <span className="pill blue">{c.pipeline_stage}</span>
                  </td>
                  <td className="mono dim">{c.cn_tracking || "—"}</td>
                  <td>
                    <span className={`pill ${c.pl_status === "Sent" ? "green" : "amber"}`}>{c.pl_status || "—"}</span>
                  </td>
                  <td className="dim">{c.next_action || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <AddPaymentDrawer open={paymentOpen} onClose={() => setPaymentOpen(false)} />
      <NewBoxDrawer open={batchOpen} onClose={() => setBatchOpen(false)} onSaved={(box) => onOpenBox(box.aft_number)} />
    </>
  );
}
