/**
 * Cost Optimization Panel — コスト最適化
 * PuLP-based LP optimization for minimum-cost formulation.
 * Placed in Tab 1 (配合管理).
 */
import React, { useState, useCallback } from 'react';
import {
  Box, Grid, Typography, TextField, Button, Alert, Chip,
  CircularProgress, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, FormControl, InputLabel, Select, MenuItem
} from '@mui/material';
import { optimizeFormulation } from '../../utils/apiClient';
import { WASTE_TYPES } from '../../constants/waste';

interface CostItem {
  material_name: string;
  material_type: string;
  amount: number;
  unit: string;
  unit_cost: number;
  total_cost: number;
}

interface OptResult {
  status: string;
  recommendation: Record<string, unknown>;
  total_cost: number;
  cost_breakdown: CostItem[];
  constraints_satisfied: Record<string, unknown>;
  solver_time_ms: number;
  reasoning: string[];
}

const OptimizationPanel: React.FC = () => {
  const [wasteType, setWasteType] = useState('汚泥（一般）');
  const [wasteWeight, setWasteWeight] = useState('1.0');
  const [maxBudget, setMaxBudget] = useState('');
  const [pH, setPH] = useState('');
  const [moisture, setMoisture] = useState('');
  const [metals, setMetals] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OptResult | null>(null);
  const [error, setError] = useState('');

  const handleOptimize = useCallback(async () => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const analysis: Record<string, number> = {};
      if (pH) analysis.pH = parseFloat(pH);
      if (moisture) analysis.moisture = parseFloat(moisture);
      for (const [key, val] of Object.entries(metals)) {
        if (val) analysis[key] = parseFloat(val);
      }

      const res = await optimizeFormulation(analysis, wasteType, {
        wasteWeight: parseFloat(wasteWeight) || 1.0,
        maxBudget: maxBudget ? parseFloat(maxBudget) : null,
      });
      setResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Optimization failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [pH, moisture, metals, wasteType, wasteWeight, maxBudget]);

  const statusColor = (status: string) => {
    switch (status) {
      case 'optimal': return 'success' as const;
      case 'infeasible': return 'warning' as const;
      default: return 'error' as const;
    }
  };

  const statusLabel = (status: string) => {
    switch (status) {
      case 'optimal': return '最適解';
      case 'infeasible': return '実行不可能';
      default: return 'エラー';
    }
  };

  return (
    <Box>
      <Box className="section-panel" sx={{ mb: 3 }}>
        <Typography className="section-panel__title">コスト最適化</Typography>

        <Grid container spacing={2}>
          <Grid item xs={12} sm={3}>
            <FormControl fullWidth size="small">
              <InputLabel>廃棄物種別</InputLabel>
              <Select
                value={wasteType}
                onChange={e => setWasteType(e.target.value)}
                label="廃棄物種別"
              >
                {WASTE_TYPES.map(t => <MenuItem key={t} value={t}>{t}</MenuItem>)}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={6} sm={3}>
            <TextField
              label="廃棄物量 (t)" size="small" fullWidth type="number"
              value={wasteWeight} onChange={e => setWasteWeight(e.target.value)}
              inputProps={{ step: 0.1, min: 0.1 }}
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <TextField
              label="予算上限 (円)" size="small" fullWidth type="number"
              value={maxBudget} onChange={e => setMaxBudget(e.target.value)}
              placeholder="任意"
              inputProps={{ step: 1000, min: 0 }}
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <TextField
              label="pH" size="small" fullWidth type="number"
              value={pH} onChange={e => setPH(e.target.value)}
              inputProps={{ step: 0.1 }}
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <TextField
              label="含水率 (%)" size="small" fullWidth type="number"
              value={moisture} onChange={e => setMoisture(e.target.value)}
              inputProps={{ step: 0.1 }}
            />
          </Grid>
          {['Pb', 'As', 'Cd', 'Cr6'].map(key => (
            <Grid item xs={6} sm={3} key={key}>
              <TextField
                label={`${key} (mg/L)`} size="small" fullWidth type="number"
                value={metals[key] || ''}
                onChange={e => setMetals(prev => ({ ...prev, [key]: e.target.value }))}
                inputProps={{ step: 0.001, min: 0 }}
              />
            </Grid>
          ))}

          <Grid item xs={12}>
            <Button
              variant="contained"
              onClick={handleOptimize}
              disabled={loading}
              sx={{ cursor: 'pointer' }}
            >
              {loading ? <CircularProgress size={20} sx={{ mr: 1 }} /> : null}
              コスト最適化を実行
            </Button>
          </Grid>
        </Grid>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {result && (
        <Grid container spacing={3}>
          {/* KPI Row */}
          <Grid item xs={12}>
            <Grid container spacing={2}>
              <Grid item xs={6} sm={3}>
                <Box className="kpi-card">
                  <div className="kpi-card__label">ステータス</div>
                  <div className="kpi-card__value" style={{ fontSize: 14 }}>
                    <Chip
                      label={statusLabel(result.status)}
                      color={statusColor(result.status)}
                      size="small"
                    />
                  </div>
                </Box>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Box className="kpi-card">
                  <div className="kpi-card__label">総コスト</div>
                  <div className="kpi-card__value" style={{ fontFamily: "'Fira Code', monospace" }}>
                    {result.total_cost > 0 ? `¥${result.total_cost.toLocaleString()}` : '-'}
                  </div>
                </Box>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Box className="kpi-card">
                  <div className="kpi-card__label">材料数</div>
                  <div className="kpi-card__value">
                    {result.cost_breakdown.length}
                    <span className="kpi-card__unit">種</span>
                  </div>
                </Box>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Box className="kpi-card">
                  <div className="kpi-card__label">ソルバー時間</div>
                  <div className="kpi-card__value" style={{ fontFamily: "'Fira Code', monospace" }}>
                    {result.solver_time_ms.toFixed(1)}
                    <span className="kpi-card__unit">ms</span>
                  </div>
                </Box>
              </Grid>
            </Grid>
          </Grid>

          {/* Cost Breakdown Table */}
          {result.cost_breakdown.length > 0 && (
            <Grid item xs={12} md={7}>
              <Box className="section-panel">
                <Typography className="section-panel__title">コスト内訳</Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>材料名</TableCell>
                        <TableCell>種別</TableCell>
                        <TableCell align="right">使用量</TableCell>
                        <TableCell align="right">単価</TableCell>
                        <TableCell align="right">小計</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {result.cost_breakdown.map((item, i) => (
                        <TableRow key={i}>
                          <TableCell sx={{ fontWeight: 500 }}>{item.material_name}</TableCell>
                          <TableCell>
                            <Chip
                              label={item.material_type === 'solidifier' ? '固化材' : '抑制剤'}
                              size="small"
                              variant="outlined"
                              color={item.material_type === 'solidifier' ? 'primary' : 'info'}
                            />
                          </TableCell>
                          <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                            {item.amount} {item.unit}
                          </TableCell>
                          <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                            ¥{item.unit_cost}/{item.unit}
                          </TableCell>
                          <TableCell align="right" sx={{
                            fontFamily: "'Fira Code', monospace",
                            fontWeight: 600,
                          }}>
                            ¥{item.total_cost.toLocaleString()}
                          </TableCell>
                        </TableRow>
                      ))}
                      <TableRow>
                        <TableCell colSpan={4} sx={{ fontWeight: 600 }}>合計</TableCell>
                        <TableCell align="right" sx={{
                          fontFamily: "'Fira Code', monospace",
                          fontWeight: 700,
                          color: '#1E40AF',
                        }}>
                          ¥{result.total_cost.toLocaleString()}
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            </Grid>
          )}

          {/* Reasoning */}
          <Grid item xs={12} md={5}>
            <Box className="section-panel">
              <Typography className="section-panel__title">最適化根拠</Typography>
              {result.reasoning.map((r, i) => (
                <Typography key={i} variant="body2" sx={{ color: 'text.secondary', mb: 0.5 }}>
                  {r}
                </Typography>
              ))}
            </Box>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

export default OptimizationPanel;
