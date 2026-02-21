/**
 * Prediction Accuracy — 予測精度KPI
 * Shows accuracy metrics, model info, and recent prediction performance.
 * Placed in Tab 2 (分析ダッシュボード).
 */
import React, { useState, useEffect } from 'react';
import {
  Box, Grid, Typography, Alert, CircularProgress, Chip,
  Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Paper, Button, FormControl, InputLabel, Select, MenuItem
} from '@mui/material';
import {
  fetchAccuracy, fetchMLModels, triggerTraining
} from '../../api/mlApi';
import { PALETTE } from '../../constants/colors';

interface AccuracyData {
  total_predictions: number;
  ml_predictions: number;
  similarity_predictions: number;
  rule_predictions: number;
  ml_ratio: number;
  avg_confidence: number;
  verified_count: number;
  verified_correct: number;
  accuracy: number;
}

interface ModelInfo {
  id: string;
  name: string;
  model_type: string;
  version: number;
  training_records: number;
  metrics: Record<string, number>;
  is_active: boolean;
  created_at: string;
}

interface TrainingResult {
  success: boolean;
  real_records: number;
  synthetic_records: number;
  total_records: number;
  classifier_metrics: Record<string, number>;
  regressor_metrics: Record<string, number>;
  warnings: string[];
}

const PredictionAccuracy: React.FC = () => {
  const [days, setDays] = useState(30);
  const [accuracy, setAccuracy] = useState<AccuracyData | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [trainingResult, setTrainingResult] = useState<TrainingResult | null>(null);
  const [error, setError] = useState('');

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [acc, mdls] = await Promise.all([
        fetchAccuracy(days),
        fetchMLModels(),
      ]);
      setAccuracy(acc);
      setModels(mdls);
    } catch {
      setError('精度データの取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [days]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRetrain = async () => {
    setTraining(true);
    setTrainingResult(null);
    try {
      const result = await triggerTraining({});
      setTrainingResult(result);
      await loadData();
    } catch {
      setError('再学習に失敗しました');
    } finally {
      setTraining(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  const activeModels = models.filter(m => m.is_active);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h3">予測精度・モデル管理</Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>集計期間</InputLabel>
            <Select value={days} onChange={e => setDays(e.target.value as number)} label="集計期間">
              <MenuItem value={7}>7日</MenuItem>
              <MenuItem value={30}>30日</MenuItem>
              <MenuItem value={90}>90日</MenuItem>
              <MenuItem value={365}>1年</MenuItem>
            </Select>
          </FormControl>
          <Button
            variant="outlined"
            size="small"
            onClick={handleRetrain}
            disabled={training}
            sx={{ cursor: 'pointer' }}
          >
            {training ? <CircularProgress size={16} sx={{ mr: 1 }} /> : null}
            再学習
          </Button>
        </Box>
      </Box>

      {error && <Alert severity="warning" sx={{ mb: 2 }}>{error}</Alert>}

      {trainingResult && (
        <Alert
          severity={trainingResult.success ? 'success' : 'warning'}
          sx={{ mb: 2 }}
          onClose={() => setTrainingResult(null)}
        >
          {trainingResult.success
            ? `再学習完了: ${trainingResult.total_records}件 (実データ ${trainingResult.real_records} + 合成 ${trainingResult.synthetic_records})`
            : `再学習失敗: ${trainingResult.warnings.join(', ')}`}
        </Alert>
      )}

      {/* KPI Row */}
      {accuracy && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={6} sm={3}>
            <Box className="kpi-card">
              <div className="kpi-card__label">総予測数</div>
              <div className="kpi-card__value">
                {accuracy.total_predictions}
                <span className="kpi-card__unit">件</span>
              </div>
            </Box>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Box className="kpi-card">
              <div className="kpi-card__label">ML予測率</div>
              <div className="kpi-card__value" style={{
                color: accuracy.ml_ratio >= 0.5 ? PALETTE.success.main : PALETTE.warning.main,
              }}>
                {(accuracy.ml_ratio * 100).toFixed(1)}
                <span className="kpi-card__unit">%</span>
              </div>
            </Box>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Box className="kpi-card">
              <div className="kpi-card__label">平均信頼度</div>
              <div className="kpi-card__value" style={{ fontFamily: "'Fira Code', monospace" }}>
                {(accuracy.avg_confidence * 100).toFixed(1)}
                <span className="kpi-card__unit">%</span>
              </div>
            </Box>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Box className="kpi-card">
              <div className="kpi-card__label">検証精度</div>
              <div className="kpi-card__value" style={{
                color: accuracy.accuracy >= 0.8 ? PALETTE.success.main :
                       accuracy.accuracy >= 0.5 ? PALETTE.warning.main : PALETTE.error.main,
              }}>
                {accuracy.verified_count > 0
                  ? `${(accuracy.accuracy * 100).toFixed(1)}`
                  : '-'}
                {accuracy.verified_count > 0 && <span className="kpi-card__unit">%</span>}
              </div>
            </Box>
          </Grid>
        </Grid>
      )}

      <Grid container spacing={3}>
        {/* Active Models */}
        <Grid item xs={12} md={6}>
          <Box className="section-panel">
            <Typography className="section-panel__title">有効モデル</Typography>
            {activeModels.length === 0 ? (
              <Alert severity="info">
                有効なMLモデルがありません。「再学習」ボタンで学習を開始してください。
              </Alert>
            ) : (
              <Grid container spacing={2}>
                {activeModels.map(m => (
                  <Grid item xs={12} key={m.id}>
                    <Paper variant="outlined" sx={{ p: 2 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="h4">{m.name}</Typography>
                        <Chip
                          label={m.model_type === 'classifier' ? '分類' : '回帰'}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                      </Box>
                      <Typography variant="body2" sx={{ color: 'text.secondary', fontFamily: "'Fira Code', monospace" }}>
                        v{m.version} | 学習データ: {m.training_records}件
                      </Typography>
                      {m.metrics && (
                        <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                          {Object.entries(m.metrics).map(([k, v]) => (
                            <Chip
                              key={k}
                              label={`${k}: ${typeof v === 'number' ? v.toFixed(3) : v}`}
                              size="small"
                              variant="outlined"
                              sx={{ fontFamily: "'Fira Code', monospace", fontSize: 11 }}
                            />
                          ))}
                        </Box>
                      )}
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            )}
          </Box>
        </Grid>

        {/* All Models Table */}
        <Grid item xs={12} md={6}>
          <Box className="section-panel">
            <Typography className="section-panel__title">モデル履歴</Typography>
            {models.length === 0 ? (
              <Alert severity="info">モデルが登録されていません</Alert>
            ) : (
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>名前</TableCell>
                      <TableCell>種別</TableCell>
                      <TableCell align="right">Ver</TableCell>
                      <TableCell align="center">状態</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {models.map(m => (
                      <TableRow key={m.id}>
                        <TableCell sx={{ fontWeight: 500 }}>{m.name}</TableCell>
                        <TableCell>{m.model_type}</TableCell>
                        <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                          {m.version}
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            label={m.is_active ? '有効' : '無効'}
                            size="small"
                            color={m.is_active ? 'success' : 'default'}
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

export default PredictionAccuracy;
