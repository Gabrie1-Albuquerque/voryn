import type { ReactNode } from "react";

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="card"
        style={{ width: 380, maxHeight: "85vh", overflow: "auto", background: "var(--bg)" }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>{title}</h2>
          <button onClick={onClose} style={{ border: "none", background: "none", fontSize: 18, padding: 4 }}>
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
