'use client';

import { useMemo, useState } from 'react';
import {
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  CartesianGrid,
  Line,
  ComposedChart,
} from 'recharts';

interface OpinionTrajectoryChartProps {
  trajectoryData: Record<string, Array<{ day: number; opinion: string }>>;
}

type OpinionKey = 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE';
type ViewMode = 'share' | 'count';

interface DayCounts {
  day: number;
  POSITIVE: number;
  NEUTRAL: number;
  NEGATIVE: number;
  total: number;
}

interface ChartPoint extends DayCounts {
  positiveShare: number;
  neutralShare: number;
  negativeShare: number;
  netSentiment: number;
}

const OPINION_META: Record<
  OpinionKey,
  { label: string; color: string; short: string }
> = {
  POSITIVE: { label: 'Positive', color: '#16a34a', short: '+' },
  NEUTRAL: { label: 'Neutral', color: '#64748b', short: '○' },
  NEGATIVE: { label: 'Negative', color: '#dc2626', short: '−' },
};

const OPINION_ORDER: OpinionKey[] = ['POSITIVE', 'NEUTRAL', 'NEGATIVE'];

function pct(part: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((part / total) * 1000) / 10;
}

function formatDayLabel(day: number): string {
  return `Day ${day}`;
}

function shareFor(point: ChartPoint, key: OpinionKey): number {
  if (key === 'POSITIVE') return point.positiveShare;
  if (key === 'NEUTRAL') return point.neutralShare;
  return point.negativeShare;
}

