import React, { useMemo } from 'react';
import {
  Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Button, Chip, Dialog, DialogActions, DialogContent,
  DialogTitle, TextField, Stack,
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Check as CheckIcon, Close as CloseIcon } from '@mui/icons-material';
import {
  fetchSuppliers, createSupplier, updateSupplier, deleteSupplier,
  exportSuppliersCsv, importSuppliersCsv,
} from '../../api/materialsApi';
import type { Supplier } from '../../types/api';
import { useCrudList } from '../../hooks/useCrudList';
import CrudListToolbar from '../common/CrudListToolbar';
import JaTablePagination from '../common/JaTablePagination';
import ConfirmDeleteDialog from '../common/ConfirmDeleteDialog';
import NotificationSnackbar from '../common/NotificationSnackbar';
import TableSkeleton from '../common/TableSkeleton';
import EmptyState from '../common/EmptyState';

const EMPTY_FORM = {
  name: '', contact_person: '', phone: '', email: '',
  address: '', waste_types: '', notes: '',
};

const api = {
  fetch: fetchSuppliers,
  create: createSupplier,
  update: updateSupplier,
  remove: deleteSupplier,
  exportCsv: exportSuppliersCsv,
  importCsv: importSuppliersCsv,
};

const SupplierList: React.FC = () => {
  const crud = useCrudList<Supplier, typeof EMPTY_FORM>(api, EMPTY_FORM);

  const openEdit = (item: Supplier) => {
    crud.handleOpenEdit(item.id, {
      name: item.name,
      contact_person: item.contact_person || '',
      phone: item.phone || '',
      email: item.email || '',
      address: item.address || '',
      waste_types: (item.waste_types || []).join(', '),
      notes: item.notes || '',
    });
  };

  const save = () => {
    const payload = {
      name: crud.form.name,
      contact_person: crud.form.contact_person || undefined,
      phone: crud.form.phone || undefined,
      email: crud.form.email || undefined,
      address: crud.form.address || undefined,
      waste_types: crud.form.waste_types ? crud.form.waste_types.split(',').map(s => s.trim()).filter(Boolean) : [],
      notes: crud.form.notes || undefined,
    };
    crud.handleSave(payload);
  };

  const colSpan = 6;
  const emptyMessage = useMemo(
    () => crud.searchQuery ? '検索結果が見つかりません' : '搬入先が登録されていません',
    [crud.searchQuery],
  );

  return (
    <Box>
      <CrudListToolbar
        title="搬入先マスタ"
        searchQuery={crud.searchQuery}
        onSearchChange={crud.handleSearchChange}
        onExport={() => crud.handleExport('suppliers.csv')}
        onImportClick={() => crud.fileInputRef.current?.click()}
        onNewClick={crud.handleOpenNew}
        fileInputRef={crud.fileInputRef}
        onFileChange={crud.handleImport}
      />

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
            {crud.loading ? (
              <TableSkeleton columns={colSpan} />
            ) : crud.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={colSpan}>
                  <EmptyState title={emptyMessage} />
                </TableCell>
              </TableRow>
            ) : (
              crud.items.map((item) => (
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
                    <Chip label={item.is_active ? '有効' : '無効'} size="small" color={item.is_active ? 'success' : 'default'} variant="outlined" />
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
        <JaTablePagination
          count={crud.total} page={crud.page}
          onPageChange={crud.handlePageChange} rowsPerPage={crud.rowsPerPage}
          onRowsPerPageChange={crud.handleRowsPerPageChange}
        />
      </TableContainer>

      <Dialog open={crud.formOpen} onClose={() => crud.setFormOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{crud.editId ? '搬入先の編集' : '搬入先の新規登録'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="搬入先名" value={crud.form.name} onChange={crud.handleFieldChange('name')} required fullWidth size="small" />
            <TextField label="担当者名" value={crud.form.contact_person} onChange={crud.handleFieldChange('contact_person')} fullWidth size="small" />
            <Stack direction="row" spacing={2}>
              <TextField label="電話番号" value={crud.form.phone} onChange={crud.handleFieldChange('phone')} fullWidth size="small" />
              <TextField label="メールアドレス" value={crud.form.email} onChange={crud.handleFieldChange('email')} fullWidth size="small" />
            </Stack>
            <TextField label="住所" value={crud.form.address} onChange={crud.handleFieldChange('address')} fullWidth size="small" />
            <TextField label="廃棄物種類（カンマ区切り）" value={crud.form.waste_types} onChange={crud.handleFieldChange('waste_types')} fullWidth size="small" placeholder="汚泥, 焼却灰, 飛灰" />
            <TextField label="備考" value={crud.form.notes} onChange={crud.handleFieldChange('notes')} fullWidth size="small" multiline rows={2} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => crud.setFormOpen(false)} startIcon={<CloseIcon />}>キャンセル</Button>
          <Button onClick={save} variant="contained" startIcon={<CheckIcon />} disabled={!crud.form.name}>
            {crud.editId ? '更新' : '登録'}
          </Button>
        </DialogActions>
      </Dialog>

      <ConfirmDeleteDialog
        open={crud.deleteDialogOpen}
        targetName={crud.deleteTarget?.name}
        onConfirm={crud.handleDeleteConfirm}
        onCancel={crud.handleDeleteCancel}
      />
      <NotificationSnackbar
        open={crud.notification.open}
        message={crud.notification.message}
        severity={crud.notification.severity}
        onClose={crud.closeNotification}
      />
    </Box>
  );
};

export default SupplierList;
