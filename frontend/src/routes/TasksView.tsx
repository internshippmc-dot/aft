import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { Me, Task } from "../lib/types";
import { fmtDate } from "../lib/format";
import { NewTaskDrawer } from "../components/NewTaskDrawer";
import { useToast } from "../components/Toast";

type Filter = "open" | "done";

function priorityPill(p: string): string {
  if (p === "High") return "red";
  if (p === "Low") return "grey";
  return "amber";
}

export function TasksView({ me }: { me: Me }) {
  const [filter, setFilter] = useState<Filter>("open");
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const toast = useToast();
  const canWrite = me.role === "owner" || me.role === "ops";

  const { data, isLoading } = useQuery({
    queryKey: ["tasks", filter],
    queryFn: () => api.get<Task[]>(`/tasks?status_filter=${filter === "open" ? "Open" : "Done"}`),
  });

  const complete = useMutation({
    mutationFn: (id: number) => api.patch<Task>(`/tasks/${id}/complete`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      toast("Task completed.");
    },
    onError: (err) => toast(err instanceof ApiError ? err.message : "Could not complete the task."),
  });

  const tasks = data || [];
  const today = new Date().toLocaleDateString("en-CA");

  return (
    <>
      <div className="h-row">
        <div>
          <h2 className="title">Tasks & Reminders</h2>
          <div className="sub">
            <div className="tabs" style={{ display: "inline-flex", marginTop: 6 }}>
              {(["open", "done"] as Filter[]).map((f) => (
                <button key={f} className={`tab ${filter === f ? "on" : ""}`} onClick={() => setFilter(f)}>
                  {f === "open" ? "Open" : "Done"}
                </button>
              ))}
            </div>
          </div>
        </div>
        {canWrite && (
          <button className="btn primary" onClick={() => setOpen(true)}>
            + New task
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="dim" style={{ padding: 24 }}>
          Loading…
        </div>
      ) : tasks.length === 0 ? (
        <div className="empty">
          <h3>{filter === "open" ? "No open tasks" : "Nothing completed yet"}</h3>
          <p>{filter === "open" ? "Reminders and follow-ups will show up here." : "Completed tasks show up here."}</p>
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th style={{ width: 80 }}>Priority</th>
              <th>Title</th>
              <th style={{ width: 110 }}>Related to</th>
              <th style={{ width: 96 }}>Due</th>
              {filter === "open" && canWrite && <th style={{ width: 90 }}></th>}
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.id}>
                <td>
                  <span className={`pill ${priorityPill(t.priority)}`}>{t.priority}</span>
                </td>
                <td>
                  {t.title}
                  {t.notes && (
                    <div className="faint" style={{ fontSize: 11 }}>
                      {t.notes}
                    </div>
                  )}
                </td>
                <td className="mono dim">{t.entity_id || "—"}</td>
                <td className={`mono ${t.due_on && t.due_on < today && filter === "open" ? "warn" : "dim"}`}>
                  {t.due_on ? fmtDate(t.due_on) : "—"}
                </td>
                {filter === "open" && canWrite && (
                  <td>
                    <button className="btn small ghost" disabled={complete.isPending} onClick={() => complete.mutate(t.id)}>
                      Complete
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <NewTaskDrawer open={open} onClose={() => setOpen(false)} />
    </>
  );
}
