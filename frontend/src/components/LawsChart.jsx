import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const COLORS = ['#1e3a5f', '#2d5494', '#c9a84c', '#e8c96d', '#4a7fc1'];

export default function LawsChart({ data }) {
  if (!data?.length) return (
    <div className="flex items-center justify-center h-32 text-gray-400 text-sm">
      No citation data yet
    </div>
  );

  const chartData = data.slice(0, 10).map(d => ({
    name: d.display_label?.slice(0, 25) || d.citation?.slice(0, 25),
    count: d.count,
    act: d.act,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 60 }}>
        <XAxis
          dataKey="name"
          tick={{ fontSize: 10 }}
          angle={-35}
          textAnchor="end"
          interval={0}
        />
        <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
        <Tooltip
          contentStyle={{ fontSize: 12, borderRadius: 8 }}
          formatter={(val) => [val, 'Citations']}
        />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {chartData.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}