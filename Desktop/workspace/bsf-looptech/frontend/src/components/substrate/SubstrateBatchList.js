import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Button, Chip, Dialog, DialogActions, DialogContent,
  DialogTitle, Snackbar, Alert
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon, Visibility as ViewIcon } from '@mui/icons-material';
import { getSubstrateBatches, deleteSubstrateBatch, ELUTION_THRESHOLDS } from '../../utils/storage';

const STATUS_CONFIG = {
  pending: { label: '未分析', color: 'default' },
  analyzed: { label: '分析済', color: 'info' },
  formulated: { label: '配合済', color: 'success' }
};

const SubstrateBatchList = ({ onEdit }) => {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteDialog, setDeleteDialog] = useState({ open: false, target: null });
  const [detailDialog, setDetailDialog] = useState({ open: false, record: null });
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  const loadRecords = () => {
    setLoading(true);
    try {
      const data = getSubstrateBatches();
      setRecords(data.sort((a, b) => new Date(b.deliveryDate) - new Date(a.deliveryDate)));
    } catch (err) {
      setSnackbar({ open: true, message: '読み込みに失敗しました', severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadRecords(); }, []);

  const handleDelete = () => {
    if (!deleteDialog.target) return;
    try {
      deleteSubstrateBatch(deleteDialog.target.id);
      setDeleteDialog({ open: false, target: null });
      setSnackbar({ open: true, message: '削除しました', severity: 'success' });
      loadRecords();
    } catch (err) {
      setSnackbar({ open: true, message: '削除に失敗しました', severity: 'error' });
    }
  };

  const hasExceedance = (analysis) => {
    if (!analysis) return false;
    return Object.entries(ELUTION_THRESHOLDS).some(([key, threshold]) => {
      const val = analysis[key];
      return val !== undefined && val !== null && val > threshold.limit;
    });
  };

  const handleNewRecord = () => {
    if (onEdit) onEdit({});
  };

  return (
    <Box className="section-panel">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography className="section-panel__title" sx={{ mb: '0 !important', pb: '0 !important', borderBottom: 'none !important' }}>
          搬入履歴
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} size="small" onClick={handleNewRecord}>
          新規登録
        </Button>
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
                  <TableRow key={record.id}>
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
                      {record.analysis ? (
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
                      <IconButton size="small" onClick={() => setDeleteDialog({ open: true, target: record })} color="error" aria-label="削除">
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
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
                      {detailDialog.record.analysis.pH !== undefined && (
                        <TableRow>
                          <TableCell>pH</TableCell>
                          <TableCell align="right" sx={{ fontFamily: "'Fira Code', monospace" }}>
                            {detailDialog.record.analysis.pH}
                          </TableCell>
                          <TableCell align="right">-</TableCell>
                          <TableCell>-</TableCell>
                        </TableRow>
                      )}
                      {detailDialog.record.analysis.moisture !== undefined && (
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
                        const val = detailDialog.record.analysis[key];
                        if (val === undefined || val === null) return null;
                        const exceeded = val > threshold.limit;
                        return (
                          <TableRow key={key}>
                            <TableCell>{threshold.name} ({key})</TableCell>
                            <TableCell align="right" sx={{
                              fontFamily: "'Fira Code', monospace",
                              fontWeight: exceeded ? 600 : 400,
                              color: exceeded ? '#DC2626' : 'inherit'
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
                    固化剤: {detailDialog.record.formulation.solidifierType} ({detailDialog.record.formulation.solidifierAmount} {detailDialog.record.formulation.solidifierUnit})
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: "'Fira Code', monospace" }}>
                    抑制材: {detailDialog.record.formulation.suppressorType} ({detailDialog.record.formulation.suppressorAmount} {detailDialog.record.formulation.suppressorUnit})
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

      {/* Delete Dialog */}
      <Dialog open={deleteDialog.open} onClose={() => setDeleteDialog({ open: false, target: null })}>
        <DialogTitle>削除確認</DialogTitle>
        <DialogContent>
          <Typography>
            {deleteDialog.target?.source} ({deleteDialog.target?.deliveryDate}) の搬入記録を削除しますか？
          </Typography>
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

export default SubstrateBatchList;
