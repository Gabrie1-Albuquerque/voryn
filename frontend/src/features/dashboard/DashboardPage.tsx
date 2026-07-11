import { useQuery } from "@tanstack/react-query";
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

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="card">
      <p style={{ fontSize: 13, opacity: 0.7, marginBottom: 4 }}>{label}</p>
      <p style={{ fontSize: 22, fontWeight: 600 }}>{value}</p>
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
            <StatCard label="Receita prevista" value={`R$ ${summary.projected_revenue}`} />
            <StatCard label="Receita realizada" value={`R$ ${summary.realized_revenue}`} />
            <StatCard label="Taxa de faltas" value={formatPercent(summary.no_show_rate)} />
            <StatCard label="Ocupação" value={formatPercent(summary.occupancy_rate)} />
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
