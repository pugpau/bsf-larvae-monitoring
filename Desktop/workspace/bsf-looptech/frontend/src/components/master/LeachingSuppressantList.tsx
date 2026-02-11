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
  fetchLeachingSuppressants,
  createLeachingSuppressant,
  updateLeachingSuppressant,
  deleteLeachingSuppressant,
  exportLeachingSuppressantsCsv,
  importLeachingSuppressantsCsv,
  downloadBlob,
} from '../../api/materialsApi';
import type { LeachingSuppressant } from '../../types/api';

const SUPPRESSANT_TYPES = [
  { value: 'chelate', label: 'キレート系' },
  { value: 'sulfide', label: '硫化物系' },
  { value: 'phosphate', label: 'リン酸系' },
  { value: 'other', label: 'その他' },
];

const TYPE_LABELS: Record<string, string> = {
  chelate: 'キレート系',
  sulfide: '硫化物系',
  phosphate: 'リン酸系',
  other: 'その他',
};

const EMPTY_FORM = {
  name: '',
  suppressant_type: 'chelate',
  target_metals: '',
  min_addition_rate: '',
  max_addition_rate: '',
  ph_range_min: '',
  ph_range_max: '',
  unit_cost: '',
  notes: '',
};

const ROWS_PER_PAGE_OPTIONS = [25, 50, 100];

const LeachingSuppressantList: React.FC = () => {
  const [items, setItems] = useState<LeachingSuppressant[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [formOpen, setFormOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; target: LeachingSuppressant | null }>({
    open: false,
    target: null,
  });
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchLeachingSuppressants({
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
      const blob = await exportLeachingSuppressantsCsv();
      downloadBlob(blob, 'leaching_suppressants.csv');
      setSnackbar({ open: true, message: 'CSVをエクスポートしました', severity: 'success' });
    } catch {
      setSnackbar({ open: true, message: 'エクスポートに失敗しました', severity: 'error' });
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await importLeachingSuppressantsCsv(file);
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

  const handleOpenEdit = (item: LeachingSuppressant) => {
    setEditId(item.id);
    setForm({
      name: item.name,
      suppressant_type: item.suppressant_type,
      target_metals: (item.target_metals || []).join(', '),
      min_addition_rate: item.min_addition_rate?.toString() || '',
      max_addition_rate: item.max_addition_rate?.toString() || '',
      ph_range_min: item.ph_range_min?.toString() || '',
      ph_range_max: item.ph_range_max?.toString() || '',
      unit_cost: item.unit_cost?.toString() || '',
      notes: item.notes || '',
    });
    setFormOpen(true);
  };

  const handleSave = async () => {
    try {
      const payload = {
        name: form.name,
        suppressant_type: form.suppressant_type,
        target_metals: form.target_metals ? form.target_metals.split(',').map(s => s.trim()).filter(Boolean) : [],
        min_addition_rate: form.min_addition_rate ? parseFloat(form.min_addition_rate) : undefined,
        max_addition_rate: form.max_addition_rate ? parseFloat(form.max_addition_rate) : undefined,
        ph_range_min: form.ph_range_min ? parseFloat(form.ph_range_min) : undefined,
        ph_range_max: form.ph_range_max ? parseFloat(form.ph_range_max) : undefined,
        unit_cost: form.unit_cost ? parseFloat(form.unit_cost) : undefined,
        notes: form.notes || undefined,
      };
      if (editId) {
        await updateLeachingSuppressant(editId, payload);
        setSnackbar({ open: true, message: '更新しました', severity: 'success' });
      } else {
        await createLeachingSuppressant(payload);
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
      await deleteLeachingSuppressant(deleteDialog.target.id);
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
        <Typography variant="h2">溶出抑制剤マスタ</Typography>
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
              <TableCell>抑制剤名</TableCell>
              <TableCell>対象重金属</TableCell>
              <TableCell align="right">添加率範囲 (%)</TableCell>
              <TableCell align="right">pH範囲</TableCell>
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
                  {searchQuery ? '検索結果が見つかりません' : '溶出抑制剤が登録されていません'}
                </TableCell>
              </TableRow>
            ) : (
              items.map((item) => (
                <TableRow key={item.id} sx={{ cursor: 'pointer' }}>
                  <TableCell>
                    <Chip label={TYPE_LABELS[item.suppressant_type] || item.suppressant_type} size="small" color="warning" variant="outlined" />
                  </TableCell>
                  <TableCell sx={{ fontWeight: 500 }}>{item.name}</TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                      {(item.target_metals || []).map((m) => (
                        <Chip key={m} label={m} size="small" variant="outlined" color="error" />
                      ))}
                      {(!item.target_metals || item.target_metals.length === 0) && '-'}
                    </Stack>
                  </TableCell>
                  <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                    {item.min_addition_rate != null && item.max_addition_rate != null
                      ? `${item.min_addition_rate.toFixed(1)} - ${item.max_addition_rate.toFixed(1)}`
                      : '-'}
                  </TableCell>
                  <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                    {item.ph_range_min != null && item.ph_range_max != null
                      ? `${item.ph_range_min.toFixed(1)} - ${item.ph_range_max.toFixed(1)}`
                      : '-'}
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
        <DialogTitle>{editId ? '溶出抑制剤の編集' : '溶出抑制剤の新規登録'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="抑制剤名" value={form.name} onChange={handleFieldChange('name')} required fullWidth size="small" />
            <TextField label="種別" value={form.suppressant_type} onChange={handleFieldChange('suppressant_type')} select fullWidth size="small">
              {SUPPRESSANT_TYPES.map(t => (<MenuItem key={t.value} value={t.value}>{t.label}</MenuItem>))}
            </TextField>
            <TextField label="対象重金属（カンマ区切り）" value={form.target_metals} onChange={handleFieldChange('target_metals')} fullWidth size="small" placeholder="Pb, Cd, As, Hg" />
            <Stack direction="row" spacing={2}>
              <TextField label="最小添加率 (%)" value={form.min_addition_rate} onChange={handleFieldChange('min_addition_rate')} type="number" fullWidth size="small" />
              <TextField label="最大添加率 (%)" value={form.max_addition_rate} onChange={handleFieldChange('max_addition_rate')} type="number" fullWidth size="small" />
            </Stack>
            <Stack direction="row" spacing={2}>
              <TextField label="pH下限" value={form.ph_range_min} onChange={handleFieldChange('ph_range_min')} type="number" fullWidth size="small" />
              <TextField label="pH上限" value={form.ph_range_max} onChange={handleFieldChange('ph_range_max')} type="number" fullWidth size="small" />
            </Stack>
            <TextField label="単価 (円/kg)" value={form.unit_cost} onChange={handleFieldChange('unit_cost')} type="number" fullWidth size="small" />
            <TextField label="備考" value={form.notes} onChange={handleFieldChange('notes')} fullWidth size="small" multiline rows={2} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFormOpen(false)} startIcon={<CloseIcon />}>キャンセル</Button>
          <Button onClick={handleSave} variant="contained" startIcon={<CheckIcon />} disabled={!form.name || !form.suppressant_type}>
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

export default LeachingSuppressantList;
