import React, { useMemo } from 'react';
import {
  Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Button, Chip, Dialog, DialogActions, DialogContent,
  DialogTitle, TextField, Stack, MenuItem, TablePagination,
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Check as CheckIcon, Close as CloseIcon } from '@mui/icons-material';
import {
  fetchLeachingSuppressants, createLeachingSuppressant, updateLeachingSuppressant,
  deleteLeachingSuppressant, exportLeachingSuppressantsCsv, importLeachingSuppressantsCsv,
} from '../../api/materialsApi';
import type { LeachingSuppressant } from '../../types/api';
import { useCrudList, ROWS_PER_PAGE_OPTIONS } from '../../hooks/useCrudList';
import CrudListToolbar from '../common/CrudListToolbar';
import ConfirmDeleteDialog from '../common/ConfirmDeleteDialog';
import NotificationSnackbar from '../common/NotificationSnackbar';

const SUPPRESSANT_TYPES = [
  { value: 'chelate', label: 'キレート系' },
  { value: 'sulfide', label: '硫化物系' },
  { value: 'phosphate', label: 'リン酸系' },
  { value: 'other', label: 'その他' },
];

const TYPE_LABELS: Record<string, string> = {
  chelate: 'キレート系', sulfide: '硫化物系', phosphate: 'リン酸系', other: 'その他',
};

const EMPTY_FORM = {
  name: '', suppressant_type: 'chelate', target_metals: '',
  min_addition_rate: '', max_addition_rate: '', ph_range_min: '',
  ph_range_max: '', unit_cost: '', notes: '',
};

const api = {
  fetch: fetchLeachingSuppressants,
  create: createLeachingSuppressant,
  update: updateLeachingSuppressant,
  remove: deleteLeachingSuppressant,
  exportCsv: exportLeachingSuppressantsCsv,
  importCsv: importLeachingSuppressantsCsv,
};

