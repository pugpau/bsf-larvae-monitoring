import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Button, Chip, Dialog, DialogActions, DialogContent,
  DialogTitle, TextField, Snackbar, Alert, Stack, MenuItem, TablePagination,
  InputAdornment, Tooltip,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Check as CheckIcon,
  Close as CloseIcon,
  Search as SearchIcon,
  FileDownload as ExportIcon,
  FileUpload as ImportIcon,
} from '@mui/icons-material';
import {
  fetchSolidificationMaterials,
  createSolidificationMaterial,
  updateSolidificationMaterial,
  deleteSolidificationMaterial,
  exportSolidificationMaterialsCsv,
  importSolidificationMaterialsCsv,
  downloadBlob,
} from '../../api/materialsApi';
import type { SolidificationMaterial } from '../../types/api';

const MATERIAL_TYPES = [
  { value: 'cement', label: 'セメント系' },
  { value: 'calcium', label: '石灰系' },
  { value: 'ite', label: '石膏系' },
  { value: 'other', label: 'その他' },
];

const TYPE_LABELS: Record<string, string> = {
  cement: 'セメント系',
  calcium: '石灰系',
  ite: '石膏系',
  other: 'その他',
};

const EMPTY_FORM = {
  name: '',
  material_type: 'cement',
  base_material: '',
  min_addition_rate: '',
  max_addition_rate: '',
  unit_cost: '',
  notes: '',
};

const ROWS_PER_PAGE_OPTIONS = [25, 50, 100];

