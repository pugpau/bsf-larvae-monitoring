import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Button, Chip, Dialog, DialogActions, DialogContent,
  DialogTitle, TextField, Snackbar, Alert, Stack, TablePagination, InputAdornment,
  Tooltip,
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
  fetchSuppliers,
  createSupplier,
  updateSupplier,
  deleteSupplier,
  exportSuppliersCsv,
  importSuppliersCsv,
  downloadBlob,
} from '../../api/materialsApi';
import type { Supplier } from '../../types/api';

const EMPTY_FORM = {
  name: '',
  contact_person: '',
  phone: '',
  email: '',
  address: '',
  waste_types: '',
  notes: '',
};

const ROWS_PER_PAGE_OPTIONS = [25, 50, 100];

const SupplierList: React.FC = () => {
  const [items, setItems] = useState<Supplier[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [formOpen, setFormOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; target: Supplier | null }>({
    open: false,
    target: null,
  });
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchSuppliers({
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
      const blob = await exportSuppliersCsv();
      downloadBlob(blob, 'suppliers.csv');
      setSnackbar({ open: true, message: 'CSVをエクスポートしました', severity: 'success' });
    } catch {
      setSnackbar({ open: true, message: 'エクスポートに失敗しました', severity: 'error' });
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await importSuppliersCsv(file);
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

  const handleOpenEdit = (item: Supplier) => {
    setEditId(item.id);
    setForm({
      name: item.name,
      contact_person: item.contact_person || '',
      phone: item.phone || '',
      email: item.email || '',
      address: item.address || '',
      waste_types: (item.waste_types || []).join(', '),
      notes: item.notes || '',
    });
    setFormOpen(true);
  };

  const handleSave = async () => {
    try {
      const payload = {
        name: form.name,
        contact_person: form.contact_person || undefined,
        phone: form.phone || undefined,
        email: form.email || undefined,
        address: form.address || undefined,
        waste_types: form.waste_types ? form.waste_types.split(',').map(s => s.trim()).filter(Boolean) : [],
        notes: form.notes || undefined,
      };
      if (editId) {
        await updateSupplier(editId, payload);
        setSnackbar({ open: true, message: '更新しました', severity: 'success' });
      } else {
        await createSupplier(payload);
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
      await deleteSupplier(deleteDialog.target.id);
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
        <Typography variant="h2">搬入先マスタ</Typography>
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
            <IconButton
              size="small"
              onClick={() => fileInputRef.current?.click()}
              color="primary"
              aria-label="CSVインポート"
            >
              <ImportIcon />
            </IconButton>
          </Tooltip>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            style={{ display: 'none' }}
            onChange={handleImport}
          />
          <Button variant="contained" startIcon={<AddIcon />} size="small" onClick={handleOpenNew}>
            新規登録
          </Button>
        </Stack>
      </Box>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>搬入先名</TableCell>
              <TableCell>担当者</TableCell>
              <TableCell>電話番号</TableCell>
              <TableCell>廃棄物種類</TableCell>
              <TableCell align="center">状態</TableCell>
              <TableCell align="center">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                  読み込み中...
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                  {searchQuery ? '検索結果が見つかりません' : '搬入先が登録されていません'}
                </TableCell>
              </TableRow>
            ) : (
              items.map((item) => (
                <TableRow key={item.id} sx={{ cursor: 'pointer' }}>
                  <TableCell sx={{ fontWeight: 500 }}>{item.name}</TableCell>
                  <TableCell>{item.contact_person || '-'}</TableCell>
                  <TableCell sx={{ fontFamily: "'Fira Code', monospace", fontSize: '0.8rem' }}>
                    {item.phone || '-'}
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                      {(item.waste_types || []).map((wt) => (
                        <Chip key={wt} label={wt} size="small" variant="outlined" />
                      ))}
                      {(!item.waste_types || item.waste_types.length === 0) && '-'}
                    </Stack>
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={item.is_active ? '有効' : '無効'}
                      size="small"
                      color={item.is_active ? 'success' : 'default'}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell align="center">
                    <IconButton size="small" onClick={() => handleOpenEdit(item)} color="primary" aria-label="編集">
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => setDeleteDialog({ open: true, target: item })}
                      color="error"
                      aria-label="削除"
                    >
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
        <DialogTitle>{editId ? '搬入先の編集' : '搬入先の新規登録'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="搬入先名" value={form.name} onChange={handleFieldChange('name')} required fullWidth size="small" />
            <TextField label="担当者名" value={form.contact_person} onChange={handleFieldChange('contact_person')} fullWidth size="small" />
            <Stack direction="row" spacing={2}>
              <TextField label="電話番号" value={form.phone} onChange={handleFieldChange('phone')} fullWidth size="small" />
              <TextField label="メールアドレス" value={form.email} onChange={handleFieldChange('email')} fullWidth size="small" />
            </Stack>
            <TextField label="住所" value={form.address} onChange={handleFieldChange('address')} fullWidth size="small" />
            <TextField label="廃棄物種類（カンマ区切り）" value={form.waste_types} onChange={handleFieldChange('waste_types')} fullWidth size="small" placeholder="汚泥, 焼却灰, 飛灰" />
            <TextField label="備考" value={form.notes} onChange={handleFieldChange('notes')} fullWidth size="small" multiline rows={2} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFormOpen(false)} startIcon={<CloseIcon />}>キャンセル</Button>
          <Button onClick={handleSave} variant="contained" startIcon={<CheckIcon />} disabled={!form.name}>
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

export default SupplierList;
