import { ReactNode } from "react";

export function Drawer({
  open,
  title,
  onClose,
  children,
  footer,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <>
      <div className={`scrim ${open ? "on" : ""}`} onClick={onClose} />
      <div className={`drawer ${open ? "on" : ""}`} role="dialog" aria-label={title}>
        <header>
          <strong>{title}</strong>
          <button className="btn ghost" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="body">{children}</div>
        <div className="foot">{footer}</div>
      </div>
    </>
  );
}
