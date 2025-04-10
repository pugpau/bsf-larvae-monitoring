import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper, 
  IconButton,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Snackbar,
  Alert,
  Chip
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Info as InfoIcon } from '@mui/icons-material';
import axios from 'axios';

const SubstrateBatchList = ({ onEdit }) => {
  const [substrateBatches, setSubstrateBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [batchToDelete, setBatchToDelete] = useState(null);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [openSnackbar, setOpenSnackbar] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState('success');

  const fetchSubstrateBatches = async () => {
    setLoading(true);
    try {
      // モックデータを使用
      const mockData = [
        {
          id: '1',
          farm_id: '112',
          name: '下水汚泥バッチA',
          description: '2025年4月1日に作成した下水汚泥バッチ',
          total_weight: 100,
          weight_unit: 'kg',
          batch_number: 'B20250401-001',
          location: 'エリアA-1',
          components: [
            {
              substrate_type_id: '1',
              substrate_type_name: '下水汚泥タイプA',
              ratio: 70
            },
            {
              substrate_type_id: '3',
              substrate_type_name: 'おが屑タイプC',
              ratio: 30
            }
          ]
        },
        {
          id: '2',
          farm_id: '112',
          name: '鶏糞バッチB',
          description: '2025年4月2日に作成した鶏糞バッチ',
          total_weight: 80,
          weight_unit: 'kg',
          batch_number: 'B20250402-001',
          location: 'エリアB-2',
          components: [
            {
              substrate_type_id: '2',
              substrate_type_name: '鶏糞タイプB',
              ratio: 60
            },
            {
              substrate_type_id: '3',
              substrate_type_name: 'おが屑タイプC',
              ratio: 40
            }
          ]
        }
      ];
      
      setSubstrateBatches(mockData);
      setError(null);
    } catch (err) {
      console.error('基質バッチの取得に失敗しました', err);
      setError('基質バッチの取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubstrateBatches();
  }, []);

  const handleEditClick = (batch) => {
    if (onEdit) {
      onEdit(batch);
    }
  };

  const handleDeleteClick = (batch) => {
    setBatchToDelete(batch);
    setDeleteDialogOpen(true);
  };

  const handleDetailsClick = (batch) => {
    setSelectedBatch(batch);
    setDetailsDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!batchToDelete) return;

    try {
      // モックデータの削除処理
      setSubstrateBatches(substrateBatches.filter(batch => batch.id !== batchToDelete.id));
      setSnackbarMessage('基質バッチを削除しました。');
      setSnackbarSeverity('success');
      setOpenSnackbar(true);
    } catch (err) {
      console.error('基質バッチの削除に失敗しました', err);
      setSnackbarMessage('基質バッチの削除に失敗しました。');
      setSnackbarSeverity('error');
      setOpenSnackbar(true);
    } finally {
      setDeleteDialogOpen(false);
      setBatchToDelete(null);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setBatchToDelete(null);
  };

  const handleDetailsClose = () => {
    setDetailsDialogOpen(false);
    setSelectedBatch(null);
  };

  const handleSnackbarClose = (event, reason) => {
    if (reason === 'clickaway') {
      return;
    }
    setOpenSnackbar(false);
  };

  if (loading) {
    return <Typography>読み込み中...</Typography>;
  }

  if (error) {
    return <Typography color="error">{error}</Typography>;
  }

  return (
    <Box sx={{ maxWidth: 800, margin: 'auto', p: 2 }}>
      <Typography variant="h6" gutterBottom>
        基質バッチ一覧
      </Typography>
      
      {substrateBatches.length === 0 ? (
        <Typography>基質バッチがありません。</Typography>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ファームID</TableCell>
                <TableCell>バッチ名</TableCell>
                <TableCell>総重量</TableCell>
                <TableCell>保管場所</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {substrateBatches.map((batch) => (
                <TableRow key={batch.id}>
                  <TableCell>{batch.farm_id}</TableCell>
                  <TableCell>{batch.name}</TableCell>
                  <TableCell>{batch.total_weight} {batch.weight_unit}</TableCell>
                  <TableCell>{batch.location}</TableCell>
                  <TableCell>
                    <IconButton onClick={() => handleDetailsClick(batch)}>
                      <InfoIcon />
                    </IconButton>
                    <IconButton onClick={() => handleEditClick(batch)}>
                      <EditIcon />
                    </IconButton>
                    <IconButton onClick={() => handleDeleteClick(batch)}>
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* 詳細ダイアログ */}
      <Dialog
        open={detailsDialogOpen}
        onClose={handleDetailsClose}
        maxWidth="md"
      >
        <DialogTitle>基質バッチ詳細</DialogTitle>
        <DialogContent>
          {selectedBatch && (
            <Box>
              <Typography variant="subtitle1">基本情報</Typography>
              <TableContainer component={Paper} sx={{ mb: 2 }}>
                <Table size="small">
                  <TableBody>
                    <TableRow>
                      <TableCell component="th" scope="row">ファームID</TableCell>
                      <TableCell>{selectedBatch.farm_id}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell component="th" scope="row">バッチ名</TableCell>
                      <TableCell>{selectedBatch.name}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell component="th" scope="row">説明</TableCell>
                      <TableCell>{selectedBatch.description}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell component="th" scope="row">総重量</TableCell>
                      <TableCell>{selectedBatch.total_weight} {selectedBatch.weight_unit}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell component="th" scope="row">バッチ番号</TableCell>
                      <TableCell>{selectedBatch.batch_number}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell component="th" scope="row">保管場所</TableCell>
                      <TableCell>{selectedBatch.location}</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>

              <Typography variant="subtitle1">基質コンポーネント</Typography>
              <TableContainer component={Paper}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>基質タイプ</TableCell>
                      <TableCell>比率 (%)</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {selectedBatch.components && selectedBatch.components.map((component, index) => (
                      <TableRow key={index}>
                        <TableCell>{component.substrate_type_name || component.substrate_type_id}</TableCell>
                        <TableCell>{component.ratio}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDetailsClose}>閉じる</Button>
        </DialogActions>
      </Dialog>

      {/* 削除確認ダイアログ */}
      <Dialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
      >
        <DialogTitle>基質バッチの削除</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {batchToDelete && `基質バッチ「${batchToDelete.name}」を削除しますか？`}
            この操作は元に戻せません。
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel}>キャンセル</Button>
          <Button onClick={handleDeleteConfirm} color="error">
            削除
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={openSnackbar} autoHideDuration={6000} onClose={handleSnackbarClose}>
        <Alert onClose={handleSnackbarClose} severity={snackbarSeverity} sx={{ width: '100%' }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default SubstrateBatchList;
