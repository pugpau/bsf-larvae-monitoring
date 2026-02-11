/**
 * Formulation Manager — 配合管理
 * Manage solidifier/suppressor formulations for incoming waste
 */
import React, { useState, useEffect } from 'react';
import {
  Box, Grid, Typography, Button, TextField, Select, MenuItem,
  FormControl, InputLabel, Table, TableHead, TableRow, TableCell,
  TableContainer, TableBody, Paper, Chip, Alert, Snackbar,
  CircularProgress, Collapse, LinearProgress, Tooltip
} from '@mui/material';
import { AutoFixHigh as AiIcon } from '@mui/icons-material';
import { getSubstrateBatches, updateSubstrateBatch, getSubstrateTypes, ELUTION_THRESHOLDS, getRecommendation } from '../../utils/storage';

const FormulationManager = () => {
  const [records, setRecords] = useState([]);
  const [solidifiers, setSolidifiers] = useState([]);
  const [suppressors, setSuppressors] = useState([]);
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [formulation, setFormulation] = useState({
    solidifierType: '', solidifierAmount: '', solidifierUnit: 'kg/t',
    suppressorType: '', suppressorAmount: '', suppressorUnit: 'kg/t'
  });
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [recommendation, setRecommendation] = useState(null);
  const [recommending, setRecommending] = useState(false);

  useEffect(() => {
    const allRecords = getSubstrateBatches();
    const analyzed = allRecords.filter(r => r.status === 'analyzed' || r.status === 'formulated');
    setRecords(analyzed.sort((a, b) => new Date(b.deliveryDate) - new Date(a.deliveryDate)));

    const types = getSubstrateTypes();
    setSolidifiers(types.filter(t => t.category === 'solidifier'));
    setSuppressors(types.filter(t => t.category === 'suppressor'));
  }, []);

  const handleFormulationChange = (field) => (e) => {
    setFormulation(prev => ({ ...prev, [field]: e.target.value }));
  };

  const handleSaveFormulation = () => {
    if (!selectedRecord) return;
    if (!formulation.solidifierType || !formulation.solidifierAmount) {
      setSnackbar({ open: true, message: '固化剤と添加量は必須です', severity: 'warning' });
      return;
    }

    const updatedFormulation = {
      ...formulation,
      solidifierAmount: parseFloat(formulation.solidifierAmount),
      suppressorAmount: formulation.suppressorAmount ? parseFloat(formulation.suppressorAmount) : 0
    };

    updateSubstrateBatch(selectedRecord.id, {
      formulation: updatedFormulation,
      status: 'formulated'
    });

    setSnackbar({ open: true, message: '配合を保存しました', severity: 'success' });

    const allRecords = getSubstrateBatches();
    const analyzed = allRecords.filter(r => r.status === 'analyzed' || r.status === 'formulated');
    setRecords(analyzed.sort((a, b) => new Date(b.deliveryDate) - new Date(a.deliveryDate)));
    setSelectedRecord({ ...selectedRecord, formulation: updatedFormulation, status: 'formulated' });
  };

  const handleRecommend = async () => {
    if (!selectedRecord?.analysis) return;
    setRecommending(true);
    setRecommendation(null);
    try {
      const result = await getRecommendation(selectedRecord.analysis, selectedRecord.wasteType);
      setRecommendation(result);
    } catch {
      setSnackbar({ open: true, message: 'AI推奨の取得に失敗しました', severity: 'error' });
    } finally {
      setRecommending(false);
    }
  };

  const handleApplyRecommendation = () => {
    if (!recommendation?.recommendation) return;
    const rec = recommendation.recommendation;
    setFormulation({
      solidifierType: rec.solidifierType || '',
      solidifierAmount: rec.solidifierAmount?.toString() || '',
      solidifierUnit: rec.solidifierUnit || 'kg/t',
      suppressorType: rec.suppressorType || '',
      suppressorAmount: rec.suppressorAmount?.toString() || '',
      suppressorUnit: rec.suppressorUnit || 'kg/t',
    });
    setSnackbar({ open: true, message: 'AI推奨値を反映しました', severity: 'info' });
  };

  const handleSelectRecord = (record) => {
    setSelectedRecord(record);
    setRecommendation(null);
    if (record.formulation) {
      setFormulation({
        solidifierType: record.formulation.solidifierType || '',
        solidifierAmount: record.formulation.solidifierAmount?.toString() || '',
        solidifierUnit: record.formulation.solidifierUnit || 'kg/t',
        suppressorType: record.formulation.suppressorType || '',
        suppressorAmount: record.formulation.suppressorAmount?.toString() || '',
        suppressorUnit: record.formulation.suppressorUnit || 'kg/t'
      });
    } else {
      setFormulation({
        solidifierType: '', solidifierAmount: '', solidifierUnit: 'kg/t',
        suppressorType: '', suppressorAmount: '', suppressorUnit: 'kg/t'
      });
    }
  };

  const getExceedingMetals = (analysis) => {
    if (!analysis) return [];
    return Object.entries(ELUTION_THRESHOLDS)
      .filter(([key, threshold]) => {
        const val = analysis[key];
        return val !== undefined && val !== null && val > threshold.limit;
      })
      .map(([key, threshold]) => ({
        key,
        name: threshold.name,
        value: analysis[key],
        limit: threshold.limit,
        ratio: (analysis[key] / threshold.limit).toFixed(1)
      }));
  };

  return (
    <Box>
      <Grid container spacing={3}>
        {/* Left: Record List */}
        <Grid item xs={12} md={5}>
          <Box className="section-panel">
            <Typography className="section-panel__title">配合対象 搬入物</Typography>

            {records.length === 0 ? (
              <Alert severity="info">分析済みの搬入記録がありません。搬入管理タブで記録を登録してください。</Alert>
            ) : (
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>搬入日</TableCell>
                      <TableCell>搬入元</TableCell>
                      <TableCell>種別</TableCell>
                      <TableCell>状態</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {records.map(record => (
                      <TableRow
                        key={record.id}
                        hover
                        selected={selectedRecord?.id === record.id}
                        onClick={() => handleSelectRecord(record)}
                        sx={{ cursor: 'pointer' }}
                      >
                        <TableCell sx={{ fontFamily: "'Fira Code', monospace", whiteSpace: 'nowrap' }}>
                          {record.deliveryDate}
                        </TableCell>
                        <TableCell>{record.source}</TableCell>
                        <TableCell>{record.wasteType}</TableCell>
                        <TableCell>
                          <Chip
                            label={record.status === 'formulated' ? '配合済' : '未配合'}
                            size="small"
                            color={record.status === 'formulated' ? 'success' : 'warning'}
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

        {/* Right: Formulation Panel */}
        <Grid item xs={12} md={7}>
          {selectedRecord ? (
            <Box>
              {/* Analysis Summary */}
              <Box className="section-panel" sx={{ mb: 3 }}>
                <Typography className="section-panel__title">
                  分析結果サマリ — {selectedRecord.source} ({selectedRecord.deliveryDate})
                </Typography>

                <Grid container spacing={2} sx={{ mb: 2 }}>
                  <Grid item xs={4}>
                    <Box className="kpi-card">
                      <div className="kpi-card__label">pH</div>
                      <div className="kpi-card__value">
                        {selectedRecord.analysis?.pH ?? '-'}
                      </div>
                    </Box>
                  </Grid>
                  <Grid item xs={4}>
                    <Box className="kpi-card">
                      <div className="kpi-card__label">含水率</div>
                      <div className="kpi-card__value">
                        {selectedRecord.analysis?.moisture ?? '-'}
                        <span className="kpi-card__unit">%</span>
                      </div>
                    </Box>
                  </Grid>
                  <Grid item xs={4}>
                    <Box className="kpi-card">
                      <div className="kpi-card__label">強熱減量</div>
                      <div className="kpi-card__value">
                        {selectedRecord.analysis?.ignitionLoss ?? '-'}
                        <span className="kpi-card__unit">%</span>
                      </div>
                    </Box>
                  </Grid>
                </Grid>

                {/* Exceeding metals */}
                {(() => {
                  const exceeding = getExceedingMetals(selectedRecord.analysis);
                  if (exceeding.length === 0) {
                    return <Alert severity="success" sx={{ mb: 2 }}>全項目基準値内です</Alert>;
                  }
                  return (
                    <Alert severity="warning" sx={{ mb: 2 }}>
                      <strong>基準超過項目:</strong>
                      {exceeding.map(m => (
                        <span key={m.key} style={{ marginLeft: 12, fontFamily: "'Fira Code', monospace" }}>
                          {m.name}: {m.value} mg/L (基準の{m.ratio}倍)
                        </span>
                      ))}
                    </Alert>
                  );
                })()}
              </Box>

              {/* Formulation Form */}
              <Box className="section-panel">
                <Typography className="section-panel__title">配合設定</Typography>

                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 1 }}>
                      固化剤
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={5}>
                    <FormControl fullWidth size="small">
                      <InputLabel>固化剤種類</InputLabel>
                      <Select value={formulation.solidifierType} onChange={handleFormulationChange('solidifierType')} label="固化剤種類">
                        {solidifiers.map(s => (
                          <MenuItem key={s.id} value={s.name}>{s.name}</MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={6} sm={4}>
                    <TextField
                      fullWidth size="small" label="添加量" type="number"
                      value={formulation.solidifierAmount}
                      onChange={handleFormulationChange('solidifierAmount')}
                      InputProps={{ inputProps: { min: 0, step: 1 } }}
                      sx={{ '& input': { fontFamily: "'Fira Code', monospace" } }}
                    />
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <FormControl fullWidth size="small">
                      <InputLabel>単位</InputLabel>
                      <Select value={formulation.solidifierUnit} onChange={handleFormulationChange('solidifierUnit')} label="単位">
                        <MenuItem value="kg/t">kg/t</MenuItem>
                        <MenuItem value="kg">kg</MenuItem>
                        <MenuItem value="%">%</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid item xs={12}>
                    <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 1, mt: 1 }}>
                      溶出抑制材
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={5}>
                    <FormControl fullWidth size="small">
                      <InputLabel>抑制材種類</InputLabel>
                      <Select value={formulation.suppressorType} onChange={handleFormulationChange('suppressorType')} label="抑制材種類">
                        <MenuItem value="">なし</MenuItem>
                        {suppressors.map(s => (
                          <MenuItem key={s.id} value={s.name}>{s.name}</MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={6} sm={4}>
                    <TextField
                      fullWidth size="small" label="添加量" type="number"
                      value={formulation.suppressorAmount}
                      onChange={handleFormulationChange('suppressorAmount')}
                      InputProps={{ inputProps: { min: 0, step: 0.1 } }}
                      sx={{ '& input': { fontFamily: "'Fira Code', monospace" } }}
                    />
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <FormControl fullWidth size="small">
                      <InputLabel>単位</InputLabel>
                      <Select value={formulation.suppressorUnit} onChange={handleFormulationChange('suppressorUnit')} label="単位">
                        <MenuItem value="kg/t">kg/t</MenuItem>
                        <MenuItem value="kg">kg</MenuItem>
                        <MenuItem value="%">%</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>

                <Box sx={{ display: 'flex', gap: 1, mt: 3, flexWrap: 'wrap' }}>
                  <Button
                    variant="outlined"
                    startIcon={recommending ? <CircularProgress size={18} /> : <AiIcon />}
                    onClick={handleRecommend}
                    disabled={recommending || !selectedRecord.analysis || Object.keys(selectedRecord.analysis).length === 0}
                  >
                    {recommending ? 'AI分析中…' : 'AI推奨'}
                  </Button>
                  <Button variant="contained" color="primary" onClick={handleSaveFormulation}>
                    配合を保存
                  </Button>
                </Box>

                {/* AI Recommendation Result */}
                <Collapse in={recommendation !== null}>
                  {recommendation && (
                    <Box
                      sx={{
                        mt: 3, p: 2, borderRadius: 1,
                        border: '1px solid',
                        borderColor: recommendation.confidence >= 0.6 ? 'success.main' : 'warning.main',
                        bgcolor: recommendation.confidence >= 0.6 ? 'success.50' : 'warning.50',
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <AiIcon fontSize="small" />
                          AI推奨配合
                          <Chip
                            label={recommendation.method === 'similarity' ? '類似実績ベース' : 'ルールベース'}
                            size="small" variant="outlined"
                            sx={{ ml: 1, fontSize: '0.7rem' }}
                          />
                        </Typography>
                        <Tooltip title={`信頼度: ${(recommendation.confidence * 100).toFixed(0)}%`}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 120 }}>
                            <LinearProgress
                              variant="determinate"
                              value={recommendation.confidence * 100}
                              color={recommendation.confidence >= 0.6 ? 'success' : 'warning'}
                              sx={{ flex: 1, height: 8, borderRadius: 4 }}
                            />
                            <Typography variant="caption" sx={{ fontFamily: "'Fira Code', monospace", fontWeight: 600 }}>
                              {(recommendation.confidence * 100).toFixed(0)}%
                            </Typography>
                          </Box>
                        </Tooltip>
                      </Box>

                      <Grid container spacing={1} sx={{ mb: 1.5 }}>
                        <Grid item xs={6}>
                          <Typography variant="caption" color="text.secondary">固化剤</Typography>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            {recommendation.recommendation.solidifierType}{' '}
                            <span style={{ fontFamily: "'Fira Code', monospace" }}>
                              {recommendation.recommendation.solidifierAmount} {recommendation.recommendation.solidifierUnit}
                            </span>
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="caption" color="text.secondary">溶出抑制材</Typography>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            {recommendation.recommendation.suppressorType || 'なし'}{' '}
                            {recommendation.recommendation.suppressorAmount > 0 && (
                              <span style={{ fontFamily: "'Fira Code', monospace" }}>
                                {recommendation.recommendation.suppressorAmount} {recommendation.recommendation.suppressorUnit}
                              </span>
                            )}
                          </Typography>
                        </Grid>
                      </Grid>

                      {/* Reasoning */}
                      <Box sx={{ mb: 1.5 }}>
                        {recommendation.reasoning.map((r, i) => (
                          <Typography key={i} variant="caption" display="block" sx={{ color: 'text.secondary', lineHeight: 1.6 }}>
                            {r}
                          </Typography>
                        ))}
                      </Box>

                      {/* Similar Records */}
                      {recommendation.similarRecords?.length > 0 && (
                        <Box sx={{ mb: 1.5 }}>
                          <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                            参考実績:
                          </Typography>
                          <Table size="small" sx={{ mt: 0.5 }}>
                            <TableHead>
                              <TableRow>
                                <TableCell sx={{ py: 0.5, fontSize: '0.7rem' }}>搬入元</TableCell>
                                <TableCell sx={{ py: 0.5, fontSize: '0.7rem' }}>日付</TableCell>
                                <TableCell sx={{ py: 0.5, fontSize: '0.7rem' }}>類似度</TableCell>
                                <TableCell sx={{ py: 0.5, fontSize: '0.7rem' }}>合否</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {recommendation.similarRecords.slice(0, 3).map((sr, i) => (
                                <TableRow key={i}>
                                  <TableCell sx={{ py: 0.3, fontSize: '0.75rem' }}>{sr.source}</TableCell>
                                  <TableCell sx={{ py: 0.3, fontSize: '0.75rem', fontFamily: "'Fira Code', monospace" }}>
                                    {sr.deliveryDate}
                                  </TableCell>
                                  <TableCell sx={{ py: 0.3, fontSize: '0.75rem', fontFamily: "'Fira Code', monospace" }}>
                                    {((1 - Math.min(sr.distance, 1)) * 100).toFixed(0)}%
                                  </TableCell>
                                  <TableCell sx={{ py: 0.3 }}>
                                    <Chip
                                      label={sr.passed ? '合格' : sr.passed === false ? '不合格' : '-'}
                                      size="small"
                                      color={sr.passed ? 'success' : sr.passed === false ? 'error' : 'default'}
                                      variant="outlined"
                                      sx={{ height: 20, fontSize: '0.65rem' }}
                                    />
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </Box>
                      )}

                      <Button
                        variant="contained" size="small"
                        onClick={handleApplyRecommendation}
                        sx={{ mt: 0.5 }}
                      >
                        推奨値を反映
                      </Button>
                    </Box>
                  )}
                </Collapse>
              </Box>
            </Box>
          ) : (
            <Box className="section-panel">
              <Typography sx={{ color: 'text.secondary', textAlign: 'center', py: 6 }}>
                左の一覧から搬入物を選択してください
              </Typography>
            </Box>
          )}
        </Grid>
      </Grid>

      <Snackbar open={snackbar.open} autoHideDuration={3000}
        onClose={() => setSnackbar(s => ({ ...s, open: false }))}>
        <Alert severity={snackbar.severity} variant="filled">{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default FormulationManager;
