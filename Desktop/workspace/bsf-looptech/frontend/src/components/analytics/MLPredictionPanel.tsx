/**
 * ML Prediction Panel — ML予測UI
 * Provides ML-based formulation prediction with model info and confidence display.
 * Placed in Tab 1 (配合管理).
 */
import React, { useState, useCallback } from 'react';
import {
  Box, Grid, Typography, TextField, Button, Alert, Chip,
  CircularProgress, Paper, Divider, FormControl, InputLabel,
  Select, MenuItem
} from '@mui/material';
import { predictFormulation, predictElution } from '../../utils/apiClient';
import { WASTE_TYPES } from '../../constants/waste';

const METAL_FIELDS = [
  { key: 'Pb', label: '鉛 (Pb)' },
  { key: 'As', label: 'ヒ素 (As)' },
  { key: 'Cd', label: 'カドミウム (Cd)' },
  { key: 'Cr6', label: '六価クロム (Cr6)' },
  { key: 'Hg', label: '水銀 (Hg)' },
  { key: 'Se', label: 'セレン (Se)' },
  { key: 'F', label: 'フッ素 (F)' },
  { key: 'B', label: 'ホウ素 (B)' },
];

interface PredictionResult {
  recommendation: Record<string, unknown>;
  confidence: number;
  method: string;
  reasoning: string[];
  model_version?: number;
  similar_records?: unknown[];
}

interface ElutionResult {
  passed: boolean;
  confidence: number;
  method: string;
  metal_predictions: Record<string, number>;
  reasoning: string[];
}

