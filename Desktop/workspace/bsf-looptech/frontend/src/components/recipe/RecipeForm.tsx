import React, { useState, useEffect } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Stack, MenuItem, Typography,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Snackbar, Alert, Divider,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Check as CheckIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import {
  createRecipe,
  updateRecipe,
  addRecipeDetail,
  removeRecipeDetail,
  fetchSolidificationMaterials,
  fetchLeachingSuppressants,
} from '../../api/materialsApi';
import type { Recipe, SolidificationMaterial, LeachingSuppressant } from '../../types/api';

interface RecipeFormProps {
  open: boolean;
  recipe: Recipe | null;
  onClose: (saved: boolean) => void;
}

const EMPTY_FORM = {
  name: '',
  waste_type: '',
  target_strength: '',
  status: 'draft',
  notes: '',
};

const EMPTY_DETAIL = {
  material_id: '',
  material_type: 'solidification' as string,
  addition_rate: '',
  notes: '',
};

const RecipeForm: React.FC<RecipeFormProps> = ({ open, recipe, onClose }) => {
  const [form, setForm] = useState(EMPTY_FORM);
  const [newDetail, setNewDetail] = useState(EMPTY_DETAIL);
  const [solidMaterials, setSolidMaterials] = useState<SolidificationMaterial[]>([]);
  const [suppressants, setSuppressants] = useState<LeachingSuppressant[]>([]);
  const [currentRecipe, setCurrentRecipe] = useState<Recipe | null>(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });

  useEffect(() => {
    if (recipe) {
      setForm({
        name: recipe.name,
        waste_type: recipe.waste_type,
        target_strength: recipe.target_strength?.toString() || '',
        status: recipe.status,
        notes: recipe.notes || '',
      });
      setCurrentRecipe(recipe);
    } else {
      setForm(EMPTY_FORM);
      setCurrentRecipe(null);
    }
  }, [recipe]);

  useEffect(() => {
    const loadMaterials = async () => {
      try {
        const [solids, supps] = await Promise.all([
          fetchSolidificationMaterials(),
          fetchLeachingSuppressants(),
        ]);
        setSolidMaterials(solids.items);
        setSuppressants(supps.items);
      } catch {
        // Materials will be empty — user can still type IDs
      }
    };
    if (open) loadMaterials();
  }, [open]);

  const handleFieldChange = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm(prev => ({ ...prev, [field]: e.target.value }));
  };

  const handleDetailChange = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setNewDetail(prev => ({ ...prev, [field]: e.target.value }));
  };

  const handleSave = async () => {
    try {
      const payload = {
        name: form.name,
        waste_type: form.waste_type,
        target_strength: form.target_strength ? parseFloat(form.target_strength) : undefined,
        status: form.status as Recipe['status'],
        notes: form.notes || undefined,
      };

      if (currentRecipe) {
        await updateRecipe(currentRecipe.id, payload);
        setSnackbar({ open: true, message: '更新しました', severity: 'success' });
      } else {
        const created = await createRecipe(payload);
        setCurrentRecipe(created);
        setSnackbar({ open: true, message: '登録しました', severity: 'success' });
      }
    } catch {
      setSnackbar({ open: true, message: '保存に失敗しました', severity: 'error' });
    }
  };

  const handleAddDetail = async () => {
    if (!currentRecipe || !newDetail.material_id || !newDetail.addition_rate) return;
    try {
      const updated = await addRecipeDetail(currentRecipe.id, {
        material_id: newDetail.material_id,
        material_type: newDetail.material_type,
        addition_rate: parseFloat(newDetail.addition_rate),
        notes: newDetail.notes || undefined,
      });
      setCurrentRecipe(updated);
      setNewDetail(EMPTY_DETAIL);
      setSnackbar({ open: true, message: '明細を追加しました', severity: 'success' });
    } catch {
      setSnackbar({ open: true, message: '明細の追加に失敗しました', severity: 'error' });
    }
  };

  const handleRemoveDetail = async (detailId: string) => {
    if (!currentRecipe) return;
    try {
      await removeRecipeDetail(currentRecipe.id, detailId);
      setCurrentRecipe(prev =>
        prev ? { ...prev, details: prev.details.filter(d => d.id !== detailId) } : null
      );
      setSnackbar({ open: true, message: '明細を削除しました', severity: 'success' });
    } catch {
      setSnackbar({ open: true, message: '明細の削除に失敗しました', severity: 'error' });
    }
  };

  const getMaterialName = (materialId: string, materialType: string): string => {
    if (materialType === 'solidification') {
      return solidMaterials.find(m => m.id === materialId)?.name || materialId.slice(0, 8);
    }
    if (materialType === 'suppressant') {
      return suppressants.find(m => m.id === materialId)?.name || materialId.slice(0, 8);
    }
    return materialId.slice(0, 8);
  };

  const materialOptions = newDetail.material_type === 'solidification'
    ? solidMaterials.map(m => ({ value: m.id, label: m.name }))
    : suppressants.map(m => ({ value: m.id, label: m.name }));

  return (
    <>
      <Dialog open={open} onClose={() => onClose(false)} maxWidth="md" fullWidth>
        <DialogTitle>{recipe ? 'レシピの編集' : 'レシピの新規作成'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="レシピ名"
              value={form.name}
              onChange={handleFieldChange('name')}
              required
              fullWidth
              size="small"
            />
            <Stack direction="row" spacing={2}>
              <TextField
                label="廃棄物種類"
                value={form.waste_type}
                onChange={handleFieldChange('waste_type')}
                required
                fullWidth
                size="small"
                placeholder="汚泥（一般）"
              />
              <TextField
                label="目標強度 (kN/m²)"
                value={form.target_strength}
                onChange={handleFieldChange('target_strength')}
                type="number"
                fullWidth
                size="small"
              />
            </Stack>
            <Stack direction="row" spacing={2}>
              <TextField
                label="ステータス"
                value={form.status}
                onChange={handleFieldChange('status')}
                select
                size="small"
                sx={{ minWidth: 160 }}
              >
                <MenuItem value="draft">下書き</MenuItem>
                <MenuItem value="active">有効</MenuItem>
                <MenuItem value="archived">アーカイブ</MenuItem>
              </TextField>
              <TextField
                label="備考"
                value={form.notes}
                onChange={handleFieldChange('notes')}
                fullWidth
                size="small"
              />
            </Stack>

            <Button
              onClick={handleSave}
              variant="outlined"
              size="small"
              sx={{ alignSelf: 'flex-start' }}
              disabled={!form.name || !form.waste_type}
            >
              {currentRecipe ? 'ヘッダ更新' : 'まず保存（明細追加可能に）'}
            </Button>

            {/* Recipe Details Section */}
            {currentRecipe && (
              <>
                <Divider sx={{ mt: 2 }} />
                <Typography variant="h3" sx={{ mt: 1 }}>配合明細</Typography>

                {currentRecipe.details && currentRecipe.details.length > 0 && (
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>材料種別</TableCell>
                          <TableCell>材料名</TableCell>
                          <TableCell align="right">添加率 (%)</TableCell>
                          <TableCell align="center">操作</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {currentRecipe.details.map((detail) => (
                          <TableRow key={detail.id}>
                            <TableCell>
                              {detail.material_type === 'solidification' ? '固化材' : '抑制剤'}
                            </TableCell>
                            <TableCell sx={{ fontWeight: 500 }}>
                              {getMaterialName(detail.material_id, detail.material_type)}
                            </TableCell>
                            <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                              {detail.addition_rate.toFixed(1)}
                            </TableCell>
                            <TableCell align="center">
                              <IconButton
                                size="small"
                                onClick={() => handleRemoveDetail(detail.id)}
                                color="error"
                                aria-label="明細削除"
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}

                {/* Add New Detail */}
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>明細追加</Typography>
                  <Stack direction="row" spacing={1} alignItems="flex-end">
                    <TextField
                      label="材料種別"
                      value={newDetail.material_type}
                      onChange={handleDetailChange('material_type')}
                      select
                      size="small"
                      sx={{ minWidth: 130 }}
                    >
                      <MenuItem value="solidification">固化材</MenuItem>
                      <MenuItem value="suppressant">抑制剤</MenuItem>
                    </TextField>
                    <TextField
                      label="材料"
                      value={newDetail.material_id}
                      onChange={handleDetailChange('material_id')}
                      select
                      size="small"
                      sx={{ minWidth: 200 }}
                    >
                      {materialOptions.map(m => (
                        <MenuItem key={m.value} value={m.value}>{m.label}</MenuItem>
                      ))}
                    </TextField>
                    <TextField
                      label="添加率 (%)"
                      value={newDetail.addition_rate}
                      onChange={handleDetailChange('addition_rate')}
                      type="number"
                      size="small"
                      sx={{ width: 120 }}
                    />
                    <Button
                      variant="contained"
                      size="small"
                      startIcon={<AddIcon />}
                      onClick={handleAddDetail}
                      disabled={!newDetail.material_id || !newDetail.addition_rate}
                    >
                      追加
                    </Button>
                  </Stack>
                </Paper>
              </>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => onClose(false)} startIcon={<CloseIcon />}>閉じる</Button>
          <Button onClick={() => onClose(true)} variant="contained" startIcon={<CheckIcon />}>
            完了
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={3000} onClose={() => setSnackbar(s => ({ ...s, open: false }))}>
        <Alert severity={snackbar.severity} variant="filled">{snackbar.message}</Alert>
      </Snackbar>
    </>
  );
};

export default RecipeForm;
