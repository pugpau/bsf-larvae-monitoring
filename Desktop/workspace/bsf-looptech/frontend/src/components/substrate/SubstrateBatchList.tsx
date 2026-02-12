import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Button, Chip, Dialog, DialogActions, DialogContent,
  DialogTitle, TablePagination, TextField, InputAdornment,
} from '@mui/material';
import {
  Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon,
  Visibility as ViewIcon, Search as SearchIcon,
  FileDownload as ExportIcon, FileUpload as ImportIcon,
} from '@mui/icons-material';
import { useNotification } from '../../hooks/useNotification';
import NotificationSnackbar from '../common/NotificationSnackbar';
import ConfirmDeleteDialog from '../common/ConfirmDeleteDialog';
import { fetchWasteRecords, deleteWasteRecord, exportWasteRecordsCsv, importWasteRecordsCsv } from '../../api/wasteApi';
import { downloadBlob } from '../../api/materialsApi';
import { ELUTION_THRESHOLDS } from '../../constants/waste';
import type { WasteRecord } from '../../types/api';

const STATUS_CONFIG: Record<string, { label: string; color: 'default' | 'info' | 'success' }> = {
  pending: { label: '未分析', color: 'default' },
  analyzed: { label: '分析済', color: 'info' },
  formulated: { label: '配合済', color: 'success' },
};

const ROWS_PER_PAGE_OPTIONS = [25, 50, 100];

interface SubstrateBatchListProps {
  onEdit: (record: WasteRecord | Record<string, never>) => void;
}

