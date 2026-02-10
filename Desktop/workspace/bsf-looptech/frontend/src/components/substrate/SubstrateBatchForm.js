import React, { useState, useEffect } from 'react';
import {
  Box, Button, TextField, Typography, Grid, Select, MenuItem,
  FormControl, InputLabel, Snackbar, Alert, Divider
} from '@mui/material';
import { saveSubstrateBatch, updateSubstrateBatch, getSubstrateTypes, ELUTION_THRESHOLDS } from '../../utils/storage';

const HEAVY_METALS = ['Pb', 'As', 'Cd', 'Cr6', 'Hg', 'Se', 'F', 'B'];

const INITIAL_ANALYSIS = {
  pH: '', moisture: '', ignitionLoss: '',
  Pb: '', As: '', Cd: '', Cr6: '', Hg: '', Se: '', F: '', B: ''
};

const INITIAL_STATE = {
  source: '',
  deliveryDate: new Date().toISOString().split('T')[0],
  wasteType: '',
  weight: '',
  weightUnit: 't',
  status: 'pending',
  analysis: { ...INITIAL_ANALYSIS },
  formulation: null,
  elutionResult: null,
  notes: ''
};

const SubstrateBatchForm = ({ initialData, onSubmitSuccess }) => {
  const [form, setForm] = useState(INITIAL_STATE);
  const [isEditing, setIsEditing] = useState(false);
  const [errors, setErrors] = useState({});
  const [wasteTypes, setWasteTypes] = useState([]);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  useEffect(() => {
    const types = getSubstrateTypes().filter(t => t.category === 'waste_type');
    setWasteTypes(types);
  }, []);

  useEffect(() => {
    if (initialData) {
      setForm({
        ...INITIAL_STATE,
        ...initialData,
        weight: initialData.weight?.toString() || '',
        analysis: { ...INITIAL_ANALYSIS, ...initialData.analysis }
      });
      setIsEditing(true);
    }
  }, [initialData]);

  const handleChange = (field) => (e) => {
    setForm(prev => ({ ...prev, [field]: e.target.value }));
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: undefined }));
  };

  const handleAnalysisChange = (field) => (e) => {
    setForm(prev => ({
      ...prev,
      analysis: { ...prev.analysis, [field]: e.target.value }
    }));
  };

  const validate = () => {
    const newErrors = {};
    if (!form.source.trim()) newErrors.source = '搬入元は必須です';
    if (!form.deliveryDate) newErrors.deliveryDate = '搬入日は必須です';
    if (!form.wasteType) newErrors.wasteType = '廃棄物種別は必須です';
    if (!form.weight || parseFloat(form.weight) <= 0) newErrors.weight = '重量を入力してください';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate()) return;

    const analysisData = {};
    Object.entries(form.analysis).forEach(([key, val]) => {
      if (val !== '' && val !== null && val !== undefined) {
        analysisData[key] = parseFloat(val);
      }
    });

    const hasAnalysis = Object.keys(analysisData).length > 0;
    const data = {
      ...form,
      weight: parseFloat(form.weight),
      analysis: analysisData,
      status: hasAnalysis ? 'analyzed' : 'pending'
    };

    try {
      if (isEditing) {
        updateSubstrateBatch(form.id, data);
        setSnackbar({ open: true, message: '搬入記録を更新しました', severity: 'success' });
      } else {
        saveSubstrateBatch(data);
        setSnackbar({ open: true, message: '搬入記録を登録しました', severity: 'success' });
      }
      setForm(INITIAL_STATE);
      setIsEditing(false);
      if (onSubmitSuccess) onSubmitSuccess();
    } catch (err) {
      setSnackbar({ open: true, message: '保存に失敗しました', severity: 'error' });
    }
  };

  const handleReset = () => {
    setForm(INITIAL_STATE);
    setIsEditing(false);
    setErrors({});
    if (onSubmitSuccess) onSubmitSuccess();
  };

  const getThresholdStatus = (metal, value) => {
    if (!value || !ELUTION_THRESHOLDS[metal]) return null;
    const numVal = parseFloat(value);
    const threshold = ELUTION_THRESHOLDS[metal];
    if (numVal > threshold.limit) return 'fail';
    if (numVal > threshold.limit * 0.8) return 'warn';
    return 'pass';
  };

  return (
    <Box className="section-panel">
      <Typography className="section-panel__title">
        {isEditing ? '搬入記録 編集' : '搬入記録 新規登録'}
      </Typography>

      <form onSubmit={handleSubmit}>
        {/* Basic Info */}
        <Grid container spacing={2}>
          <Grid item xs={12} sm={4}>
            <TextField
              fullWidth size="small" label="搬入元"
              value={form.source} onChange={handleChange('source')}
              error={!!errors.source} helperText={errors.source}
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              fullWidth size="small" label="搬入日" type="date"
              value={form.deliveryDate} onChange={handleChange('deliveryDate')}
              error={!!errors.deliveryDate} helperText={errors.deliveryDate}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small" error={!!errors.wasteType}>
              <InputLabel>廃棄物種別</InputLabel>
              <Select value={form.wasteType} onChange={handleChange('wasteType')} label="廃棄物種別">
                {wasteTypes.map(t => (
                  <MenuItem key={t.id} value={t.name}>{t.name}</MenuItem>
                ))}
                <MenuItem value="汚泥（一般）">汚泥（一般）</MenuItem>
                <MenuItem value="焼却灰">焼却灰</MenuItem>
                <MenuItem value="その他">その他</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={3}>
            <TextField
              fullWidth size="small" label="重量" type="number"
              value={form.weight} onChange={handleChange('weight')}
              error={!!errors.weight} helperText={errors.weight}
              InputProps={{ inputProps: { min: 0, step: 0.1 } }}
              sx={{ '& input': { fontFamily: "'Fira Code', monospace" } }}
            />
          </Grid>
          <Grid item xs={12} sm={2}>
            <FormControl fullWidth size="small">
              <InputLabel>単位</InputLabel>
              <Select value={form.weightUnit} onChange={handleChange('weightUnit')} label="単位">
                <MenuItem value="t">t</MenuItem>
                <MenuItem value="kg">kg</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={7}>
            <TextField
              fullWidth size="small" label="備考"
              value={form.notes} onChange={handleChange('notes')}
            />
          </Grid>
        </Grid>

        <Divider sx={{ my: 3 }} />

        {/* Analysis Results */}
        <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 2 }}>
          分析結果
        </Typography>

        <Grid container spacing={2}>
          <Grid item xs={6} sm={3}>
            <TextField
              fullWidth size="small" label="pH" type="number"
              value={form.analysis.pH} onChange={handleAnalysisChange('pH')}
              InputProps={{ inputProps: { min: 0, max: 14, step: 0.1 } }}
              sx={{ '& input': { fontFamily: "'Fira Code', monospace" } }}
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <TextField
              fullWidth size="small" label="含水率 (%)" type="number"
              value={form.analysis.moisture} onChange={handleAnalysisChange('moisture')}
              InputProps={{ inputProps: { min: 0, max: 100, step: 0.1 } }}
              sx={{ '& input': { fontFamily: "'Fira Code', monospace" } }}
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <TextField
              fullWidth size="small" label="強熱減量 (%)" type="number"
              value={form.analysis.ignitionLoss} onChange={handleAnalysisChange('ignitionLoss')}
              InputProps={{ inputProps: { min: 0, max: 100, step: 0.1 } }}
              sx={{ '& input': { fontFamily: "'Fira Code', monospace" } }}
            />
          </Grid>
        </Grid>

        {/* Heavy Metals */}
        <Typography variant="subtitle2" sx={{ color: 'text.secondary', mt: 3, mb: 2 }}>
          重金属 溶出試験値 (mg/L)
        </Typography>

        <Grid container spacing={2}>
          {HEAVY_METALS.map(metal => {
            const threshold = ELUTION_THRESHOLDS[metal];
            const status = getThresholdStatus(metal, form.analysis[metal]);
            return (
              <Grid item xs={6} sm={3} key={metal}>
                <TextField
                  fullWidth size="small"
                  label={`${threshold.name} (${metal})`}
                  type="number"
                  value={form.analysis[metal]}
                  onChange={handleAnalysisChange(metal)}
                  InputProps={{ inputProps: { min: 0, step: 0.0001 } }}
                  helperText={`基準値: ${threshold.limit} ${threshold.unit}`}
                  sx={{
                    '& input': { fontFamily: "'Fira Code', monospace" },
                    '& .MuiOutlinedInput-root': {
                      ...(status === 'fail' && { '& fieldset': { borderColor: '#DC2626' } }),
                      ...(status === 'warn' && { '& fieldset': { borderColor: '#D97706' } }),
                      ...(status === 'pass' && { '& fieldset': { borderColor: '#16A34A' } })
                    }
                  }}
                />
              </Grid>
            );
          })}
        </Grid>

        <Box sx={{ display: 'flex', gap: 1, mt: 3 }}>
          <Button type="submit" variant="contained" color="primary">
            {isEditing ? '更新' : '登録'}
          </Button>
          <Button variant="outlined" onClick={handleReset}>キャンセル</Button>
        </Box>
      </form>

      <Snackbar open={snackbar.open} autoHideDuration={3000}
        onClose={() => setSnackbar(s => ({ ...s, open: false }))}>
        <Alert severity={snackbar.severity} variant="filled">{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default SubstrateBatchForm;
