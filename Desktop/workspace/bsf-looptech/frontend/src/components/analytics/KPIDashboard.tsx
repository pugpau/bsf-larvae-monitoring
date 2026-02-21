/**
 * KPI Dashboard — 運用KPIリアルタイム表示
 * 6つのKPI指標 + アラート + ミニトレンドチャート
 * 30秒ポーリングで自動更新
 * Placed in Tab 2 (分析ダッシュボード) at the top.
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box, Grid, Typography, Alert, CircularProgress, Chip,
  FormControl, InputLabel, Select, MenuItem,
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Legend,
} from 'recharts';
import {
  fetchKPIRealtime, fetchKPITrends, fetchKPIAlerts,
} from '../../api/kpiApi';
import { CHART_COLORS, getKPIStatusColor } from '../../constants/colors';
import { formatKPIValue } from '../../utils/formatters';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { getAnimationProps } from '../../utils/recharts';
import type { KPIMetric, KPIRealtimeData, KPITrendPoint, KPIAlert as KPIAlertItem } from '../../types/api';

// KPIs where "up" is bad (reverse trend color)
const INVERSE_TREND_METRICS = new Set([
  'violation_rate', 'material_cost', 'avg_processing_time',
]);

const POLLING_INTERVAL = 30_000; // 30 seconds
const MAX_VISIBLE_ALERTS = 3;

const KPIDashboard: React.FC = () => {
  const prefersReduced = useReducedMotion();
  const animProps = getAnimationProps(prefersReduced);
  const [days, setDays] = useState(7);
  const [realtime, setRealtime] = useState<KPIRealtimeData | null>(null);
  const [trends, setTrends] = useState<KPITrendPoint[]>([]);
  const [alerts, setAlerts] = useState<KPIAlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadAll = useCallback(async () => {
    try {
      setError('');
      const [rt, tr, al] = await Promise.all([
        fetchKPIRealtime(days),
        fetchKPITrends(6),
        fetchKPIAlerts(days),
      ]);
      setRealtime(rt);
      setTrends(tr.data || []);
      setAlerts(al.alerts || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'KPI取得エラー';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [days]);

  const pollRealtime = useCallback(async () => {
    try {
      const rt = await fetchKPIRealtime(days);
      setRealtime(rt);
    } catch {
      // Silent fail for polling — don't overwrite existing data
    }
  }, [days]);

  // Initial load + period change
  useEffect(() => {
    setLoading(true);
    loadAll();
  }, [loadAll]);

  // Polling for realtime only
  useEffect(() => {
    intervalRef.current = setInterval(pollRealtime, POLLING_INTERVAL);
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [pollRealtime]);

  const handleDaysChange = (event: SelectChangeEvent<number>) => {
    setDays(event.target.value as number);
  };

  const renderTrendIndicator = (metric: KPIMetric, metricKey: string) => {
    if (metric.trend === null) return null;

    const isInverse = INVERSE_TREND_METRICS.has(metricKey);
    const isPositive = metric.trend > 0;

    // For inverse metrics: up = bad (red), down = good (green)
    // For normal metrics: up = good (green), down = bad (red)
    let trendClass: string;
    if (metric.trend === 0) {
      trendClass = 'kpi-card__trend--stable';
    } else if (isInverse) {
      trendClass = isPositive ? 'kpi-card__trend--up' : 'kpi-card__trend--down';
    } else {
      trendClass = isPositive ? 'kpi-card__trend--down' : 'kpi-card__trend--up';
    }

    return (
      <div className={`kpi-card__trend ${trendClass}`}>
        {metric.trend > 0 ? '+' : ''}{metric.trend.toFixed(1)}%
      </div>
    );
  };

  const formatValue = (metric: KPIMetric): string =>
    formatKPIValue(metric.value, metric.unit);

  const getValueColor = (metric: KPIMetric): string | undefined =>
    getKPIStatusColor(metric.status);

  const renderKPICard = (metric: KPIMetric, metricKey: string) => (
    <Box className="kpi-card">
      <div className="kpi-card__label">{metric.label}</div>
      <div
        className="kpi-card__value"
        style={{ color: getValueColor(metric) }}
      >
        {formatValue(metric)}
        <span className="kpi-card__unit">{metric.unit}</span>
      </div>
      {renderTrendIndicator(metric, metricKey)}
    </Box>
  );

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  const kpiMetrics: Array<{ key: string; metric: KPIMetric }> = realtime
    ? [
        { key: 'processing_volume', metric: realtime.processing_volume },
        { key: 'formulation_success_rate', metric: realtime.formulation_success_rate },
        { key: 'material_cost', metric: realtime.material_cost },
        { key: 'ml_usage_rate', metric: realtime.ml_usage_rate },
        { key: 'avg_processing_time', metric: realtime.avg_processing_time },
        { key: 'violation_rate', metric: realtime.violation_rate },
      ]
    : [];

  const visibleAlerts = alerts.slice(0, MAX_VISIBLE_ALERTS);
  const hiddenCount = alerts.length - MAX_VISIBLE_ALERTS;

  return (
    <Box className="section-panel">
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography className="section-panel__title">KPIダッシュボード</Typography>
        <FormControl size="small" sx={{ minWidth: 100 }}>
          <InputLabel>期間</InputLabel>
          <Select
            value={days}
            label="期間"
            onChange={handleDaysChange}
          >
            <MenuItem value={7}>7日</MenuItem>
            <MenuItem value={30}>30日</MenuItem>
            <MenuItem value={90}>90日</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {error && <Alert severity="warning" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Alerts */}
      {visibleAlerts.length > 0 && (
        <Box sx={{ mb: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
          {visibleAlerts.map((alert, i) => (
            <Alert
              key={`${alert.metric}-${i}`}
              severity={alert.severity === 'critical' ? 'error' : 'warning'}
              sx={{ py: 0.5 }}
            >
              {alert.message}
            </Alert>
          ))}
          {hiddenCount > 0 && (
            <Chip
              label={`他${hiddenCount}件のアラート`}
              size="small"
              color="warning"
              variant="outlined"
            />
          )}
        </Box>
      )}

      {/* KPI Cards */}
      {kpiMetrics.length > 0 && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {kpiMetrics.map(({ key, metric }) => (
            <Grid item xs={6} sm={4} md={2} key={key}>
              {renderKPICard(metric, key)}
            </Grid>
          ))}
        </Grid>
      )}

      {/* Mini Trend Chart */}
      {trends.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
            月次トレンド
          </Typography>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" tick={{ fontSize: 12 }} />
              <YAxis yAxisId="left" tick={{ fontSize: 12 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} />
              <RechartsTooltip />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="processing_volume"
                stroke={CHART_COLORS.processing_volume}
                name="処理量"
                strokeWidth={2}
                dot={{ r: 3 }}
                {...animProps}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="success_rate"
                stroke={CHART_COLORS.success_rate}
                name="成功率(%)"
                strokeWidth={2}
                dot={{ r: 3 }}
                {...animProps}
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      )}
    </Box>
  );
};

export default KPIDashboard;
