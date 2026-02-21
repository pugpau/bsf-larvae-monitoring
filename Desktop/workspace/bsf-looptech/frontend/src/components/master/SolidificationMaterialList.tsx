import React, { useMemo } from 'react';
import {
  Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Button, Chip, Dialog, DialogActions, DialogContent,
  DialogTitle, TextField, Stack, MenuItem,
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Check as CheckIcon, Close as CloseIcon } from '@mui/icons-material';
import {
  fetchSolidificationMaterials, createSolidificationMaterial, updateSolidificationMaterial,
  deleteSolidificationMaterial, exportSolidificationMaterialsCsv, importSolidificationMaterialsCsv,
} from '../../api/materialsApi';
import type { SolidificationMaterial } from '../../types/api';
import { useCrudList } from '../../hooks/useCrudList';
import CrudListToolbar from '../common/CrudListToolbar';
import JaTablePagination from '../common/JaTablePagination';
import ConfirmDeleteDialog from '../common/ConfirmDeleteDialog';
import NotificationSnackbar from '../common/NotificationSnackbar';
import TableSkeleton from '../common/TableSkeleton';
import EmptyState from '../common/EmptyState';

const MATERIAL_TYPES = [
  { value: 'cement', label: 'セメント系' },
  { value: 'calcium', label: '石灰系' },
  { value: 'ite', label: '石膏系' },
  { value: 'other', label: 'その他' },
];

const TYPE_LABELS: Record<string, string> = {
  cement: 'セメント系', calcium: '石灰系', ite: '石膏系', other: 'その他',
};

const EMPTY_FORM = {
  name: '', material_type: 'cement', base_material: '',
  min_addition_rate: '', max_addition_rate: '', unit_cost: '', notes: '',
};

const api = {
  fetch: fetchSolidificationMaterials,
  create: createSolidificationMaterial,
  update: updateSolidificationMaterial,
  remove: deleteSolidificationMaterial,
  exportCsv: exportSolidificationMaterialsCsv,
  importCsv: importSolidificationMaterialsCsv,
};

const SolidificationMaterialList: React.FC = () => {
  const crud = useCrudList<SolidificationMaterial, typeof EMPTY_FORM>(api, EMPTY_FORM);

  const openEdit = (item: SolidificationMaterial) => {
    crud.handleOpenEdit(item.id, {
      name: item.name,
      material_type: item.material_type,
      base_material: item.base_material || '',
      min_addition_rate: item.min_addition_rate?.toString() || '',
      max_addition_rate: item.max_addition_rate?.toString() || '',
      unit_cost: item.unit_cost?.toString() || '',
      notes: item.notes || '',
    });
  };

  const save = () => {
    const payload = {
      name: crud.form.name,
      material_type: crud.form.material_type as SolidificationMaterial['material_type'],
      base_material: crud.form.base_material || undefined,
      min_addition_rate: crud.form.min_addition_rate ? parseFloat(crud.form.min_addition_rate) : undefined,
      max_addition_rate: crud.form.max_addition_rate ? parseFloat(crud.form.max_addition_rate) : undefined,
      unit_cost: crud.form.unit_cost ? parseFloat(crud.form.unit_cost) : undefined,
      notes: crud.form.notes || undefined,
    };
    crud.handleSave(payload);
  };

  const colSpan = 7;
  const emptyMessage = useMemo(
    () => crud.searchQuery ? '検索結果が見つかりません' : '固化材が登録されていません',
    [crud.searchQuery],
  );

  return (
    <Box>
      <CrudListToolbar
        title="固化材マスタ"
        searchQuery={crud.searchQuery}
        onSearchChange={crud.handleSearchChange}
        onExport={() => crud.handleExport('solidification_materials.csv')}
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
              <TableCell>固化材名</TableCell>
              <TableCell>ベース材料</TableCell>
              <TableCell align="right">最小添加率 (%)</TableCell>
              <TableCell align="right">最大添加率 (%)</TableCell>
              <TableCell align="right">単価 (円/kg)</TableCell>
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
        <DialogTitle>{crud.editId ? '固化材の編集' : '固化材の新規登録'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="固化材名" value={crud.form.name} onChange={crud.handleFieldChange('name')} required fullWidth size="small" />
            <TextField label="種別" value={crud.form.material_type} onChange={crud.handleFieldChange('material_type')} select fullWidth size="small">
              {MATERIAL_TYPES.map(t => (<MenuItem key={t.value} value={t.value}>{t.label}</MenuItem>))}
            </TextField>
            <TextField label="ベース材料" value={crud.form.base_material} onChange={crud.handleFieldChange('base_material')} fullWidth size="small" placeholder="CaO-SiO2系" />
            <Stack direction="row" spacing={2}>
              <TextField label="最小添加率 (%)" value={crud.form.min_addition_rate} onChange={crud.handleFieldChange('min_addition_rate')} type="number" fullWidth size="small" />
              <TextField label="最大添加率 (%)" value={crud.form.max_addition_rate} onChange={crud.handleFieldChange('max_addition_rate')} type="number" fullWidth size="small" />
            </Stack>
            <TextField label="単価 (円/kg)" value={crud.form.unit_cost} onChange={crud.handleFieldChange('unit_cost')} type="number" fullWidth size="small" />
            <TextField label="備考" value={crud.form.notes} onChange={crud.handleFieldChange('notes')} fullWidth size="small" multiline rows={2} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => crud.setFormOpen(false)} startIcon={<CloseIcon />}>キャンセル</Button>
          <Button onClick={save} variant="contained" startIcon={<CheckIcon />} disabled={!crud.form.name || !crud.form.material_type}>
            {crud.editId ? '更新' : '登録'}
          </Button>
        </DialogActions>
      </Dialog>

      <ConfirmDeleteDialog open={crud.deleteDialogOpen} targetName={crud.deleteTarget?.name} onConfirm={crud.handleDeleteConfirm} onCancel={crud.handleDeleteCancel} />
      <NotificationSnackbar open={crud.notification.open} message={crud.notification.message} severity={crud.notification.severity} onClose={crud.closeNotification} />
    </Box>
  );
};

export default SolidificationMaterialList;
