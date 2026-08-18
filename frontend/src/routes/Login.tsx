import { FormEvent, useState } from "react";
import { api, ApiError } from "../lib/api";
import { Me } from "../lib/types";

export function Login({ onSignedIn }: { onSignedIn: (me: Me) => void }) {
  const [email, setEmail] = useState("siddharth@actuallyfair.in");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = await api.post<Me>("/auth/login", { email, password });
      onSignedIn(me);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign in failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div id="login">
      <div className="login-form">
        <div className="wordmark">
          Actually Fair <span>/ Operations</span>
        </div>

        <form className="login-body" onSubmit={submit}>
          <h1>Sign in</h1>
          <p className="lede">Internal console. Access is logged.</p>

          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="pw">Password</label>
            <input
              id="pw"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button className="btn block" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <p className={`err ${error ? "on" : ""}`}>{error}</p>

          <p className="login-note">
            Sessions end after 60 minutes idle or 12 hours total. Two-factor enrolment is not yet enforced on this
            instance — see SECURITY.md.
          </p>
        </form>

        <div className="faint" style={{ fontSize: 11 }}>
          Actually Fair Technologies Pvt Ltd · Mulund, Mumbai
        </div>
      </div>

      <div className="login-art">
        <div className="eyebrow">Factory to Delhi</div>
        <div className="art-legs">
          <div className="legbar lg">
            <div className="leg done">
              <div className="bar" />
              <div className="lbl">Dispatch</div>
              <div className="dt">04 Aug</div>
            </div>
            <div className="leg done">
              <div className="bar" />
              <div className="lbl">CN warehouse</div>
              <div className="dt">06 Aug</div>
            </div>
            <div className="leg done">
              <div className="bar" />
              <div className="lbl">Flight</div>
              <div className="dt">09 Aug</div>
            </div>
            <div className="leg pred">
              <div className="bar" />
              <div className="lbl">Delhi</div>
              <div className="dt">13–15 Aug</div>
            </div>
          </div>
        </div>
        <p className="art-cap">
          Four legs, one box, and every order inside it. Solid means it happened. Hatched means the console is
          estimating from the last twenty shipments.
        </p>
      </div>
    </div>
  );
}
