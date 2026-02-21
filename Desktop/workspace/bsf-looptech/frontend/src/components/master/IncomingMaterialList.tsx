import React, { useState, useEffect, useMemo } from 'react';
import {
  Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Button, Chip, Dialog, DialogActions, DialogContent,
  DialogTitle, TextField, Stack, MenuItem,
  FormControl, InputLabel, Select,
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import {
  Edit as EditIcon, Delete as DeleteIcon,
  Check as CheckIcon, Close as CloseIcon,
} from '@mui/icons-material';
import {
  fetchIncomingMaterials, createIncomingMaterial, updateIncomingMaterial,
  deleteIncomingMaterial, exportIncomingMaterialsCsv, importIncomingMaterialsCsv,
} from '../../api/deliveryApi';
import { fetchSuppliers } from '../../api/materialsApi';
import type { IncomingMaterial, Supplier } from '../../types/api';
import { useCrudList } from '../../hooks/useCrudList';
import CrudListToolbar from '../common/CrudListToolbar';
import JaTablePagination from '../common/JaTablePagination';
import ConfirmDeleteDialog from '../common/ConfirmDeleteDialog';
import NotificationSnackbar from '../common/NotificationSnackbar';
import TableSkeleton from '../common/TableSkeleton';
import EmptyState from '../common/EmptyState';

const EMPTY_FORM = {
  supplier_id: '',
  material_category: '',
  name: '',
  description: '',
  default_weight_unit: 't',
  notes: '',
};

const api = {
  fetch: fetchIncomingMaterials,
  create: createIncomingMaterial,
  update: updateIncomingMaterial,
  remove: deleteIncomingMaterial,
  exportCsv: exportIncomingMaterialsCsv,
  importCsv: importIncomingMaterialsCsv,
};

const IncomingMaterialList: React.FC = () => {
  const crud = useCrudList<IncomingMaterial, typeof EMPTY_FORM>(api, EMPTY_FORM);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);

  useEffect(() => {
    fetchSuppliers({ limit: 500 }).then((res) => setSuppliers(res.items)).catch(() => {});
  }, []);

  const supplierMap = useMemo(() => {
    const map = new Map<string, string>();
    suppliers.forEach((s) => map.set(s.id, s.name));
    return map;
  }, [suppliers]);

  const openEdit = (item: IncomingMaterial) => {
    crud.handleOpenEdit(item.id, {
      supplier_id: item.supplier_id,
      material_category: item.material_category,
      name: item.name,
      description: item.description || '',
      default_weight_unit: item.default_weight_unit || 't',
      notes: item.notes || '',
    });
  };

  const save = () => {
    const payload = {
      supplier_id: crud.form.supplier_id,
      material_category: crud.form.material_category,
      name: crud.form.name,
      description: crud.form.description || undefined,
      default_weight_unit: crud.form.default_weight_unit || 't',
      notes: crud.form.notes || undefined,
      is_active: true,
    };
    crud.handleSave(payload);
  };

  const handleSelectChange = (field: string) => (e: SelectChangeEvent<string>) => {
    crud.handleFieldSet(field, e.target.value);
  };

  const colSpan = 7;
  const emptyMessage = useMemo(
    () => crud.searchQuery ? '検索結果が見つかりません' : '搬入物が登録されていません',
    [crud.searchQuery],
  );

  const canSave = crud.form.supplier_id && crud.form.material_category && crud.form.name;

  return (
    <Box>
      <CrudListToolbar
        title="搬入物マスタ"
        searchQuery={crud.searchQuery}
        onSearchChange={crud.handleSearchChange}
        onExport={() => crud.handleExport('incoming_materials.csv')}
        onImportClick={() => crud.fileInputRef.current?.click()}
        onNewClick={crud.handleOpenNew}
        fileInputRef={crud.fileInputRef}
        onFileChange={crud.handleImport}
      />

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>搬入先</TableCell>
              <TableCell>種類</TableCell>
              <TableCell>名称</TableCell>
              <TableCell>単位</TableCell>
              <TableCell>説明</TableCell>
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
                  <TableCell>{item.supplier_name || supplierMap.get(item.supplier_id) || '-'}</TableCell>
                  <TableCell>
                    <Chip label={item.material_category} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell sx={{ fontWeight: 500 }}>{item.name}</TableCell>
                  <TableCell sx={{ fontFamily: "'Fira Code', monospace", fontSize: '0.8rem' }}>
                    {item.default_weight_unit}
                  </TableCell>
                  <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.description || '-'}
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
                    <IconButton size="small" onClick={() => openEdit(item)} color="primary" aria-label="編集">
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton size="small" onClick={() => crud.handleDeleteClick(item)} color="error" aria-label="削除">
                      <DeleteIcon fontSize="small" />
                    </IconButton>
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
        <DialogTitle>{crud.editId ? '搬入物の編集' : '搬入物の新規登録'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <FormControl fullWidth size="small" required>
              <InputLabel>搬入先</InputLabel>
              <Select
                value={crud.form.supplier_id}
                onChange={handleSelectChange('supplier_id')}
                label="搬入先"
              >
                {suppliers.map((s) => (
                  <MenuItem key={s.id} value={s.id}>{s.name}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="種類（カテゴリ）"
              value={crud.form.material_category}
              onChange={crud.handleFieldChange('material_category')}
              required fullWidth size="small"
              placeholder="汚泥, 焼却灰, 飛灰 など"
            />
            <TextField
              label="名称"
              value={crud.form.name}
              onChange={crud.handleFieldChange('name')}
              required fullWidth size="small"
            />
            <TextField
              label="説明"
              value={crud.form.description}
              onChange={crud.handleFieldChange('description')}
              fullWidth size="small" multiline rows={2}
            />
            <Stack direction="row" spacing={2}>
              <TextField
                label="デフォルト単位"
                value={crud.form.default_weight_unit}
                onChange={crud.handleFieldChange('default_weight_unit')}
                fullWidth size="small"
                placeholder="t"
              />
            </Stack>
            <TextField
              label="備考"
              value={crud.form.notes}
              onChange={crud.handleFieldChange('notes')}
              fullWidth size="small" multiline rows={2}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => crud.setFormOpen(false)} startIcon={<CloseIcon />}>キャンセル</Button>
          <Button onClick={save} variant="contained" startIcon={<CheckIcon />} disabled={!canSave}>
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

export default IncomingMaterialList;
