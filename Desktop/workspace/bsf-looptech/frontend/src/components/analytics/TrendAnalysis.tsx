/**
 * Trend Analysis — 月次トレンド分析
 * Monthly trend charts for predictions, accuracy, and waste volumes.
 * Placed in Tab 2 (分析ダッシュボード).
 */
import React, { useState, useEffect } from 'react';
import {
  Box, Grid, Typography, Alert, CircularProgress,
  FormControl, InputLabel, Select, MenuItem
} from '@mui/material';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Legend,
  BarChart, Bar
} from 'recharts';
import { fetchTrends } from '../../api/mlApi';
import { CHART_COLORS, GRID_STROKE } from '../../constants/colors';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { getAnimationProps } from '../../utils/recharts';
import type { TrendData } from '../../types/api';

const TrendAnalysis: React.FC = () => {
  const prefersReduced = useReducedMotion();
  const animProps = getAnimationProps(prefersReduced);
  const [months, setMonths] = useState(6);
  const [data, setData] = useState<TrendData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const result = await fetchTrends(months);
        if (!cancelled) setData(result);
      } catch {
        if (!cancelled) setError('トレンドデータの取得に失敗しました');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [months]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="warning" sx={{ mb: 2 }}>{error}</Alert>;
  }

  const hasPredictions = data?.monthly_predictions && data.monthly_predictions.length > 0;
  const hasAccuracy = data?.monthly_accuracy && data.monthly_accuracy.length > 0;
  const hasWaste = data?.monthly_waste && data.monthly_waste.length > 0;
  const noData = !hasPredictions && !hasAccuracy && !hasWaste;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h3">月次トレンド分析</Typography>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>期間</InputLabel>
          <Select value={months} onChange={e => setMonths(e.target.value as number)} label="期間">
            <MenuItem value={3}>3ヶ月</MenuItem>
            <MenuItem value={6}>6ヶ月</MenuItem>
            <MenuItem value={12}>12ヶ月</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {noData && (
        <Alert severity="info">
          トレンドデータがまだありません。予測や搬入データが蓄積されると表示されます。
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Prediction Method Distribution */}
        {hasPredictions && (
          <Grid item xs={12} md={6}>
            <Box className="chart-container">
              <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 1 }}>
                月別予測手法分布
              </Typography>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={data!.monthly_predictions} margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontFamily: "'Fira Code', monospace", fontSize: 11 }} allowDecimals={false} />
                  <RechartsTooltip />
                  <Legend />
                  <Bar dataKey="ml" name="ML" fill={CHART_COLORS.primary} stackId="a" radius={[0, 0, 0, 0]} {...animProps} />
                  <Bar dataKey="similarity" name="類似" fill={CHART_COLORS.info} stackId="a" {...animProps} />
                  <Bar dataKey="rule" name="ルール" fill={CHART_COLORS.warning} stackId="a" radius={[4, 4, 0, 0]} {...animProps} />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </Grid>
        )}

        {/* Accuracy Trend */}
        {hasAccuracy && (
          <Grid item xs={12} md={6}>
            <Box className="chart-container">
              <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 1 }}>
                予測精度推移
              </Typography>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={data!.monthly_accuracy} margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fontFamily: "'Fira Code', monospace", fontSize: 11 }}
                    label={{ value: '精度 (%)', angle: -90, position: 'insideLeft', style: { fontSize: 12 } }}
                  />
                  <RechartsTooltip formatter={(val: number) => [`${val.toFixed(1)}%`, '精度']} />
                  <Line
                    type="monotone" dataKey="accuracy" name="精度"
                    stroke={CHART_COLORS.primary} strokeWidth={2}
                    dot={{ r: 4 }} activeDot={{ r: 6 }}
                    {...animProps}
                  />
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </Grid>
        )}

        {/* Waste Volume Trend */}
        {hasWaste && (
          <Grid item xs={12}>
            <Box className="chart-container">
              <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 1 }}>
                搬入・配合件数推移
              </Typography>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={data!.monthly_waste} margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontFamily: "'Fira Code', monospace", fontSize: 11 }} allowDecimals={false} />
                  <RechartsTooltip />
                  <Legend />
                  <Bar dataKey="records" name="搬入" fill={CHART_COLORS.secondary} radius={[4, 4, 0, 0]} {...animProps} />
                  <Bar dataKey="formulated" name="配合済" fill={CHART_COLORS.success} radius={[4, 4, 0, 0]} {...animProps} />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default TrendAnalysis;
