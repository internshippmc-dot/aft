import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { Me, Resource } from "../lib/types";
import { ResourceDrawer } from "../components/ResourceDrawer";
import { useToast } from "../components/Toast";

export function ResourcesView({ me }: { me: Me }) {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Resource | null>(null);
  const queryClient = useQueryClient();
  const toast = useToast();
  const canWrite = me.role === "owner" || me.role === "ops";

  const { data, isLoading } = useQuery({
    queryKey: ["resources"],
    queryFn: () => api.get<Resource[]>("/resources"),
  });

  const del = useMutation({
    mutationFn: (id: number) => api.del(`/resources/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resources"] });
      toast("Resource removed.");
    },
    onError: (err) => toast(err instanceof ApiError ? err.message : "Could not remove the resource."),
  });

  const resources = data || [];

  function edit(r: Resource) {
    setEditing(r);
    setOpen(true);
  }
  function addNew() {
    setEditing(null);
    setOpen(true);
  }

  return (
    <>
      <div className="h-row">
        <div>
          <h2 className="title">Resources & SOPs</h2>
          <div className="sub">Shared quick links, internal references, and standard operating processes.</div>
        </div>
        {canWrite && (
          <button className="btn primary" onClick={addNew}>
            + Add resource
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="dim" style={{ padding: 24 }}>
          Loading…
        </div>
      ) : resources.length === 0 ? (
        <div className="empty">
          <h3>No resources yet</h3>
          <p>Shared links and SOPs will show up here.</p>
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th style={{ width: 70 }}>Type</th>
              <th>Title</th>
              <th style={{ width: 120 }}>Category</th>
              <th>Description</th>
              {canWrite && <th style={{ width: 130 }}></th>}
            </tr>
          </thead>
          <tbody>
            {resources.map((r) => (
              <tr key={r.id}>
                <td>
                  <span className="pill grey">{r.type}</span>
                </td>
                <td>
                  {r.url ? (
                    <a href={r.url} target="_blank" rel="noreferrer">
                      {r.title}
                    </a>
                  ) : (
                    r.title
                  )}
                </td>
                <td className="dim">{r.category || "—"}</td>
                <td className="dim">{r.description || "—"}</td>
                {canWrite && (
                  <td>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button className="btn small ghost" onClick={() => edit(r)}>
                        Edit
                      </button>
                      <button className="btn small ghost" onClick={() => del.mutate(r.id)}>
                        Delete
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <ResourceDrawer open={open} editing={editing} onClose={() => setOpen(false)} />
    </>
  );
}