const LeachingSuppressantList: React.FC = () => {
  const crud = useCrudList<LeachingSuppressant, typeof EMPTY_FORM>(api, EMPTY_FORM);

  const openEdit = (item: LeachingSuppressant) => {
    crud.handleOpenEdit(item.id, {
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
  };

  const save = () => {
    const payload = {
      name: crud.form.name,
      suppressant_type: crud.form.suppressant_type,
      target_metals: crud.form.target_metals ? crud.form.target_metals.split(',').map(s => s.trim()).filter(Boolean) : [],
      min_addition_rate: crud.form.min_addition_rate ? parseFloat(crud.form.min_addition_rate) : undefined,
      max_addition_rate: crud.form.max_addition_rate ? parseFloat(crud.form.max_addition_rate) : undefined,
      ph_range_min: crud.form.ph_range_min ? parseFloat(crud.form.ph_range_min) : undefined,
      ph_range_max: crud.form.ph_range_max ? parseFloat(crud.form.ph_range_max) : undefined,
      unit_cost: crud.form.unit_cost ? parseFloat(crud.form.unit_cost) : undefined,
      notes: crud.form.notes || undefined,
    };
    crud.handleSave(payload);
  };

  const colSpan = 7;
  const emptyMessage = useMemo(
    () => crud.searchQuery ? '検索結果が見つかりません' : '溶出抑制剤が登録されていません',
    [crud.searchQuery],
  );

  return (
    <Box>
      <CrudListToolbar
        title="溶出抑制剤マスタ"
        searchQuery={crud.searchQuery}
        onSearchChange={crud.handleSearchChange}
        onExport={() => crud.handleExport('leaching_suppressants.csv')}
        onImportClick={() => crud.fileInputRef.current?.click()}
        onNewClick={crud.handleOpenNew}
        fileInputRef={crud.fileInputRef}
        onFileChange={crud.handleImport}
      />

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
            {crud.loading ? (
              <TableRow>
                <TableCell colSpan={colSpan} align="center" sx={{ py: 4, color: 'text.secondary' }}>読み込み中...</TableCell>
              </TableRow>
            ) : crud.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={colSpan} align="center" sx={{ py: 4, color: 'text.secondary' }}>{emptyMessage}</TableCell>
              </TableRow>
            ) : (
              crud.items.map((item) => (
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
                      ? `${item.min_addition_rate.toFixed(1)} - ${item.max_addition_rate.toFixed(1)}` : '-'}
                  </TableCell>
                  <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                    {item.ph_range_min != null && item.ph_range_max != null
                      ? `${item.ph_range_min.toFixed(1)} - ${item.ph_range_max.toFixed(1)}` : '-'}
                  </TableCell>
                  <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                    {item.unit_cost != null ? item.unit_cost.toLocaleString() : '-'}
                  </TableCell>
                  <TableCell align="center">
                    <IconButton size="small" onClick={() => openEdit(item)} color="primary" aria-label="編集"><EditIcon fontSize="small" /></IconButton>
                    <IconButton size="small" onClick={() => crud.handleDeleteClick(item)} color="error" aria-label="削除"><DeleteIcon fontSize="small" /></IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <TablePagination
          component="div" count={crud.total} page={crud.page}
          onPageChange={crud.handlePageChange} rowsPerPage={crud.rowsPerPage}
          onRowsPerPageChange={crud.handleRowsPerPageChange}
          rowsPerPageOptions={ROWS_PER_PAGE_OPTIONS}
          labelRowsPerPage="表示件数:"
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} / ${count}件`}
        />
      </TableContainer>

      <Dialog open={crud.formOpen} onClose={() => crud.setFormOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{crud.editId ? '溶出抑制剤の編集' : '溶出抑制剤の新規登録'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="抑制剤名" value={crud.form.name} onChange={crud.handleFieldChange('name')} required fullWidth size="small" />
            <TextField label="種別" value={crud.form.suppressant_type} onChange={crud.handleFieldChange('suppressant_type')} select fullWidth size="small">
              {SUPPRESSANT_TYPES.map(t => (<MenuItem key={t.value} value={t.value}>{t.label}</MenuItem>))}
            </TextField>
            <TextField label="対象重金属（カンマ区切り）" value={crud.form.target_metals} onChange={crud.handleFieldChange('target_metals')} fullWidth size="small" placeholder="Pb, Cd, As, Hg" />
            <Stack direction="row" spacing={2}>
              <TextField label="最小添加率 (%)" value={crud.form.min_addition_rate} onChange={crud.handleFieldChange('min_addition_rate')} type="number" fullWidth size="small" />
              <TextField label="最大添加率 (%)" value={crud.form.max_addition_rate} onChange={crud.handleFieldChange('max_addition_rate')} type="number" fullWidth size="small" />
            </Stack>
            <Stack direction="row" spacing={2}>
              <TextField label="pH下限" value={crud.form.ph_range_min} onChange={crud.handleFieldChange('ph_range_min')} type="number" fullWidth size="small" />
              <TextField label="pH上限" value={crud.form.ph_range_max} onChange={crud.handleFieldChange('ph_range_max')} type="number" fullWidth size="small" />
            </Stack>
            <TextField label="単価 (円/kg)" value={crud.form.unit_cost} onChange={crud.handleFieldChange('unit_cost')} type="number" fullWidth size="small" />
            <TextField label="備考" value={crud.form.notes} onChange={crud.handleFieldChange('notes')} fullWidth size="small" multiline rows={2} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => crud.setFormOpen(false)} startIcon={<CloseIcon />}>キャンセル</Button>
          <Button onClick={save} variant="contained" startIcon={<CheckIcon />} disabled={!crud.form.name || !crud.form.suppressant_type}>
            {crud.editId ? '更新' : '登録'}
          </Button>
        </DialogActions>
      </Dialog>

      <ConfirmDeleteDialog open={crud.deleteDialogOpen} targetName={crud.deleteTarget?.name} onConfirm={crud.handleDeleteConfirm} onCancel={crud.handleDeleteCancel} />
      <NotificationSnackbar open={crud.notification.open} message={crud.notification.message} severity={crud.notification.severity} onClose={crud.closeNotification} />
    </Box>
  );
};

export default LeachingSuppressantList;
