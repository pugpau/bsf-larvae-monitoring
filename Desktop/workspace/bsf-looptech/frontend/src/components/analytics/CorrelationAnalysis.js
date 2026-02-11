/**
 * Waste Treatment Correlation Analysis
 * Analyzes relationships between waste analysis values and formulation quantities
 */
import React, { useState, useMemo } from 'react';
import {
  Box, Grid, Typography, FormControl, InputLabel, Select, MenuItem,
  Button, ButtonGroup, Alert, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Tooltip, IconButton
} from '@mui/material';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer,
  BarChart, Bar, Cell, ReferenceLine
} from 'recharts';
import { Download as DownloadIcon } from '@mui/icons-material';
import { getSubstrateBatches, ELUTION_THRESHOLDS } from '../../utils/storage';

// Chart colors from MASTER.md design system
const CHART_COLORS = [
  '#1E40AF', '#3B82F6', '#0284C7', '#16A34A',
  '#D97706', '#DC2626', '#7C3AED', '#64748B'
];

// Metrics available for correlation analysis
const ANALYSIS_METRICS = [
  { value: 'pH', label: 'pH', unit: '' },
  { value: 'moisture', label: '含水率', unit: '%' },
  { value: 'ignitionLoss', label: '強熱減量', unit: '%' },
  { value: 'Pb', label: '鉛 (Pb)', unit: 'mg/L' },
  { value: 'As', label: 'ヒ素 (As)', unit: 'mg/L' },
  { value: 'Cd', label: 'カドミウム (Cd)', unit: 'mg/L' },
  { value: 'Cr6', label: '六価クロム (Cr6)', unit: 'mg/L' },
  { value: 'F', label: 'フッ素 (F)', unit: 'mg/L' },
  { value: 'B', label: 'ホウ素 (B)', unit: 'mg/L' }
];

const FORMULATION_METRICS = [
  { value: 'solidifierAmount', label: '固化剤添加量', unit: 'kg/t' },
  { value: 'suppressorAmount', label: '抑制材添加量', unit: 'kg/t' }
];

const ALL_METRICS = [...ANALYSIS_METRICS, ...FORMULATION_METRICS];

const calculateCorrelation = (x, y) => {
  const n = x.length;
  if (n < 3 || n !== y.length) return 0;

  const sumX = x.reduce((a, b) => a + b, 0);
  const sumY = y.reduce((a, b) => a + b, 0);
  const sumXY = x.reduce((total, xi, i) => total + xi * y[i], 0);
  const sumX2 = x.reduce((total, xi) => total + xi * xi, 0);
  const sumY2 = y.reduce((total, yi) => total + yi * yi, 0);

  const numerator = n * sumXY - sumX * sumY;
  const denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));

  return denominator === 0 ? 0 : numerator / denominator;
};

const calculateR2 = (correlation) => correlation * correlation;

const getCorrelationStrength = (r) => {
  const abs = Math.abs(r);
  if (abs >= 0.7) return { label: '強い相関', color: '#DC2626' };
  if (abs >= 0.4) return { label: '中程度', color: '#D97706' };
  if (abs >= 0.2) return { label: '弱い相関', color: '#3B82F6' };
  return { label: '相関なし', color: '#64748B' };
};

const getMetricValue = (record, metricKey) => {
  if (FORMULATION_METRICS.some(m => m.value === metricKey)) {
    return record.formulation?.[metricKey] ?? null;
  }
  return record.analysis?.[metricKey] ?? null;
};

const ScatterTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <Box sx={{
      bgcolor: '#fff', border: '1px solid #E2E8F0', borderRadius: 1, p: 1.5,
      boxShadow: '0 2px 4px rgba(0,0,0,0.08)', fontFamily: "'Fira Code', monospace", fontSize: 12
    }}>
      <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>{d.source}</Typography>
      <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: 11 }}>{d.deliveryDate} | {d.wasteType}</Typography>
      <Typography variant="body2" sx={{ color: '#1E40AF' }}>X: {d.x?.toFixed(4)}</Typography>
      <Typography variant="body2" sx={{ color: '#D97706' }}>Y: {d.y?.toFixed(4)}</Typography>
    </Box>
  );
};

