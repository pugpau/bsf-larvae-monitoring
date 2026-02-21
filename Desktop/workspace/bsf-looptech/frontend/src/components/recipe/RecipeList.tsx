import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Button, Chip, Stack, TextField, MenuItem,
  InputAdornment, Tooltip,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Search as SearchIcon,
  FileDownload as ExportIcon,
  History as HistoryIcon,
} from '@mui/icons-material';
import { fetchRecipes, deleteRecipe, exportRecipesCsv, downloadBlob } from '../../api/materialsApi';
import type { Recipe } from '../../types/api';
import RecipeForm from './RecipeForm';
import RecipeVersionHistory from './RecipeVersionHistory';
import TableSkeleton from '../common/TableSkeleton';
import EmptyState from '../common/EmptyState';
import JaTablePagination from '../common/JaTablePagination';
import ConfirmDeleteDialog from '../common/ConfirmDeleteDialog';
import NotificationSnackbar from '../common/NotificationSnackbar';
import { useNotification } from '../../hooks/useNotification';
import { DATA_CELL_SX } from '../../styles/dataCell';

const STATUS_CONFIG: Record<string, { label: string; color: 'default' | 'primary' | 'success' | 'warning' }> = {
  draft: { label: '下書き', color: 'default' },
  active: { label: '有効', color: 'success' },
  archived: { label: 'アーカイブ', color: 'warning' },
};

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
  const [deleteTarget, setDeleteTarget] = useState<Recipe | null>(null);
  const { notification, notify, closeNotification } = useNotification();
  const [versionHistory, setVersionHistory] = useState<{ open: boolean; target: Recipe | null }>({
    open: false,
    target: null,
  });

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
      notify('データの読み込みに失敗しました', 'error');
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
      notify('CSVをエクスポートしました');
    } catch {
      notify('エクスポートに失敗しました', 'error');
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

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    try {
      await deleteRecipe(deleteTarget.id);
      setDeleteTarget(null);
      notify('削除しました');
      load();
    } catch {
      notify('削除に失敗しました', 'error');
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
              <TableCell align="center">Ver.</TableCell>
              <TableCell align="center">ステータス</TableCell>
              <TableCell align="center">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableSkeleton columns={7} />
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7}>
                  <EmptyState
                    title={searchQuery ? '検索結果が見つかりません' : 'レシピが登録されていません'}
                    description={searchQuery ? '検索条件を変更してください' : '「新規作成」からレシピを追加してください'}
                  />
                </TableCell>
              </TableRow>
            ) : (
              items.map((item) => {
                const statusCfg = STATUS_CONFIG[item.status] || STATUS_CONFIG.draft;
                return (
                  <TableRow key={item.id} sx={{ cursor: 'pointer' }}>
                    <TableCell sx={{ fontWeight: 500 }}>{item.name}</TableCell>
                    <TableCell>{item.waste_type}</TableCell>
                    <TableCell align="right" sx={DATA_CELL_SX}>
                      {item.target_strength != null ? `${item.target_strength.toLocaleString()} kN/m²` : '-'}
                    </TableCell>
                    <TableCell align="center">
                      <Chip label={`${item.details?.length || 0} 材料`} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell align="center">
                      <Chip
                        label={`v${item.current_version || 1}`}
                        size="small"
                        variant="outlined"
                        color="info"
                        sx={{ ...DATA_CELL_SX, fontSize: '0.75rem' }}
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Chip label={statusCfg.label} size="small" color={statusCfg.color} variant="outlined" />
                    </TableCell>
                    <TableCell align="center">
                      <Tooltip title="バージョン履歴">
                        <IconButton size="small" onClick={() => setVersionHistory({ open: true, target: item })} color="info" aria-label="バージョン履歴">
                          <HistoryIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <IconButton size="small" onClick={() => handleOpenEdit(item)} color="primary" aria-label="編集">
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" onClick={() => setDeleteTarget(item)} color="error" aria-label="削除">
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
        <JaTablePagination
          count={total}
          page={page}
          onPageChange={handlePageChange}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={handleRowsPerPageChange}
        />
      </TableContainer>

      {/* Recipe Form Dialog */}
      {formOpen && (
        <RecipeForm open={formOpen} recipe={editTarget} onClose={handleFormClose} />
      )}

      {/* Delete Confirmation */}
      <ConfirmDeleteDialog
        open={deleteTarget !== null}
        targetName={deleteTarget?.name}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTarget(null)}
      />

      {/* Version History Dialog */}
      {versionHistory.open && versionHistory.target && (
        <RecipeVersionHistory
          open={versionHistory.open}
          recipeId={versionHistory.target.id}
          recipeName={versionHistory.target.name}
          currentVersion={versionHistory.target.current_version || 1}
          onClose={(changed) => {
            setVersionHistory({ open: false, target: null });
            if (changed) load();
          }}
        />
      )}

      <NotificationSnackbar
        open={notification.open}
        message={notification.message}
        severity={notification.severity}
        onClose={closeNotification}
      />
    </Box>
  );
};

export default RecipeList;
