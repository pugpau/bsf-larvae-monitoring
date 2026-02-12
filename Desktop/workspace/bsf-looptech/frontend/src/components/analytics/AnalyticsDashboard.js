/**
 * Quality Management Dashboard — 品質管理
 * Overview of elution test compliance, formulation effectiveness, and regulatory status
 */
import React, { useState, useEffect, useMemo } from 'react';
import {
  Box, Grid, Typography, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Chip, Alert
} from '@mui/material';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer
} from 'recharts';
import { fetchWasteRecords } from '../../api/wasteApi';
import { ELUTION_THRESHOLDS } from '../../constants/waste';

const QualityDashboard = () => {
  const [records, setRecords] = useState([]);

  useEffect(() => {
    fetchWasteRecords({ limit: 500, sort_by: 'delivery_date', sort_order: 'desc' })
      .then(result => setRecords(result.items))
      .catch(() => setRecords([]));
  }, []);

  const analyzed = useMemo(() =>
    records.filter(r => r.analysis && Object.keys(r.analysis).length > 0),
  [records]);

  const formulated = useMemo(() =>
    records.filter(r => r.status === 'formulated'),
  [records]);

  const withElution = useMemo(() =>
    records.filter(r => r.elutionResult),
  [records]);

  const passCount = useMemo(() =>
    withElution.filter(r => r.elutionResult.passed).length,
  [withElution]);

  const passRate = withElution.length > 0
    ? (passCount / withElution.length * 100).toFixed(1)
    : '-';

  // Heavy metal compliance overview
  const metalOverview = useMemo(() => {
    return Object.entries(ELUTION_THRESHOLDS).map(([key, threshold]) => {
      const values = analyzed
        .map(r => r.analysis[key])
        .filter(v => v !== undefined && v !== null);

      const exceedCount = values.filter(v => v > threshold.limit).length;
      const elutionValues = withElution
        .map(r => r.elutionResult?.[key])
        .filter(v => v !== undefined && v !== null);
      const elutionExceed = elutionValues.filter(v => v > threshold.limit).length;

      return {
        key,
        name: threshold.name,
        limit: threshold.limit,
        unit: threshold.unit,
        count: values.length,
        max: values.length > 0 ? Math.max(...values) : null,
        min: values.length > 0 ? Math.min(...values) : null,
        avg: values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : null,
        exceedCount,
        elutionCount: elutionValues.length,
        elutionExceed
      };
    });
  }, [analyzed, withElution]);

  // Pass/fail by waste type
  const byWasteType = useMemo(() => {
    const types = {};
    withElution.forEach(r => {
      const t = r.wasteType || '不明';
      if (!types[t]) types[t] = { name: t, pass: 0, fail: 0 };
      if (r.elutionResult.passed) {
        types[t] = { ...types[t], pass: types[t].pass + 1 };
      } else {
        types[t] = { ...types[t], fail: types[t].fail + 1 };
      }
    });
    return Object.values(types);
  }, [withElution]);

  // Recent elution results
  const recentResults = useMemo(() =>
    withElution
      .sort((a, b) => new Date(b.deliveryDate) - new Date(a.deliveryDate))
      .slice(0, 10),
  [withElution]);

  return (
    <Box>
      {/* KPI Row */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} sm={3}>
          <Box className="kpi-card">
            <div className="kpi-card__label">総搬入数</div>
            <div className="kpi-card__value">
              {records.length}
              <span className="kpi-card__unit">件</span>
            </div>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box className="kpi-card">
            <div className="kpi-card__label">分析済</div>
            <div className="kpi-card__value">
              {analyzed.length}
              <span className="kpi-card__unit">件</span>
            </div>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box className="kpi-card">
            <div className="kpi-card__label">配合済</div>
            <div className="kpi-card__value">
              {formulated.length}
              <span className="kpi-card__unit">件</span>
            </div>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box className="kpi-card">
            <div className="kpi-card__label">溶出試験合格率</div>
            <div className="kpi-card__value" style={{ color: passRate !== '-' && parseFloat(passRate) >= 90 ? '#16A34A' : '#D97706' }}>
              {passRate}
              {passRate !== '-' && <span className="kpi-card__unit">%</span>}
            </div>
          </Box>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Heavy Metal Compliance Table */}
        <Grid item xs={12} md={7}>
          <Box className="section-panel">
            <Typography className="section-panel__title">重金属項目別 コンプライアンス状況</Typography>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>項目</TableCell>
                    <TableCell align="right">基準値</TableCell>
                    <TableCell align="right">最大値</TableCell>
                    <TableCell align="right">平均値</TableCell>
                    <TableCell align="center">搬入時超過</TableCell>
                    <TableCell align="center">溶出超過</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {metalOverview.map(m => {
                    const maxExceeds = m.max !== null && m.max > m.limit;
                    return (
                      <TableRow key={m.key}>
                        <TableCell sx={{ fontWeight: 500 }}>
                          {m.name} ({m.key})
                        </TableCell>
                        <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                          {m.limit} {m.unit}
                        </TableCell>
                        <TableCell align="right" sx={{
                          fontFamily: "'Fira Code', monospace",
                          color: maxExceeds ? '#DC2626' : 'inherit',
                          fontWeight: maxExceeds ? 600 : 400
                        }}>
                          {m.max !== null ? m.max.toFixed(4) : '-'}
                        </TableCell>
                        <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                          {m.avg !== null ? m.avg.toFixed(4) : '-'}
                        </TableCell>
                        <TableCell align="center">
                          {m.count > 0 ? (
                            m.exceedCount > 0 ? (
                              <Chip label={`${m.exceedCount}/${m.count}`} size="small" color="error" variant="outlined" />
                            ) : (
                              <Chip label={`0/${m.count}`} size="small" color="success" variant="outlined" />
                            )
                          ) : '-'}
                        </TableCell>
                        <TableCell align="center">
                          {m.elutionCount > 0 ? (
                            m.elutionExceed > 0 ? (
                              <Chip label={`${m.elutionExceed}/${m.elutionCount}`} size="small" color="error" variant="outlined" />
                            ) : (
                              <Chip label={`0/${m.elutionCount}`} size="small" color="success" variant="outlined" />
                            )
                          ) : '-'}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        </Grid>

        {/* Pass/Fail by Waste Type */}
        <Grid item xs={12} md={5}>
          <Box className="chart-container">
            <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 1 }}>
              廃棄物種別 合否実績
            </Typography>
            {byWasteType.length === 0 ? (
              <Alert severity="info">溶出試験データがありません</Alert>
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={byWasteType} margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontFamily: "'Fira Code', monospace", fontSize: 11 }} allowDecimals={false} />
                  <RechartsTooltip />
                  <Bar dataKey="pass" name="合格" fill="#16A34A" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="fail" name="不合格" fill="#DC2626" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Box>
        </Grid>

        {/* Recent Elution Results */}
        <Grid item xs={12}>
          <Box className="section-panel">
            <Typography className="section-panel__title">直近の溶出試験結果</Typography>
            {recentResults.length === 0 ? (
              <Alert severity="info">溶出試験結果がありません</Alert>
            ) : (
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>搬入日</TableCell>
                      <TableCell>搬入元</TableCell>
                      <TableCell>種別</TableCell>
                      <TableCell>固化剤</TableCell>
                      <TableCell align="right">添加量</TableCell>
                      {Object.entries(ELUTION_THRESHOLDS).slice(0, 4).map(([key, t]) => (
                        <TableCell key={key} align="right">{t.name}</TableCell>
                      ))}
                      <TableCell align="center">判定</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {recentResults.map(r => (
                      <TableRow key={r.id}>
                        <TableCell sx={{ fontFamily: "'Fira Code', monospace", whiteSpace: 'nowrap' }}>
                          {r.deliveryDate}
                        </TableCell>
                        <TableCell sx={{ fontWeight: 500 }}>{r.source}</TableCell>
                        <TableCell>{r.wasteType}</TableCell>
                        <TableCell>{r.formulation?.solidifierType || '-'}</TableCell>
                        <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                          {r.formulation?.solidifierAmount || '-'} {r.formulation?.solidifierUnit || ''}
                        </TableCell>
                        {Object.entries(ELUTION_THRESHOLDS).slice(0, 4).map(([key, threshold]) => {
                          const val = r.elutionResult?.[key];
                          const exceeded = val !== undefined && val > threshold.limit;
                          return (
                            <TableCell key={key} align="right" sx={{
                              fontFamily: "'Fira Code', monospace",
                              color: exceeded ? '#DC2626' : val !== undefined ? '#16A34A' : 'inherit',
                              fontWeight: exceeded ? 600 : 400
                            }}>
                              {val !== undefined ? val.toFixed(4) : '-'}
                            </TableCell>
                          );
                        })}
                        <TableCell align="center">
                          <Chip
                            label={r.elutionResult.passed ? '合格' : '不合格'}
                            size="small"
                            color={r.elutionResult.passed ? 'success' : 'error'}
                            variant="outlined"
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
};

export default QualityDashboard;
