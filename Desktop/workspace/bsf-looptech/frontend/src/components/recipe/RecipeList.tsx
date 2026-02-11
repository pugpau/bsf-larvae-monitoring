import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Button, Chip, Dialog, DialogActions, DialogContent,
  DialogTitle, Snackbar, Alert, Stack, TextField, MenuItem, TablePagination,
  InputAdornment, Tooltip,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Search as SearchIcon,
  FileDownload as ExportIcon,
} from '@mui/icons-material';
import { fetchRecipes, deleteRecipe, exportRecipesCsv, downloadBlob } from '../../api/materialsApi';
import type { Recipe } from '../../types/api';
import RecipeForm from './RecipeForm';

const STATUS_CONFIG: Record<string, { label: string; color: 'default' | 'primary' | 'success' | 'warning' }> = {
  draft: { label: '下書き', color: 'default' },
  active: { label: '有効', color: 'success' },
  archived: { label: 'アーカイブ', color: 'warning' },
};

const ROWS_PER_PAGE_OPTIONS = [25, 50, 100];

const RecipeList: React.FC = () => {
  const [items, setItems] = useState<Recipe[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [formOpen, setFormOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Recipe | null>(null);
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; target: Recipe | null }>({
    open: false,
    target: null,
  });
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchRecipes({
        q: searchQuery || undefined,
        status: statusFilter || undefined,
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
  }, [searchQuery, statusFilter, page, rowsPerPage]);

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
      const blob = await exportRecipesCsv();
      downloadBlob(blob, 'recipes.csv');
      setSnackbar({ open: true, message: 'CSVをエクスポートしました', severity: 'success' });
    } catch {
      setSnackbar({ open: true, message: 'エクスポートに失敗しました', severity: 'error' });
    }
  };

  const handleOpenNew = () => {
    setEditTarget(null);
    setFormOpen(true);
  };

  const handleOpenEdit = (item: Recipe) => {
    setEditTarget(item);
    setFormOpen(true);
  };

  const handleFormClose = (saved: boolean) => {
    setFormOpen(false);
    setEditTarget(null);
    if (saved) load();
  };

  const handleDelete = async () => {
    if (!deleteDialog.target) return;
    try {
      await deleteRecipe(deleteDialog.target.id);
      setDeleteDialog({ open: false, target: null });
      setSnackbar({ open: true, message: '削除しました', severity: 'success' });
      load();
    } catch {
      setSnackbar({ open: true, message: '削除に失敗しました', severity: 'error' });
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h2">配合レシピ一覧</Typography>
        <Stack direction="row" spacing={1} alignItems="center">
          <TextField
            placeholder="検索..."
            value={searchQuery}
            onChange={handleSearchChange}
            size="small"
            sx={{ width: 200 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" color="action" />
                </InputAdornment>
              ),
            }}
          />
          <TextField
            label="ステータス"
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
            select
            size="small"
            sx={{ minWidth: 140 }}
          >
            <MenuItem value="">すべて</MenuItem>
            <MenuItem value="draft">下書き</MenuItem>
            <MenuItem value="active">有効</MenuItem>
            <MenuItem value="archived">アーカイブ</MenuItem>
          </TextField>
          <Tooltip title="CSVエクスポート">
            <IconButton size="small" onClick={handleExport} color="primary" aria-label="CSVエクスポート">
              <ExportIcon />
            </IconButton>
          </Tooltip>
          <Button variant="contained" startIcon={<AddIcon />} size="small" onClick={handleOpenNew}>
            新規作成
          </Button>
        </Stack>
      </Box>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>レシピ名</TableCell>
              <TableCell>廃棄物種類</TableCell>
              <TableCell align="right">目標強度</TableCell>
              <TableCell align="center">明細数</TableCell>
              <TableCell align="center">ステータス</TableCell>
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
                  {searchQuery ? '検索結果が見つかりません' : 'レシピが登録されていません'}
                </TableCell>
              </TableRow>
            ) : (
              items.map((item) => {
                const statusCfg = STATUS_CONFIG[item.status] || STATUS_CONFIG.draft;
                return (
                  <TableRow key={item.id} sx={{ cursor: 'pointer' }}>
                    <TableCell sx={{ fontWeight: 500 }}>{item.name}</TableCell>
                    <TableCell>{item.waste_type}</TableCell>
                    <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                      {item.target_strength != null ? `${item.target_strength.toLocaleString()} kN/m²` : '-'}
                    </TableCell>
                    <TableCell align="center">
                      <Chip label={`${item.details?.length || 0} 材料`} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell align="center">
                      <Chip label={statusCfg.label} size="small" color={statusCfg.color} variant="outlined" />
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
                );
              })
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

      {/* Recipe Form Dialog */}
      {formOpen && (
        <RecipeForm open={formOpen} recipe={editTarget} onClose={handleFormClose} />
      )}

      {/* Delete Confirmation */}
      <Dialog open={deleteDialog.open} onClose={() => setDeleteDialog({ open: false, target: null })}>
        <DialogTitle>削除確認</DialogTitle>
        <DialogContent>
          <Typography>「{deleteDialog.target?.name}」を削除しますか？</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            配合明細もすべて削除されます。
          </Typography>
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

export default RecipeList;
