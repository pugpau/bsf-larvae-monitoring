import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Button, TextField, Typography, Grid, Select, MenuItem,
  FormControl, InputLabel, Divider,
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import { useNotification } from '../../hooks/useNotification';
import NotificationSnackbar from '../common/NotificationSnackbar';
import { createWasteRecord, updateWasteRecord } from '../../api/wasteApi';
import { WASTE_TYPES, ELUTION_THRESHOLDS } from '../../constants/waste';
import type { WasteRecord } from '../../types/api';

const HEAVY_METALS = ['Pb', 'As', 'Cd', 'Cr6', 'Hg', 'Se', 'F', 'B'] as const;

interface AnalysisState {
  [key: string]: string;
}

const INITIAL_ANALYSIS: AnalysisState = {
  pH: '', moisture: '', ignitionLoss: '',
  Pb: '', As: '', Cd: '', Cr6: '', Hg: '', Se: '', F: '', B: '',
};

interface FormState {
  id?: string;
  source: string;
  deliveryDate: string;
  wasteType: string;
  weight: string;
  weightUnit: string;
  status: string;
  analysis: AnalysisState;
  formulation: Record<string, unknown> | null;
  elutionResult: Record<string, unknown> | null;
  notes: string;
}

const INITIAL_STATE: FormState = {
  source: '',
  deliveryDate: new Date().toISOString().split('T')[0],
  wasteType: '',
  weight: '',
  weightUnit: 't',
  status: 'pending',
  analysis: { ...INITIAL_ANALYSIS },
  formulation: null,
  elutionResult: null,
  notes: '',
};

interface SubstrateBatchFormProps {
  initialData: WasteRecord | Record<string, never>;
  onSubmitSuccess: () => void;
}

const SubstrateBatchForm: React.FC<SubstrateBatchFormProps> = ({ initialData, onSubmitSuccess }) => {
  const [form, setForm] = useState<FormState>(INITIAL_STATE);
  const [isEditing, setIsEditing] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const { notification, notify, closeNotification } = useNotification();

  useEffect(() => {
    if (initialData && 'id' in initialData) {
      const record = initialData as WasteRecord;
      const analysisStrings: AnalysisState = { ...INITIAL_ANALYSIS };
      if (record.analysis) {
        Object.entries(record.analysis).forEach(([key, val]) => {
          if (val !== null && val !== undefined && key in INITIAL_ANALYSIS) {
            analysisStrings[key] = String(val);
          }
        });
      }
      setForm({
        id: record.id,
        source: record.source,
        deliveryDate: record.deliveryDate,
        wasteType: record.wasteType,
        weight: record.weight?.toString() || '',
        weightUnit: record.weightUnit || 't',
        status: record.status,
        analysis: analysisStrings,
        formulation: record.formulation || null,
        elutionResult: record.elutionResult || null,
        notes: record.notes || '',
      });
      setIsEditing(true);
    }
  }, [initialData]);

  const handleChange = useCallback((field: string) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement> | SelectChangeEvent<string>,
  ) => {
    setForm(prev => ({ ...prev, [field]: e.target.value }));
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: '' }));
  }, [errors]);

  const handleAnalysisChange = useCallback((field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm(prev => ({
      ...prev,
      analysis: { ...prev.analysis, [field]: e.target.value },
    }));
  }, []);

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!form.source.trim()) newErrors.source = '搬入元は必須です';
    if (!form.deliveryDate) newErrors.deliveryDate = '搬入日は必須です';
    if (!form.wasteType) newErrors.wasteType = '廃棄物種別は必須です';
    if (!form.weight || parseFloat(form.weight) <= 0) newErrors.weight = '重量を入力してください';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate() || submitting) return;

    const analysisData: Record<string, number> = {};
    Object.entries(form.analysis).forEach(([key, val]) => {
      if (val !== '' && val !== null && val !== undefined) {
        const num = parseFloat(val);
        if (!isNaN(num)) analysisData[key] = num;
      }
    });

    const hasAnalysis = Object.keys(analysisData).length > 0;
    const payload: Partial<WasteRecord> = {
      source: form.source,
      deliveryDate: form.deliveryDate,
      wasteType: form.wasteType,
      weight: parseFloat(form.weight),
      weightUnit: form.weightUnit,
      analysis: hasAnalysis ? analysisData : undefined,
      status: hasAnalysis ? 'analyzed' : 'pending',
      notes: form.notes || undefined,
    };

    setSubmitting(true);
    try {
      if (isEditing && form.id) {
        await updateWasteRecord(form.id, payload);
        notify('搬入記録を更新しました');
      } else {
        await createWasteRecord(payload);
        notify('搬入記録を登録しました');
      }
      setTimeout(() => {
        setForm(INITIAL_STATE);
        setIsEditing(false);
        onSubmitSuccess();
      }, 500);
    } catch {
      notify('保存に失敗しました', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setForm(INITIAL_STATE);
    setIsEditing(false);
    setErrors({});
    onSubmitSuccess();
  };

  const getThresholdStatus = (metal: string, value: string): string | null => {
    if (!value || !ELUTION_THRESHOLDS[metal]) return null;
    const numVal = parseFloat(value);
    if (isNaN(numVal)) return null;
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
                {WASTE_TYPES.map(t => (
                  <MenuItem key={t} value={t}>{t}</MenuItem>
                ))}
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
                      ...(status === 'pass' && { '& fieldset': { borderColor: '#16A34A' } }),
                    },
                  }}
                />
              </Grid>
            );
          })}
        </Grid>

        <Box sx={{ display: 'flex', gap: 1, mt: 3 }}>
          <Button type="submit" variant="contained" color="primary" disabled={submitting}>
            {isEditing ? '更新' : '登録'}
          </Button>
          <Button variant="outlined" onClick={handleReset} disabled={submitting}>キャンセル</Button>
        </Box>
      </form>

      <NotificationSnackbar open={notification.open} message={notification.message} severity={notification.severity} onClose={closeNotification} />
    </Box>
  );
};

export default SubstrateBatchForm;
