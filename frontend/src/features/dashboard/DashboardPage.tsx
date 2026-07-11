import { useQuery } from "@tanstack/react-query";
import { Gauge, TrendingUp, UserX, Wallet, type LucideIcon } from "lucide-react";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getDashboardSummary } from "../../api/dashboard";

function toDateInputValue(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function defaultRange(): { start: string; end: string } {
  const end = new Date();
  end.setDate(end.getDate() + 1);
  const start = new Date();
  start.setDate(start.getDate() - 30);
  return { start: toDateInputValue(start), end: toDateInputValue(end) };
}

function formatPercent(value: number | null): string {
  if (value === null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function StatCard({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  tone: "accent" | "success" | "danger" | "warning";
}) {
  const tones = {
    accent: { background: "var(--accent-bg)", color: "var(--accent-strong)" },
    success: { background: "var(--success-bg)", color: "var(--success)" },
    danger: { background: "var(--danger-bg)", color: "var(--danger)" },
    warning: { background: "var(--warning-bg)", color: "var(--warning)" },
  } as const;

  return (
    <div className="card stat-card">
      <span className="stat-card-icon" style={tones[tone]}>
        <Icon size={20} />
      </span>
      <span>
        <p className="stat-card-label">{label}</p>
        <p className="stat-card-value">{value}</p>
      </span>
    </div>
  );
}

export function DashboardPage() {
  const [range, setRange] = useState(defaultRange);
  const summaryQuery = useQuery({
    queryKey: ["dashboard-summary", range.start, range.end],
    queryFn: () => getDashboardSummary(range.start, range.end),
  });

  const summary = summaryQuery.data;

  return (
    <div>
      <h1>Dashboard</h1>
      <div className="card" style={{ display: "flex", gap: 12, marginBottom: 16, alignItems: "flex-end", maxWidth: 400 }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          De
          <input
            type="date"
            value={range.start}
            onChange={(e) => setRange((r) => ({ ...r, start: e.target.value }))}
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Até
          <input type="date" value={range.end} onChange={(e) => setRange((r) => ({ ...r, end: e.target.value }))} />
        </label>
      </div>

      {summaryQuery.isLoading && <p>Carregando...</p>}
      {summaryQuery.isError && <p className="error-text">Não foi possível carregar o dashboard.</p>}

      {summary && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 12,
              marginBottom: 20,
            }}
          >
            <StatCard label="Receita prevista" value={`R$ ${summary.projected_revenue}`} icon={TrendingUp} tone="accent" />
            <StatCard label="Receita realizada" value={`R$ ${summary.realized_revenue}`} icon={Wallet} tone="success" />
            <StatCard label="Taxa de faltas" value={formatPercent(summary.no_show_rate)} icon={UserX} tone="danger" />
            <StatCard label="Ocupação" value={formatPercent(summary.occupancy_rate)} icon={Gauge} tone="warning" />
          </div>

          <div className="card">
            <h2>Serviços mais vendidos</h2>
            {summary.top_services.length === 0 ? (
              <p>Nenhum serviço concluído no período.</p>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={summary.top_services}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="completed_count" name="Atendimentos" fill="#7c3aed" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </>
      )}
    </div>
  );
}
