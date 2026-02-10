import React, { useState, useEffect } from 'react';
import {
  Box, TextField, Button, Typography, Grid, Select, MenuItem,
  FormControl, InputLabel, IconButton, Snackbar, Alert, FormHelperText
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon } from '@mui/icons-material';
import { saveSubstrateType, updateSubstrateType, MATERIAL_CATEGORIES } from '../../utils/storage';

const INITIAL_STATE = {
  name: '',
  category: '',
  description: '',
  supplier: '',
  unitCost: '',
  unit: 'kg',
  attributes: []
};

const SubstrateTypeForm = ({ initialData, onSubmitSuccess }) => {
  const [form, setForm] = useState(INITIAL_STATE);
  const [isEditing, setIsEditing] = useState(false);
  const [errors, setErrors] = useState({});
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  useEffect(() => {
    if (initialData) {
      setForm({
        ...INITIAL_STATE,
        ...initialData,
        unitCost: initialData.unitCost?.toString() || ''
      });
      setIsEditing(true);
    }
  }, [initialData]);

  const handleChange = (field) => (e) => {
    setForm(prev => ({ ...prev, [field]: e.target.value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  const handleAddAttribute = () => {
    setForm(prev => ({
      ...prev,
      attributes: [...prev.attributes, { name: '', value: '', unit: '' }]
    }));
  };

  const handleAttributeChange = (index, field) => (e) => {
    setForm(prev => ({
      ...prev,
      attributes: prev.attributes.map((attr, i) =>
        i === index ? { ...attr, [field]: e.target.value } : attr
      )
    }));
  };

  const handleRemoveAttribute = (index) => {
    setForm(prev => ({
      ...prev,
      attributes: prev.attributes.filter((_, i) => i !== index)
    }));
  };

  const validate = () => {
    const newErrors = {};
    if (!form.name.trim()) newErrors.name = '材料名は必須です';
    if (!form.category) newErrors.category = 'カテゴリは必須です';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate()) return;

    const data = {
      ...form,
      unitCost: form.unitCost ? parseFloat(form.unitCost) : 0,
      attributes: form.attributes.filter(a => a.name.trim())
    };

    try {
      if (isEditing) {
        updateSubstrateType(form.id, data);
        setSnackbar({ open: true, message: '材料情報を更新しました', severity: 'success' });
      } else {
        saveSubstrateType(data);
        setSnackbar({ open: true, message: '材料を登録しました', severity: 'success' });
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

  return (
    <Box className="section-panel">
      <Typography className="section-panel__title">
        {isEditing ? '材料情報 編集' : '材料マスタ 新規登録'}
      </Typography>

      <form onSubmit={handleSubmit}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <FormControl fullWidth error={!!errors.category} size="small">
              <InputLabel>カテゴリ</InputLabel>
              <Select value={form.category} onChange={handleChange('category')} label="カテゴリ">
                {Object.entries(MATERIAL_CATEGORIES).map(([key, label]) => (
                  <MenuItem key={key} value={key}>{label}</MenuItem>
                ))}
              </Select>
              {errors.category && <FormHelperText>{errors.category}</FormHelperText>}
            </FormControl>
          </Grid>

          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth size="small" label="材料名"
              value={form.name} onChange={handleChange('name')}
              error={!!errors.name} helperText={errors.name}
            />
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth size="small" label="説明" multiline rows={2}
              value={form.description} onChange={handleChange('description')}
            />
          </Grid>

          <Grid item xs={12} sm={4}>
            <TextField
              fullWidth size="small" label="仕入先"
              value={form.supplier} onChange={handleChange('supplier')}
            />
          </Grid>

          <Grid item xs={12} sm={4}>
            <TextField
              fullWidth size="small" label="単価（円）" type="number"
              value={form.unitCost} onChange={handleChange('unitCost')}
              InputProps={{ inputProps: { min: 0, step: 0.01 } }}
              sx={{ '& input': { fontFamily: "'Fira Code', monospace" } }}
            />
          </Grid>

          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>単位</InputLabel>
              <Select value={form.unit} onChange={handleChange('unit')} label="単位">
                <MenuItem value="kg">kg</MenuItem>
                <MenuItem value="t">t</MenuItem>
                <MenuItem value="L">L</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>

        <Box sx={{ mt: 3, mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="subtitle2" sx={{ color: 'text.secondary' }}>
              属性情報
            </Typography>
            <Button size="small" startIcon={<AddIcon />} onClick={handleAddAttribute}>
              属性追加
            </Button>
          </Box>

          {form.attributes.map((attr, index) => (
            <Grid container spacing={1} key={index} sx={{ mb: 1 }}>
              <Grid item xs={4}>
                <TextField fullWidth size="small" placeholder="項目名"
                  value={attr.name} onChange={handleAttributeChange(index, 'name')} />
              </Grid>
              <Grid item xs={4}>
                <TextField fullWidth size="small" placeholder="値"
                  value={attr.value} onChange={handleAttributeChange(index, 'value')}
                  sx={{ '& input': { fontFamily: "'Fira Code', monospace" } }} />
              </Grid>
              <Grid item xs={3}>
                <TextField fullWidth size="small" placeholder="単位"
                  value={attr.unit} onChange={handleAttributeChange(index, 'unit')} />
              </Grid>
              <Grid item xs={1}>
                <IconButton size="small" onClick={() => handleRemoveAttribute(index)} color="error">
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Grid>
            </Grid>
          ))}
        </Box>

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

export default SubstrateTypeForm;