const CorrelationAnalysis = () => {
  const [xAxis, setXAxis] = useState('Pb');
  const [yAxis, setYAxis] = useState('solidifierAmount');
  const [viewMode, setViewMode] = useState('scatter');
  const [wasteTypeFilter, setWasteTypeFilter] = useState('all');

  const records = useMemo(() => {
    const all = getSubstrateBatches();
    return all.filter(r =>
      r.status === 'formulated' &&
      r.analysis && Object.keys(r.analysis).length > 0 &&
      r.formulation
    );
  }, []);

  const filteredRecords = useMemo(() => {
    if (wasteTypeFilter === 'all') return records;
    return records.filter(r => r.wasteType === wasteTypeFilter);
  }, [records, wasteTypeFilter]);

  const wasteTypes = useMemo(() => {
    return [...new Set(records.map(r => r.wasteType))];
  }, [records]);

  const scatterData = useMemo(() => {
    return filteredRecords
      .map(r => ({
        x: getMetricValue(r, xAxis),
        y: getMetricValue(r, yAxis),
        source: r.source,
        deliveryDate: r.deliveryDate,
        wasteType: r.wasteType
      }))
      .filter(d => d.x !== null && d.y !== null && !isNaN(d.x) && !isNaN(d.y));
  }, [filteredRecords, xAxis, yAxis]);

  const correlation = useMemo(() => {
    if (scatterData.length < 3) return 0;
    return calculateCorrelation(
      scatterData.map(d => d.x),
      scatterData.map(d => d.y)
    );
  }, [scatterData]);

  const r2 = calculateR2(correlation);
  const strength = getCorrelationStrength(correlation);

  // Correlation matrix for all metric pairs
  const correlationMatrix = useMemo(() => {
    const metricsToShow = ALL_METRICS.filter(m => {
      return filteredRecords.some(r => {
        const v = getMetricValue(r, m.value);
        return v !== null && v !== undefined && !isNaN(v) && v !== 0;
      });
    });

    const matrix = metricsToShow.map(m1 => {
      const row = { metric: m1.label, key: m1.value };
      metricsToShow.forEach(m2 => {
        const pairs = filteredRecords
          .map(r => [getMetricValue(r, m1.value), getMetricValue(r, m2.value)])
          .filter(([a, b]) => a !== null && b !== null && !isNaN(a) && !isNaN(b));
        if (pairs.length >= 3) {
          row[m2.value] = calculateCorrelation(pairs.map(p => p[0]), pairs.map(p => p[1]));
        } else {
          row[m2.value] = null;
        }
      });
      return row;
    });

    return { matrix, metrics: metricsToShow };
  }, [filteredRecords]);

  // Bar chart: formulation effectiveness (Pb reduction %)
  const effectivenessData = useMemo(() => {
    return records
      .filter(r => r.elutionResult && r.analysis)
      .map(r => {
        const metals = Object.keys(ELUTION_THRESHOLDS);
        const reductions = metals
          .filter(m => r.analysis[m] && r.elutionResult[m])
          .map(m => ({
            metal: ELUTION_THRESHOLDS[m].name,
            before: r.analysis[m],
            after: r.elutionResult[m],
            reduction: ((r.analysis[m] - r.elutionResult[m]) / r.analysis[m] * 100)
          }))
          .filter(d => d.reduction > 0);
        return {
          source: `${r.source} (${r.deliveryDate})`,
          reductions,
          avgReduction: reductions.length > 0
            ? reductions.reduce((s, d) => s + d.reduction, 0) / reductions.length
            : 0
        };
      })
      .filter(d => d.avgReduction > 0)
      .sort((a, b) => b.avgReduction - a.avgReduction);
  }, [records]);

  const handleExport = () => {
    const headers = ['搬入元', '搬入日', '廃棄物種別',
      ...ALL_METRICS.map(m => m.label)];
    const rows = filteredRecords.map(r =>
      [r.source, r.deliveryDate, r.wasteType,
        ...ALL_METRICS.map(m => getMetricValue(r, m.value) ?? '')]
    );
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `correlation_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const xMeta = ALL_METRICS.find(m => m.value === xAxis);
  const yMeta = ALL_METRICS.find(m => m.value === yAxis);

  if (records.length === 0) {
    return (
      <Box className="section-panel">
        <Alert severity="info">
          配合済みの搬入記録がありません。搬入管理タブで記録を登録し、配合管理タブで配合を設定してください。
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box className="section-panel" sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography className="section-panel__title" sx={{ mb: '0 !important', pb: '0 !important', borderBottom: 'none !important' }}>
            廃棄物分析・配合 相関分析
          </Typography>
          <IconButton size="small" onClick={handleExport} aria-label="CSV出力">
            <DownloadIcon />
          </IconButton>
        </Box>

        {/* Filters */}
        <Box className="filter-bar">
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>廃棄物種別</InputLabel>
            <Select value={wasteTypeFilter} onChange={e => setWasteTypeFilter(e.target.value)} label="廃棄物種別">
              <MenuItem value="all">すべて</MenuItem>
              {wasteTypes.map(t => <MenuItem key={t} value={t}>{t}</MenuItem>)}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>X軸</InputLabel>
            <Select value={xAxis} onChange={e => setXAxis(e.target.value)} label="X軸">
              {ALL_METRICS.map(m => <MenuItem key={m.value} value={m.value}>{m.label}</MenuItem>)}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>Y軸</InputLabel>
            <Select value={yAxis} onChange={e => setYAxis(e.target.value)} label="Y軸">
              {ALL_METRICS.map(m => <MenuItem key={m.value} value={m.value}>{m.label}</MenuItem>)}
            </Select>
          </FormControl>
          <ButtonGroup size="small">
            <Button variant={viewMode === 'scatter' ? 'contained' : 'outlined'} onClick={() => setViewMode('scatter')}>散布図</Button>
            <Button variant={viewMode === 'matrix' ? 'contained' : 'outlined'} onClick={() => setViewMode('matrix')}>相関行列</Button>
            <Button variant={viewMode === 'effect' ? 'contained' : 'outlined'} onClick={() => setViewMode('effect')}>配合効果</Button>
          </ButtonGroup>
        </Box>
      </Box>

      {/* KPI Row */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} sm={3}>
          <Box className="kpi-card">
            <div className="kpi-card__label">相関係数 (r)</div>
            <div className="kpi-card__value" style={{ color: strength.color }}>
              {correlation.toFixed(3)}
            </div>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box className="kpi-card">
            <div className="kpi-card__label">決定係数 (R²)</div>
            <div className="kpi-card__value" style={{ fontFamily: "'Fira Code', monospace" }}>
              {r2.toFixed(3)}
            </div>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box className="kpi-card">
            <div className="kpi-card__label">相関強度</div>
            <div className="kpi-card__value" style={{ fontSize: 16, color: strength.color }}>
              {strength.label}
            </div>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box className="kpi-card">
            <div className="kpi-card__label">データ数</div>
            <div className="kpi-card__value">
              {scatterData.length}
              <span className="kpi-card__unit">件</span>
            </div>
          </Box>
        </Grid>
      </Grid>

      {/* Chart Area */}
      {viewMode === 'scatter' && (
        <Box className="chart-container" sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 1 }}>
            {xMeta?.label} vs {yMeta?.label}
          </Typography>
          {scatterData.length < 3 ? (
            <Alert severity="warning" sx={{ my: 2 }}>
              散布図の描画には3件以上のデータが必要です（現在: {scatterData.length}件）
            </Alert>
          ) : (
            <ResponsiveContainer width="100%" height={400}>
              <ScatterChart margin={{ top: 20, right: 30, bottom: 40, left: 50 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis
                  dataKey="x" type="number" name={xMeta?.label}
                  label={{ value: `${xMeta?.label} ${xMeta?.unit ? `(${xMeta.unit})` : ''}`, position: 'insideBottom', offset: -10, style: { fontSize: 12 } }}
                  tick={{ fontFamily: "'Fira Code', monospace", fontSize: 11 }}
                />
                <YAxis
                  dataKey="y" type="number" name={yMeta?.label}
                  label={{ value: `${yMeta?.label} ${yMeta?.unit ? `(${yMeta.unit})` : ''}`, angle: -90, position: 'insideLeft', style: { fontSize: 12 } }}
                  tick={{ fontFamily: "'Fira Code', monospace", fontSize: 11 }}
                />
                <RechartsTooltip content={<ScatterTooltip />} />
                {wasteTypeFilter === 'all' && wasteTypes.length > 1 ? (
                  wasteTypes.map((type, i) => (
                    <Scatter
                      key={type}
                      name={type}
                      data={scatterData.filter(d => d.wasteType === type)}
                      fill={CHART_COLORS[i % CHART_COLORS.length]}
                    />
                  ))
                ) : (
                  <Scatter name="データ" data={scatterData} fill={CHART_COLORS[0]} />
                )}
              </ScatterChart>
            </ResponsiveContainer>
          )}
          <Typography variant="caption" sx={{ color: 'text.secondary', mt: 1, display: 'block' }}>
            r = {correlation.toFixed(3)} | R² = {r2.toFixed(3)} | n = {scatterData.length}
          </Typography>
        </Box>
      )}

      {viewMode === 'matrix' && (
        <Box className="section-panel" sx={{ mb: 3, overflow: 'auto' }}>
          <Typography className="section-panel__title">相関行列</Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600, position: 'sticky', left: 0, bgcolor: '#F1F5F9', zIndex: 1 }}>指標</TableCell>
                  {correlationMatrix.metrics.map(m => (
                    <TableCell key={m.value} align="center" sx={{ fontSize: 11, minWidth: 70 }}>
                      {m.label}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {correlationMatrix.matrix.map(row => (
                  <TableRow key={row.key}>
                    <TableCell sx={{ fontWeight: 500, fontSize: 12, position: 'sticky', left: 0, bgcolor: '#fff', zIndex: 1 }}>
                      {row.metric}
                    </TableCell>
                    {correlationMatrix.metrics.map(m => {
                      const val = row[m.value];
                      if (val === null) return <TableCell key={m.value} align="center">-</TableCell>;
                      const isIdentity = row.key === m.value;
                      const s = getCorrelationStrength(val);
                      return (
                        <TableCell key={m.value} align="center" sx={{
                          fontFamily: "'Fira Code', monospace",
                          fontSize: 11,
                          bgcolor: isIdentity ? '#F1F5F9' : undefined,
                          color: isIdentity ? '#64748B' : s.color,
                          fontWeight: Math.abs(val) >= 0.7 ? 600 : 400
                        }}>
                          <Tooltip title={isIdentity ? '' : `${s.label} (R²=${(val * val).toFixed(3)})`}>
                            <span>{val.toFixed(2)}</span>
                          </Tooltip>
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {viewMode === 'effect' && (
        <Box className="chart-container" sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 1 }}>
            配合による溶出値低減率（平均）
          </Typography>
          {effectivenessData.length === 0 ? (
            <Alert severity="info" sx={{ my: 2 }}>
              溶出試験結果のあるデータがありません
            </Alert>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={effectivenessData} layout="vertical" margin={{ top: 10, right: 30, bottom: 10, left: 120 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis
                  type="number" domain={[0, 100]}
                  label={{ value: '平均低減率 (%)', position: 'insideBottom', offset: -5, style: { fontSize: 12 } }}
                  tick={{ fontFamily: "'Fira Code', monospace", fontSize: 11 }}
                />
                <YAxis
                  dataKey="source" type="category"
                  tick={{ fontSize: 11 }}
                  width={110}
                />
                <RechartsTooltip
                  formatter={(val) => [`${val.toFixed(1)}%`, '平均低減率']}
                />
                <ReferenceLine x={50} stroke="#D97706" strokeDasharray="3 3" label={{ value: '50%', position: 'top', fontSize: 11 }} />
                <Bar dataKey="avgReduction" radius={[0, 4, 4, 0]}>
                  {effectivenessData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Box>
      )}

      {/* Insights */}
      <Box className="section-panel">
        <Typography className="section-panel__title">分析インサイト</Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" sx={{ mb: 1 }}>
              <strong>{xMeta?.label}</strong> と <strong>{yMeta?.label}</strong> の相関係数は{' '}
              <span style={{ fontFamily: "'Fira Code', monospace", fontWeight: 600, color: strength.color }}>
                {correlation.toFixed(3)}
              </span>
              {' '}（{strength.label}）です。
              決定係数 R² = {r2.toFixed(3)} より、
              {r2 >= 0.5
                ? `${yMeta?.label}の変動の${(r2 * 100).toFixed(0)}%が${xMeta?.label}で説明できます。`
                : `${xMeta?.label}による${yMeta?.label}の説明力は限定的です。`
              }
            </Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" component="div">
              <strong>活用ポイント:</strong>
              <ul style={{ margin: '4px 0', paddingLeft: 20 }}>
                <li>強い正の相関がある分析値→固化剤量の増加が必要</li>
                <li>廃棄物種別ごとに異なる傾向を確認</li>
                <li>溶出試験結果との比較で配合効果を検証</li>
              </ul>
            </Typography>
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default CorrelationAnalysis;
