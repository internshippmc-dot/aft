import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "./lib/api";
import { Me } from "./lib/types";
import { Login } from "./routes/Login";
import { Shell } from "./routes/Shell";

export default function App() {
  const queryClient = useQueryClient();
  const meQuery = useQuery<Me, ApiError>({
    queryKey: ["me"],
    queryFn: () => api.get<Me>("/auth/me"),
    retry: false,
  });

  // Any 401 outside the auth endpoints means the session expired — drop back
  // to the login screen immediately rather than on the next full reload.
  useEffect(() => {
    const onUnauthorized = () => queryClient.setQueryData(["me"], null);
    window.addEventListener("aft:unauthorized", onUnauthorized);
    return () => window.removeEventListener("aft:unauthorized", onUnauthorized);
  }, [queryClient]);

  if (meQuery.isLoading) {
    return <div style={{ padding: 24 }} className="dim">Loading…</div>;
  }

  if (!meQuery.data) {
    return <Login onSignedIn={(me) => queryClient.setQueryData(["me"], me)} />;
  }

  return <Shell me={meQuery.data} />;
}