const SolidificationMaterialList: React.FC = () => {
  const [items, setItems] = useState<SolidificationMaterial[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [formOpen, setFormOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; target: SolidificationMaterial | null }>({
    open: false,
    target: null,
  });
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchSolidificationMaterials({
        q: searchQuery || undefined,
        limit: rowsPerPage,
        offset: page * rowsPerPage,
      });
      setItems(result.items);
      setTotal(result.total);
    } catch {
      setSnackbar({ open: true, message: 'データの読み込みに失敗しました', severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [searchQuery, page, rowsPerPage]);

  useEffect(() => { load(); }, [load]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setPage(0);
  };

  const handlePageChange = (_: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleRowsPerPageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(e.target.value, 10));
    setPage(0);
  };

  const handleExport = async () => {
    try {
      const blob = await exportSolidificationMaterialsCsv();
      downloadBlob(blob, 'solidification_materials.csv');
      setSnackbar({ open: true, message: 'CSVをエクスポートしました', severity: 'success' });
    } catch {
      setSnackbar({ open: true, message: 'エクスポートに失敗しました', severity: 'error' });
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await importSolidificationMaterialsCsv(file);
      const msg = `${result.imported}件インポート, ${result.skipped}件スキップ`;
      setSnackbar({ open: true, message: msg, severity: result.errors.length > 0 ? 'error' : 'success' });
      load();
    } catch {
      setSnackbar({ open: true, message: 'インポートに失敗しました', severity: 'error' });
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleOpenNew = () => {
    setEditId(null);
    setForm(EMPTY_FORM);
    setFormOpen(true);
  };

  const handleOpenEdit = (item: SolidificationMaterial) => {
    setEditId(item.id);
    setForm({
      name: item.name,
      material_type: item.material_type,
      base_material: item.base_material || '',
      min_addition_rate: item.min_addition_rate?.toString() || '',
      max_addition_rate: item.max_addition_rate?.toString() || '',
      unit_cost: item.unit_cost?.toString() || '',
      notes: item.notes || '',
    });
    setFormOpen(true);
  };

  const handleSave = async () => {
    try {
      const payload = {
        name: form.name,
        material_type: form.material_type as SolidificationMaterial['material_type'],
        base_material: form.base_material || undefined,
        min_addition_rate: form.min_addition_rate ? parseFloat(form.min_addition_rate) : undefined,
        max_addition_rate: form.max_addition_rate ? parseFloat(form.max_addition_rate) : undefined,
        unit_cost: form.unit_cost ? parseFloat(form.unit_cost) : undefined,
        notes: form.notes || undefined,
      };
      if (editId) {
        await updateSolidificationMaterial(editId, payload);
        setSnackbar({ open: true, message: '更新しました', severity: 'success' });
      } else {
        await createSolidificationMaterial(payload);
        setSnackbar({ open: true, message: '登録しました', severity: 'success' });
      }
      setFormOpen(false);
      load();
    } catch {
      setSnackbar({ open: true, message: '保存に失敗しました', severity: 'error' });
    }
  };

  const handleDelete = async () => {
    if (!deleteDialog.target) return;
    try {
      await deleteSolidificationMaterial(deleteDialog.target.id);
      setDeleteDialog({ open: false, target: null });
      setSnackbar({ open: true, message: '削除しました', severity: 'success' });
      load();
    } catch {
      setSnackbar({ open: true, message: '削除に失敗しました', severity: 'error' });
    }
  };

  const handleFieldChange = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm(prev => ({ ...prev, [field]: e.target.value }));
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h2">固化材マスタ</Typography>
        <Stack direction="row" spacing={1} alignItems="center">
          <TextField
            placeholder="検索..."
            value={searchQuery}
            onChange={handleSearchChange}
            size="small"
            sx={{ width: 220 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" color="action" />
                </InputAdornment>
              ),
            }}
          />
          <Tooltip title="CSVエクスポート">
            <IconButton size="small" onClick={handleExport} color="primary" aria-label="CSVエクスポート">
              <ExportIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="CSVインポート">
            <IconButton size="small" onClick={() => fileInputRef.current?.click()} color="primary" aria-label="CSVインポート">
              <ImportIcon />
            </IconButton>
          </Tooltip>
          <input ref={fileInputRef} type="file" accept=".csv" style={{ display: 'none' }} onChange={handleImport} />
          <Button variant="contained" startIcon={<AddIcon />} size="small" onClick={handleOpenNew}>
            新規登録
          </Button>
        </Stack>
      </Box>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>種別</TableCell>
              <TableCell>固化材名</TableCell>
              <TableCell>ベース材料</TableCell>
              <TableCell align="right">最小添加率 (%)</TableCell>
              <TableCell align="right">最大添加率 (%)</TableCell>
              <TableCell align="right">単価 (円/kg)</TableCell>
              <TableCell align="center">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                  読み込み中...
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                  {searchQuery ? '検索結果が見つかりません' : '固化材が登録されていません'}
                </TableCell>
              </TableRow>
            ) : (
              items.map((item) => (
                <TableRow key={item.id} sx={{ cursor: 'pointer' }}>
                  <TableCell>
                    <Chip label={TYPE_LABELS[item.material_type] || item.material_type} size="small" color="primary" variant="outlined" />
                  </TableCell>
                  <TableCell sx={{ fontWeight: 500 }}>{item.name}</TableCell>
                  <TableCell>{item.base_material || '-'}</TableCell>
                  <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                    {item.min_addition_rate != null ? item.min_addition_rate.toFixed(1) : '-'}
                  </TableCell>
                  <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                    {item.max_addition_rate != null ? item.max_addition_rate.toFixed(1) : '-'}
                  </TableCell>
                  <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                    {item.unit_cost != null ? item.unit_cost.toLocaleString() : '-'}
                  </TableCell>
                  <TableCell align="center">
                    <IconButton size="small" onClick={() => handleOpenEdit(item)} color="primary" aria-label="編集">
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton size="small" onClick={() => setDeleteDialog({ open: true, target: item })} color="error" aria-label="削除">
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={total}
          page={page}
          onPageChange={handlePageChange}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={handleRowsPerPageChange}
          rowsPerPageOptions={ROWS_PER_PAGE_OPTIONS}
          labelRowsPerPage="表示件数:"
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} / ${count}件`}
        />
      </TableContainer>

      {/* Create/Edit Dialog */}
      <Dialog open={formOpen} onClose={() => setFormOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editId ? '固化材の編集' : '固化材の新規登録'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="固化材名" value={form.name} onChange={handleFieldChange('name')} required fullWidth size="small" />
            <TextField label="種別" value={form.material_type} onChange={handleFieldChange('material_type')} select fullWidth size="small">
              {MATERIAL_TYPES.map(t => (<MenuItem key={t.value} value={t.value}>{t.label}</MenuItem>))}
            </TextField>
            <TextField label="ベース材料" value={form.base_material} onChange={handleFieldChange('base_material')} fullWidth size="small" placeholder="CaO-SiO2系" />
            <Stack direction="row" spacing={2}>
              <TextField label="最小添加率 (%)" value={form.min_addition_rate} onChange={handleFieldChange('min_addition_rate')} type="number" fullWidth size="small" />
              <TextField label="最大添加率 (%)" value={form.max_addition_rate} onChange={handleFieldChange('max_addition_rate')} type="number" fullWidth size="small" />
            </Stack>
            <TextField label="単価 (円/kg)" value={form.unit_cost} onChange={handleFieldChange('unit_cost')} type="number" fullWidth size="small" />
            <TextField label="備考" value={form.notes} onChange={handleFieldChange('notes')} fullWidth size="small" multiline rows={2} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFormOpen(false)} startIcon={<CloseIcon />}>キャンセル</Button>
          <Button onClick={handleSave} variant="contained" startIcon={<CheckIcon />} disabled={!form.name || !form.material_type}>
            {editId ? '更新' : '登録'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={deleteDialog.open} onClose={() => setDeleteDialog({ open: false, target: null })}>
        <DialogTitle>削除確認</DialogTitle>
        <DialogContent>
          <Typography>「{deleteDialog.target?.name}」を削除しますか？</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, target: null })}>キャンセル</Button>
          <Button onClick={handleDelete} color="error" variant="contained">削除</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={3000} onClose={() => setSnackbar(s => ({ ...s, open: false }))}>
        <Alert severity={snackbar.severity} variant="filled">{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default SolidificationMaterialList;