const MLPredictionPanel: React.FC = () => {
  const [wasteType, setWasteType] = useState('汚泥（一般）');
  const [pH, setPH] = useState('');
  const [moisture, setMoisture] = useState('');
  const [metals, setMetals] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [elutionResult, setElutionResult] = useState<ElutionResult | null>(null);
  const [error, setError] = useState('');

  const buildAnalysis = useCallback(() => {
    const analysis: Record<string, number> = {};
    if (pH) analysis.pH = parseFloat(pH);
    if (moisture) analysis.moisture = parseFloat(moisture);
    for (const [key, val] of Object.entries(metals)) {
      if (val) analysis[key] = parseFloat(val);
    }
    return analysis;
  }, [pH, moisture, metals]);

  const handlePredict = useCallback(async () => {
    setLoading(true);
    setError('');
    setResult(null);
    setElutionResult(null);
    try {
      const analysis = buildAnalysis();
      const pred = await predictFormulation(analysis, wasteType);
      setResult(pred);

      // Auto-run elution prediction
      if (pred.recommendation) {
        const elution = await predictElution(analysis, pred.recommendation);
        setElutionResult(elution);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Prediction failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [buildAnalysis, wasteType]);

  const updateMetal = (key: string, value: string) => {
    setMetals(prev => ({ ...prev, [key]: value }));
  };

  const getMethodLabel = (method: string) => {
    switch (method) {
      case 'ml': return { label: 'ML予測', color: 'primary' as const };
      case 'similarity': return { label: '類似実績', color: 'info' as const };
      case 'rule': return { label: 'ルールベース', color: 'warning' as const };
      default: return { label: method, color: 'default' as const };
    }
  };

  const rec = result?.recommendation as Record<string, unknown> | undefined;

  return (
    <Box>
      <Box className="section-panel" sx={{ mb: 3 }}>
        <Typography className="section-panel__title">ML配合予測</Typography>

        <Grid container spacing={2}>
          <Grid item xs={12} sm={4}>
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
          <Grid item xs={6} sm={4}>
            <TextField
              label="pH" size="small" fullWidth type="number"
              value={pH} onChange={e => setPH(e.target.value)}
              inputProps={{ step: 0.1, min: 0, max: 14 }}
            />
          </Grid>
          <Grid item xs={6} sm={4}>
            <TextField
              label="含水率 (%)" size="small" fullWidth type="number"
              value={moisture} onChange={e => setMoisture(e.target.value)}
              inputProps={{ step: 0.1, min: 0, max: 100 }}
            />
          </Grid>

          {METAL_FIELDS.map(m => (
            <Grid item xs={6} sm={3} key={m.key}>
              <TextField
                label={`${m.label} (mg/L)`} size="small" fullWidth type="number"
                value={metals[m.key] || ''}
                onChange={e => updateMetal(m.key, e.target.value)}
                inputProps={{ step: 0.001, min: 0 }}
              />
            </Grid>
          ))}

          <Grid item xs={12}>
            <Button
              variant="contained"
              onClick={handlePredict}
              disabled={loading || (!pH && !moisture && Object.keys(metals).length === 0)}
              sx={{ cursor: 'pointer' }}
            >
              {loading ? <CircularProgress size={20} sx={{ mr: 1 }} /> : null}
              配合予測を実行
            </Button>
          </Grid>
        </Grid>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {result && (
        <Grid container spacing={3}>
          {/* Prediction Result */}
          <Grid item xs={12} md={7}>
            <Box className="section-panel">
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Typography className="section-panel__title" sx={{ mb: '0 !important', pb: '0 !important', borderBottom: 'none !important' }}>
                  予測結果
                </Typography>
                <Chip
                  label={getMethodLabel(result.method).label}
                  color={getMethodLabel(result.method).color}
                  size="small"
                  variant="outlined"
                />
                {result.model_version && (
                  <Chip label={`v${result.model_version}`} size="small" variant="outlined" />
                )}
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Box className="kpi-card">
                    <div className="kpi-card__label">固化材</div>
                    <div className="kpi-card__value" style={{ fontSize: 14 }}>
                      {rec?.solidifierType as string || '-'}
                    </div>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box className="kpi-card">
                    <div className="kpi-card__label">添加量</div>
                    <div className="kpi-card__value">
                      {rec?.solidifierAmount as number || '-'}
                      <span className="kpi-card__unit">{rec?.solidifierUnit as string || 'kg/t'}</span>
                    </div>
                  </Box>
                </Grid>
                {Boolean(rec?.suppressorType) && rec && (
                  <>
                    <Grid item xs={6}>
                      <Box className="kpi-card">
                        <div className="kpi-card__label">溶出抑制剤</div>
                        <div className="kpi-card__value" style={{ fontSize: 14 }}>
                          {String(rec.suppressorType)}
                        </div>
                      </Box>
                    </Grid>
                    <Grid item xs={6}>
                      <Box className="kpi-card">
                        <div className="kpi-card__label">抑制剤量</div>
                        <div className="kpi-card__value">
                          {String(rec.suppressorAmount)}
                          <span className="kpi-card__unit">{String(rec.suppressorUnit || 'kg/t')}</span>
                        </div>
                      </Box>
                    </Grid>
                  </>
                )}
              </Grid>

              <Divider sx={{ my: 2 }} />

              <Typography variant="body2" sx={{ fontWeight: 500, mb: 1 }}>推論根拠:</Typography>
              {result.reasoning.map((r, i) => (
                <Typography key={i} variant="body2" sx={{ color: 'text.secondary', pl: 1 }}>
                  {r}
                </Typography>
              ))}
            </Box>
          </Grid>

          {/* Confidence & Elution */}
          <Grid item xs={12} md={5}>
            <Box className="kpi-card" sx={{ mb: 2 }}>
              <div className="kpi-card__label">予測信頼度</div>
              <div className="kpi-card__value" style={{
                color: result.confidence >= 0.7 ? '#16A34A' :
                       result.confidence >= 0.4 ? '#D97706' : '#DC2626',
              }}>
                {(result.confidence * 100).toFixed(1)}
                <span className="kpi-card__unit">%</span>
              </div>
            </Box>

            {elutionResult && (
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="h4" sx={{ mb: 1 }}>溶出試験予測</Typography>
                <Chip
                  label={elutionResult.passed ? '合格見込み' : '要注意'}
                  color={elutionResult.passed ? 'success' : 'error'}
                  size="small"
                  sx={{ mb: 1 }}
                />
                <Typography variant="body2" sx={{
                  fontFamily: "'Fira Code', monospace",
                  color: 'text.secondary',
                  mb: 1,
                }}>
                  確率: {(elutionResult.confidence * 100).toFixed(1)}%
                </Typography>
                {elutionResult.reasoning.map((r, i) => (
                  <Typography key={i} variant="body2" sx={{ color: 'text.secondary', fontSize: 12 }}>
                    {r}
                  </Typography>
                ))}
              </Paper>
            )}
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

export default MLPredictionPanel;