const SubstrateBatchList: React.FC<SubstrateBatchListProps> = ({ onEdit }) => {
  const [records, setRecords] = useState<WasteRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [deleteTarget, setDeleteTarget] = useState<WasteRecord | null>(null);
  const [detailDialog, setDetailDialog] = useState<{ open: boolean; record: WasteRecord | null }>({ open: false, record: null });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { notification, notify, closeNotification } = useNotification();

  const loadRecords = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchWasteRecords({
        q: searchQuery || undefined,
        limit: rowsPerPage,
        offset: page * rowsPerPage,
        sort_by: 'delivery_date',
        sort_order: 'desc',
      });
      setRecords(result.items);
      setTotal(result.total);
    } catch {
      notify('読み込みに失敗しました', 'error');
    } finally {
      setLoading(false);
    }
  }, [searchQuery, page, rowsPerPage, notify]);

  useEffect(() => { loadRecords(); }, [loadRecords]);

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    try {
      await deleteWasteRecord(deleteTarget.id);
      setDeleteTarget(null);
      notify('削除しました');
      loadRecords();
    } catch {
      notify('削除に失敗しました', 'error');
    }
  }, [deleteTarget, notify, loadRecords]);

  const handleExport = useCallback(async () => {
    try {
      const blob = await exportWasteRecordsCsv();
      downloadBlob(blob, 'waste_records.csv');
      notify('CSVをエクスポートしました');
    } catch {
      notify('エクスポートに失敗しました', 'error');
    }
  }, [notify]);

  const handleImport = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      notify('ファイルサイズが大きすぎます（最大10MB）', 'error');
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }
    try {
      const result = await importWasteRecordsCsv(file);
      const msg = `${result.imported}件インポート, ${result.skipped}件スキップ`;
      notify(msg, result.errors.length > 0 ? 'error' : 'success');
      loadRecords();
    } catch {
      notify('インポートに失敗しました', 'error');
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }, [notify, loadRecords]);

  const hasExceedance = (analysis?: Record<string, number | null>): boolean => {
    if (!analysis) return false;
    return Object.entries(ELUTION_THRESHOLDS).some(([key, threshold]) => {
      const val = analysis[key];
      return val !== undefined && val !== null && val > threshold.limit;
    });
  };

  return (
    <Box className="section-panel">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
        <Typography className="section-panel__title" sx={{ mb: '0 !important', pb: '0 !important', borderBottom: 'none !important' }}>
          搬入履歴
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <TextField
            size="small" placeholder="検索..." value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(0); }}
            InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> }}
            sx={{ width: 200 }}
          />
          <Button size="small" startIcon={<ExportIcon />} onClick={handleExport}>CSV出力</Button>
          <Button size="small" startIcon={<ImportIcon />} component="label">
            CSV入力
            <input ref={fileInputRef} type="file" accept=".csv" hidden onChange={handleImport} />
          </Button>
          <Button variant="contained" startIcon={<AddIcon />} size="small" onClick={() => onEdit({})}>
            新規登録
          </Button>
        </Box>
      </Box>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>搬入日</TableCell>
              <TableCell>搬入元</TableCell>
              <TableCell>廃棄物種別</TableCell>
              <TableCell align="right">重量</TableCell>
              <TableCell align="right">pH</TableCell>
              <TableCell align="right">含水率</TableCell>
              <TableCell>基準超過</TableCell>
              <TableCell>ステータス</TableCell>
              <TableCell align="center">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={9} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                  読み込み中...
                </TableCell>
              </TableRow>
            ) : records.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                  搬入記録がありません
                </TableCell>
              </TableRow>
            ) : (
              records.map((record) => {
                const exceeded = hasExceedance(record.analysis);
                const statusCfg = STATUS_CONFIG[record.status] || STATUS_CONFIG.pending;
                return (
                  <TableRow key={record.id} hover sx={{ cursor: 'pointer' }}>
                    <TableCell sx={{ fontFamily: "'Fira Code', monospace", whiteSpace: 'nowrap' }}>
                      {record.deliveryDate}
                    </TableCell>
                    <TableCell sx={{ fontWeight: 500 }}>{record.source}</TableCell>
                    <TableCell>{record.wasteType}</TableCell>
                    <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                      {record.weight} {record.weightUnit}
                    </TableCell>
                    <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                      {record.analysis?.pH ?? '-'}
                    </TableCell>
                    <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                      {record.analysis?.moisture ? `${record.analysis.moisture}%` : '-'}
                    </TableCell>
                    <TableCell>
                      {record.analysis && Object.keys(record.analysis).length > 0 ? (
                        exceeded ? (
                          <span className="status-fail">超過あり</span>
                        ) : (
                          <span className="status-pass">基準内</span>
                        )
                      ) : '-'}
                    </TableCell>
                    <TableCell>
                      <Chip label={statusCfg.label} size="small" color={statusCfg.color} variant="outlined" />
                    </TableCell>
                    <TableCell align="center" sx={{ whiteSpace: 'nowrap' }}>
                      <IconButton size="small" onClick={() => setDetailDialog({ open: true, record })} color="info" aria-label="詳細表示">
                        <ViewIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" onClick={() => onEdit(record)} color="primary" aria-label="編集">
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" onClick={() => setDeleteTarget(record)} color="error" aria-label="削除">
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
          component="div" count={total} page={page} rowsPerPage={rowsPerPage}
          onPageChange={(_, newPage) => setPage(newPage)}
          onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
          rowsPerPageOptions={ROWS_PER_PAGE_OPTIONS}
          labelRowsPerPage="表示件数:"
        />
      </TableContainer>

      {/* Detail Dialog */}
      <Dialog open={detailDialog.open} onClose={() => setDetailDialog({ open: false, record: null })} maxWidth="sm" fullWidth>
        <DialogTitle>搬入詳細</DialogTitle>
        <DialogContent>
          {detailDialog.record && (
            <Box>
              <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 1 }}>基本情報</Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, mb: 2 }}>
                <Typography variant="body2">搬入元: <strong>{detailDialog.record.source}</strong></Typography>
                <Typography variant="body2">搬入日: <strong style={{ fontFamily: "'Fira Code', monospace" }}>{detailDialog.record.deliveryDate}</strong></Typography>
                <Typography variant="body2">種別: <strong>{detailDialog.record.wasteType}</strong></Typography>
                <Typography variant="body2">重量: <strong style={{ fontFamily: "'Fira Code', monospace" }}>{detailDialog.record.weight} {detailDialog.record.weightUnit}</strong></Typography>
              </Box>

              {detailDialog.record.analysis && Object.keys(detailDialog.record.analysis).length > 0 && (
                <>
                  <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 1 }}>分析結果</Typography>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>項目</TableCell>
                        <TableCell align="right">測定値</TableCell>
                        <TableCell align="right">基準値</TableCell>
                        <TableCell>判定</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {detailDialog.record.analysis.pH != null && (
                        <TableRow>
                          <TableCell>pH</TableCell>
                          <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                            {detailDialog.record.analysis.pH}
                          </TableCell>
                          <TableCell align="right">-</TableCell>
                          <TableCell>-</TableCell>
                        </TableRow>
                      )}
                      {detailDialog.record.analysis.moisture != null && (
                        <TableRow>
                          <TableCell>含水率</TableCell>
                          <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                            {detailDialog.record.analysis.moisture}%
                          </TableCell>
                          <TableCell align="right">-</TableCell>
                          <TableCell>-</TableCell>
                        </TableRow>
                      )}
                      {Object.entries(ELUTION_THRESHOLDS).map(([key, threshold]) => {
                        const val = detailDialog.record?.analysis?.[key];
                        if (val === undefined || val === null) return null;
                        const exceeded = val > threshold.limit;
                        return (
                          <TableRow key={key}>
                            <TableCell>{threshold.name} ({key})</TableCell>
                            <TableCell align="right" sx={{
                              fontFamily: "'Fira Code', monospace",
                              fontWeight: exceeded ? 600 : 400,
                              color: exceeded ? '#DC2626' : 'inherit',
                            }}>
                              {val}
                            </TableCell>
                            <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                              {threshold.limit} {threshold.unit}
                            </TableCell>
                            <TableCell>
                              <span className={exceeded ? 'status-fail' : 'status-pass'}>
                                {exceeded ? '超過' : '合格'}
                              </span>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </>
              )}

              {detailDialog.record.formulation && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 1 }}>配合情報</Typography>
                  <Typography variant="body2" sx={{ fontFamily: "'Fira Code', monospace" }}>
                    固化剤: {(detailDialog.record.formulation as Record<string, unknown>).solidifierType as string} ({(detailDialog.record.formulation as Record<string, unknown>).solidifierAmount as number} {(detailDialog.record.formulation as Record<string, unknown>).solidifierUnit as string})
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: "'Fira Code', monospace" }}>
                    抑制材: {(detailDialog.record.formulation as Record<string, unknown>).suppressorType as string} ({(detailDialog.record.formulation as Record<string, unknown>).suppressorAmount as number} {(detailDialog.record.formulation as Record<string, unknown>).suppressorUnit as string})
                  </Typography>
                </Box>
              )}

              {detailDialog.record.notes && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" sx={{ color: 'text.secondary' }}>備考</Typography>
                  <Typography variant="body2">{detailDialog.record.notes}</Typography>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialog({ open: false, record: null })}>閉じる</Button>
        </DialogActions>
      </Dialog>

      <ConfirmDeleteDialog
        open={Boolean(deleteTarget)}
        targetName={deleteTarget ? `${deleteTarget.source} (${deleteTarget.deliveryDate})` : ''}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />

      <NotificationSnackbar open={notification.open} message={notification.message} severity={notification.severity} onClose={closeNotification} />
    </Box>
  );
};

export default SubstrateBatchList;
