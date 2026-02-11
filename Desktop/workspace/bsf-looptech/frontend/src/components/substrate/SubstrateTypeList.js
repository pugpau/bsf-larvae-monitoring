import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Button, Chip, Dialog, DialogActions, DialogContent,
  DialogTitle, Snackbar, Alert
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';
import { getSubstrateTypes, deleteSubstrateType, getCategoryLabel } from '../../utils/storage';

const CATEGORY_COLORS = {
  solidifier: 'primary',
  suppressor: 'warning',
  waste_type: 'default'
};

const SubstrateTypeList = ({ onEdit }) => {
  const [types, setTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteDialog, setDeleteDialog] = useState({ open: false, target: null });
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  const loadTypes = () => {
    setLoading(true);
    try {
      const data = getSubstrateTypes();
      setTypes(data);
    } catch (err) {
      setSnackbar({ open: true, message: 'データの読み込みに失敗しました', severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadTypes(); }, []);

  const handleDelete = () => {
    if (!deleteDialog.target) return;
    try {
      deleteSubstrateType(deleteDialog.target.id);
      setDeleteDialog({ open: false, target: null });
      setSnackbar({ open: true, message: '削除しました', severity: 'success' });
      loadTypes();
    } catch (err) {
      setSnackbar({ open: true, message: '削除に失敗しました', severity: 'error' });
    }
  };

  const handleNewType = () => {
    if (onEdit) onEdit(null);
  };

  return (
    <Box className="section-panel">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography className="section-panel__title" sx={{ mb: '0 !important', pb: '0 !important', borderBottom: 'none !important' }}>
          材料マスタ一覧
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} size="small" onClick={handleNewType}>
          新規登録
        </Button>
      </Box>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>カテゴリ</TableCell>
              <TableCell>材料名</TableCell>
              <TableCell>仕入先</TableCell>
              <TableCell align="right">単価（円）</TableCell>
              <TableCell>単位</TableCell>
              <TableCell>説明</TableCell>
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
            ) : types.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                  材料が登録されていません
                </TableCell>
              </TableRow>
            ) : (
              types.map((type) => (
                <TableRow key={type.id}>
                  <TableCell>
                    <Chip
                      label={getCategoryLabel(type.category || type.type)}
                      size="small"
                      color={CATEGORY_COLORS[type.category || type.type] || 'default'}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell sx={{ fontWeight: 500 }}>{type.name}</TableCell>
                  <TableCell>{type.supplier || '-'}</TableCell>
                  <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                    {type.unitCost ? type.unitCost.toLocaleString() : '-'}
                  </TableCell>
                  <TableCell>{type.unit || '-'}</TableCell>
                  <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {type.description || '-'}
                  </TableCell>
                  <TableCell align="center">
                    <IconButton size="small" onClick={() => onEdit(type)} color="primary" aria-label="編集">
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton size="small" onClick={() => setDeleteDialog({ open: true, target: type })} color="error" aria-label="削除">
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

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

      <Snackbar open={snackbar.open} autoHideDuration={3000}
        onClose={() => setSnackbar(s => ({ ...s, open: false }))}>
        <Alert severity={snackbar.severity} variant="filled">{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default SubstrateTypeList;
