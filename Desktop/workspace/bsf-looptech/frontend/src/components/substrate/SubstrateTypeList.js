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
  Alert
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon } from '@mui/icons-material';
import axios from 'axios';
import { getSubstrateTypes, deleteSubstrateType } from '../../utils/storage';
import { getCategoryLabel } from '../../utils/unifiedData';

const SubstrateTypeList = ({ onEdit }) => {
  const [substrateTypes, setSubstrateTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [typeToDelete, setTypeToDelete] = useState(null);
  const [openSnackbar, setOpenSnackbar] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState('success');

  const fetchSubstrateTypes = async () => {
    setLoading(true);
    try {
      // モックデータを使用
      const mockData = [
        {
          id: '1',
          name: '下水汚泥タイプA',
          type: 'sewage_sludge',
          description: '下水処理場から回収した汚泥',
          attributes: [
            { name: '水分含有量', value: '60', unit: '%' },
            { name: 'pH', value: '6.5', unit: '' }
          ]
        },
        {
          id: '2',
          name: '鶏糞タイプB',
          type: 'chicken_manure',
          description: '養鶏場から回収した鶏糞',
          attributes: [
            { name: '窒素含有量', value: '4', unit: '%' },
            { name: 'リン含有量', value: '2', unit: '%' }
          ]
        },
        {
          id: '3',
          name: 'おが屑タイプC',
          type: 'sawdust',
          description: '製材所から回収したおが屑',
          attributes: [
            { name: '水分含有量', value: '15', unit: '%' },
            { name: '粒径', value: '2', unit: 'mm' }
          ]
        }
      ];
      
      // ローカルストレージから基質タイプを取得
      const data = getSubstrateTypes();
      setSubstrateTypes(data);
      setError(null);
    } catch (err) {
      console.error('基質タイプの取得に失敗しました', err);
      setError('基質タイプの取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubstrateTypes();
  }, []);

  const handleEditClick = (substrateType) => {
    if (onEdit) {
      onEdit(substrateType);
    }
  };

  const handleDeleteClick = (substrateType) => {
    setTypeToDelete(substrateType);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!typeToDelete) return;

    try {
      // ローカルストレージから削除
      deleteSubstrateType(typeToDelete.id);
      setSubstrateTypes(substrateTypes.filter(type => type.id !== typeToDelete.id));
      setSnackbarMessage('基質タイプを削除しました。');
      setSnackbarSeverity('success');
      setOpenSnackbar(true);
    } catch (err) {
      console.error('基質タイプの削除に失敗しました', err);
      setSnackbarMessage('基質タイプの削除に失敗しました。');
      setSnackbarSeverity('error');
      setOpenSnackbar(true);
    } finally {
      setDeleteDialogOpen(false);
      setTypeToDelete(null);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setTypeToDelete(null);
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
        基質タイプ一覧
      </Typography>
      
      {substrateTypes.length === 0 ? (
        <Typography>基質タイプがありません。</Typography>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>名前</TableCell>
                <TableCell>カテゴリ</TableCell>
                <TableCell>説明</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {substrateTypes.map((type) => (
                <TableRow key={type.id}>
                  <TableCell>{type.name}</TableCell>
                  <TableCell>{getCategoryLabel(type.type)}</TableCell>
                  <TableCell>{type.description}</TableCell>
                  <TableCell>
                    <IconButton onClick={() => handleEditClick(type)}>
                      <EditIcon />
                    </IconButton>
                    <IconButton onClick={() => handleDeleteClick(type)}>
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
      >
        <DialogTitle>基質タイプの削除</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {typeToDelete && `基質タイプ「${typeToDelete.name}」を削除しますか？`}
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

export default SubstrateTypeList;