function OpinionTooltip({
  active,
  payload,
  label,
  mode,
}: {
  active?: boolean;
  payload?: Array<{ dataKey?: string; value?: number; payload?: ChartPoint }>;
  label?: number | string;
  mode: ViewMode;
}) {
  if (!active || !payload?.length) return null;

  const point = payload[0]?.payload;
  if (!point) return null;

  const day = typeof label === 'number' ? label : point.day;
  const rows: { key: OpinionKey; value: number; share: number }[] = OPINION_ORDER.map((key) => ({
    key,
    value: point[key],
    share: shareFor(point, key),
  }));

  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 shadow-md text-sm">
      <p className="font-semibold text-slate-800 mb-1.5">{formatDayLabel(Number(day))}</p>
      <ul className="space-y-1">
        {rows.map(({ key, value, share }) => (
          <li key={key} className="flex items-center justify-between gap-6 text-slate-600">
            <span className="flex items-center gap-2">
              <span
                className="inline-block h-2.5 w-2.5 rounded-sm"
                style={{ backgroundColor: OPINION_META[key].color }}
              />
              {OPINION_META[key].label}
            </span>
            <span className="tabular-nums text-slate-800">
              {mode === 'share' ? (
                <>
                  {share}% <span className="text-slate-400">({value})</span>
                </>
              ) : (
                <>
                  {value} <span className="text-slate-400">({share}%)</span>
                </>
              )}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-2 pt-1.5 border-t border-slate-100 text-xs text-slate-500">
        {point.total} agents · net sentiment {(point.netSentiment >= 0 ? '+' : '') + point.netSentiment}%
      </p>
    </div>
  );
}

function MixCallout({
  title,
  point,
}: {
  title: string;
  point: ChartPoint;
}) {
  return (
    <div className="flex-1 min-w-0 rounded-md border border-slate-200 bg-slate-50 px-3 py-2.5">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 mb-1.5">{title}</p>
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-sm tabular-nums">
        {OPINION_ORDER.map((key) => (
          <span key={key} className="text-slate-700">
            <span style={{ color: OPINION_META[key].color }} className="font-semibold">
              {shareFor(point, key)}%
            </span>{' '}
            {OPINION_META[key].short}
          </span>
        ))}
      </div>
    </div>
  );
}

function SingleDayMix({ point }: { point: ChartPoint }) {
  const segments = OPINION_ORDER.map((key) => ({
    key,
    share: shareFor(point, key),
    count: point[key],
    ...OPINION_META[key],
  })).filter((s) => s.share > 0 || s.count > 0);

  return (
    <div className="rounded-md border border-slate-200 bg-slate-50/80 p-5">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2 mb-5">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {formatDayLabel(point.day)} · final mix
          </p>
          <p className="text-2xl font-semibold text-slate-900 mt-1 tabular-nums">
            {(point.netSentiment >= 0 ? '+' : '') + point.netSentiment}%
            <span className="text-sm font-medium text-slate-500 ml-2">net sentiment</span>
          </p>
        </div>
        <p className="text-sm text-slate-500 tabular-nums">{point.total} agents</p>
      </div>

      {/* Stacked composition bar — same visual language as the multi-day area stack */}
      <div
        className="flex h-14 w-full overflow-hidden rounded-md ring-1 ring-slate-200"
        role="img"
        aria-label={`Opinion mix: ${segments.map((s) => `${s.share}% ${s.label}`).join(', ')}`}
      >
        {segments.map((seg) => (
          <div
            key={seg.key}
            className="relative flex items-center justify-center min-w-0 transition-opacity hover:opacity-90"
            style={{
              width: `${seg.share}%`,
              backgroundColor: seg.color,
              opacity: seg.key === 'NEUTRAL' ? 0.85 : 0.92,
            }}
            title={`${seg.label}: ${seg.share}% (${seg.count})`}
          >
            {seg.share >= 12 && (
              <span className="text-xs font-semibold tabular-nums text-white drop-shadow-sm">
                {seg.share}%
              </span>
            )}
          </div>
        ))}
      </div>

      <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-3">
        {OPINION_ORDER.map((key) => {
          const meta = OPINION_META[key];
          const share = shareFor(point, key);
          const count = point[key];
          return (
            <div
              key={key}
              className="rounded-md border border-slate-200 bg-white px-3 py-3"
            >
              <div className="flex items-center gap-2 mb-2">
                <span
                  className="h-2.5 w-2.5 rounded-sm shrink-0"
                  style={{ backgroundColor: meta.color }}
                />
                <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {meta.label}
                </span>
              </div>
              <p className="text-2xl font-semibold tabular-nums text-slate-900">{share}%</p>
              <p className="text-xs text-slate-500 mt-0.5 tabular-nums">
                {count} agent{count === 1 ? '' : 's'}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function OpinionTrajectoryChart({ trajectoryData }: OpinionTrajectoryChartProps) {
  const [mode, setMode] = useState<ViewMode>('share');

  const chartData = useMemo(() => {
    if (!trajectoryData || Object.keys(trajectoryData).length === 0) {
      return [] as ChartPoint[];
    }

    const dayCounts: Record<number, DayCounts> = {};

    Object.values(trajectoryData).forEach((agentHistory) => {
      agentHistory.forEach((record) => {
        const { day, opinion } = record;
        if (!dayCounts[day]) {
          dayCounts[day] = { day, POSITIVE: 0, NEUTRAL: 0, NEGATIVE: 0, total: 0 };
        }
        if (opinion === 'POSITIVE' || opinion === 'NEUTRAL' || opinion === 'NEGATIVE') {
          dayCounts[day][opinion]++;
          dayCounts[day].total++;
        }
      });
    });

    return Object.values(dayCounts)
      .sort((a, b) => a.day - b.day)
      .map((d): ChartPoint => {
        const positiveShare = pct(d.POSITIVE, d.total);
        const neutralShare = pct(d.NEUTRAL, d.total);
        const negativeShare = pct(d.NEGATIVE, d.total);
        return {
          ...d,
          positiveShare,
          neutralShare,
          negativeShare,
          netSentiment: Math.round((positiveShare - negativeShare) * 10) / 10,
        };
      });
  }, [trajectoryData]);

  if (chartData.length === 0) {
    return null;
  }

  const first = chartData[0];
  const last = chartData[chartData.length - 1];
  const singleDay = chartData.length === 1;
  const positiveDelta = Math.round((last.positiveShare - first.positiveShare) * 10) / 10;
  const negativeDelta = Math.round((last.negativeShare - first.negativeShare) * 10) / 10;

  const insight = singleDay
    ? `Only one day of data — showing the final opinion mix (${first.positiveShare}% positive, ${first.neutralShare}% neutral, ${first.negativeShare}% negative).`
    : positiveDelta === 0 && negativeDelta === 0
      ? `Opinion mix held steady from ${formatDayLabel(first.day)} to ${formatDayLabel(last.day)}.`
      : `By ${formatDayLabel(last.day)}, positive ${positiveDelta >= 0 ? 'rose' : 'fell'} ${Math.abs(positiveDelta)} pts (${first.positiveShare}% → ${last.positiveShare}%); negative ${negativeDelta >= 0 ? 'rose' : 'fell'} ${Math.abs(negativeDelta)} pts (${first.negativeShare}% → ${last.negativeShare}%).`;

  const shareKeys = {
    POSITIVE: 'positiveShare',
    NEUTRAL: 'neutralShare',
    NEGATIVE: 'negativeShare',
  } as const;

  const yDomain = mode === 'share' ? [0, 100] : undefined;
  const yTickFormatter = (v: number) => (mode === 'share' ? `${v}%` : String(v));

  return (
    <div className="w-full">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between mb-4">
        <div className="min-w-0">
          <h3 className="text-lg font-semibold text-slate-900">
            {singleDay ? 'Opinion Mix' : 'Opinion Spread Over Time'}
          </h3>
          <p className="text-sm text-slate-500 mt-1">
            {singleDay
              ? 'Final share of agents with positive, neutral, or negative opinions for this run.'
              : 'How the share of agents with positive, neutral, or negative opinions changed each day.'}
          </p>
        </div>
        {!singleDay && (
          <div className="inline-flex shrink-0 rounded-md border border-slate-200 bg-slate-50 p-0.5 self-start">
            {([
              { id: 'share' as const, label: 'Share (%)' },
              { id: 'count' as const, label: 'Count' },
            ]).map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => setMode(opt.id)}
                className={`px-3 py-1.5 text-xs font-semibold rounded transition-colors ${
                  mode === opt.id
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}
      </div>

      <p className="text-sm text-slate-700 mb-4 rounded-md border border-emerald-100 bg-emerald-50/60 px-3 py-2">
        {insight}
      </p>

      {singleDay ? (
        <SingleDayMix point={first} />
      ) : (
        <>
          <div className="w-full h-[300px]">
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={chartData} margin={{ top: 10, right: 16, left: 0, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis
                  dataKey="day"
                  tickFormatter={(d) => `D${d}`}
                  tick={{ fill: '#64748b', fontSize: 12 }}
                  axisLine={{ stroke: '#e2e8f0' }}
                  tickLine={false}
                  label={{ value: 'Day', position: 'insideBottomRight', offset: -2, fill: '#94a3b8', fontSize: 11 }}
                />
                <YAxis
                  yAxisId="left"
                  domain={yDomain}
                  tickFormatter={yTickFormatter}
                  tick={{ fill: '#94a3b8', fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                  width={44}
                />
                {mode === 'share' && (
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    domain={[-100, 100]}
                    tickFormatter={(v) => `${v}%`}
                    tick={{ fill: '#94a3b8', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    width={40}
                  />
                )}
                <Tooltip content={<OpinionTooltip mode={mode} />} />
                <Legend
                  verticalAlign="top"
                  height={32}
                  formatter={(value) => {
                    if (value === 'netSentiment') return 'Net (pos − neg)';
                    return OPINION_META[value as OpinionKey]?.label ?? value;
                  }}
                />
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey={mode === 'share' ? shareKeys.POSITIVE : 'POSITIVE'}
                  name="POSITIVE"
                  stackId="1"
                  stroke={OPINION_META.POSITIVE.color}
                  fill={OPINION_META.POSITIVE.color}
                  fillOpacity={0.75}
                />
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey={mode === 'share' ? shareKeys.NEUTRAL : 'NEUTRAL'}
                  name="NEUTRAL"
                  stackId="1"
                  stroke={OPINION_META.NEUTRAL.color}
                  fill={OPINION_META.NEUTRAL.color}
                  fillOpacity={0.65}
                />
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey={mode === 'share' ? shareKeys.NEGATIVE : 'NEGATIVE'}
                  name="NEGATIVE"
                  stackId="1"
                  stroke={OPINION_META.NEGATIVE.color}
                  fill={OPINION_META.NEGATIVE.color}
                  fillOpacity={0.75}
                />
                {mode === 'share' && (
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="netSentiment"
                    name="netSentiment"
                    stroke="#0f172a"
                    strokeWidth={2}
                    dot={{ r: 3, fill: '#0f172a' }}
                    activeDot={{ r: 5 }}
                  />
                )}
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-4 flex flex-col sm:flex-row items-stretch gap-2 sm:gap-3">
            <MixCallout title={`${formatDayLabel(first.day)} (start)`} point={first} />
            <div className="hidden sm:flex items-center text-slate-300 text-lg px-1" aria-hidden>
              →
            </div>
            <MixCallout title={`${formatDayLabel(last.day)} (final)`} point={last} />
          </div>
        </>
      )}
    </div>
  );
}
