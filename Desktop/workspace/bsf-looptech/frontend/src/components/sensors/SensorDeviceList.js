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
  Button,
  IconButton,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Snackbar,
  Alert,
  LinearProgress,
  CircularProgress,
  Chip
} from '@mui/material';
import { 
  Edit as EditIcon, 
  Delete as DeleteIcon,
  Add as AddIcon,
  Link as LinkIcon,
  PowerSettingsNew as PowerIcon
} from '@mui/icons-material';
import SensorDeviceForm from './SensorDeviceForm';
import axios from 'axios';

const SensorDeviceList = () => {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [openForm, setOpenForm] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [openDeleteDialog, setOpenDeleteDialog] = useState(false);
  const [deviceToDelete, setDeviceToDelete] = useState(null);
  const [openSnackbar, setOpenSnackbar] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState('success');
  const [substrateBatches, setSubstrateBatches] = useState([]);
  const [wakingUpDevice, setWakingUpDevice] = useState(null); // 追加：起動中のデバイスID

  // センサーデバイス一覧を取得
  const fetchDevices = async () => {
    setLoading(true);
    try {
      const response = await axios.get('http://localhost:8000/sensors/devices');
      setDevices(response.data);
      setError(null);
    } catch (error) {
      console.error('センサーデバイスの取得に失敗しました', error);
      setError('センサーデバイスの取得に失敗しました。再読み込みしてください。');
      setSnackbarMessage('センサーデバイスの取得に失敗しました。');
      setSnackbarSeverity('error');
      setOpenSnackbar(true);
    } finally {
      setLoading(false);
    }
  };

  // 基質バッチ一覧を取得
  const fetchSubstrateBatches = async () => {
    try {
      const response = await axios.get('http://localhost:8000/substrate/batches');
      setSubstrateBatches(response.data);
    } catch (error) {
      console.error('基質バッチの取得に失敗しました', error);
    }
  };

  // 初期データ取得
  useEffect(() => {
    fetchDevices();
    fetchSubstrateBatches();
  }, []);

  // デバイス編集ダイアログを開く
  const handleEditDevice = (device) => {
    setSelectedDevice(device);
    setOpenForm(true);
  };

  // 新規デバイス登録ダイアログを開く
  const handleAddDevice = () => {
    setSelectedDevice(null);
    setOpenForm(true);
  };

  // デバイス削除ダイアログを開く
  const handleDeleteClick = (device) => {
    setDeviceToDelete(device);
    setOpenDeleteDialog(true);
  };

  // デバイス削除を実行
  const handleDeleteConfirm = async () => {
    if (!deviceToDelete) return;
    
    setLoading(true);
    try {
      await axios.delete(`http://localhost:8000/sensors/devices/${deviceToDelete.id}`);
      
      // 削除成功後、デバイス一覧を更新
      setDevices(devices.filter(device => device.id !== deviceToDelete.id));
      
      setSnackbarMessage('センサーデバイスを削除しました。');
      setSnackbarSeverity('success');
      setOpenSnackbar(true);
    } catch (error) {
      console.error('センサーデバイスの削除に失敗しました', error);
      
      let errorMessage = 'センサーデバイスの削除に失敗しました。';
      
      if (error.response) {
        if (error.response.data && error.response.data.detail) {
          errorMessage += ' ' + error.response.data.detail;
        } else if (error.response.status === 404) {
          errorMessage = 'センサーデバイスが見つかりません。';
        }
      }
      
      setSnackbarMessage(errorMessage);
      setSnackbarSeverity('error');
      setOpenSnackbar(true);
    } finally {
      setLoading(false);
      setOpenDeleteDialog(false);
      setDeviceToDelete(null);
    }
  };

  // フォーム送信後の処理
  const handleFormSubmitSuccess = () => {
    setOpenForm(false);
    fetchDevices(); // デバイス一覧を再取得
  };

  // Snackbarを閉じる
  const handleSnackbarClose = (event, reason) => {
    if (reason === 'clickaway') {
      return;
    }
    setOpenSnackbar(false);
  };
  
  const handleWakeupDevice = async (device) => {
    if (!device) return;
    
    setWakingUpDevice(device.id);
    try {
      await axios.post(`http://localhost:8000/sensors/devices/${device.id}/wakeup`);
      
      setSnackbarMessage(`センサーデバイス「${device.name || device.device_id}」の起動信号を送信しました。`);
      setSnackbarSeverity('success');
      setOpenSnackbar(true);
    } catch (error) {
      console.error('センサーデバイスの起動に失敗しました', error);
      
      let errorMessage = 'センサーデバイスの起動に失敗しました。';
      
      if (error.response) {
        if (error.response.data && error.response.data.detail) {
          errorMessage += ' ' + error.response.data.detail;
        } else if (error.response.status === 404) {
          errorMessage = 'センサーデバイスが見つかりません。';
        }
      }
      
      setSnackbarMessage(errorMessage);
      setSnackbarSeverity('error');
      setOpenSnackbar(true);
    } finally {
      setWakingUpDevice(null);
    }
  };

  // 基質バッチ名を取得
  const getBatchName = (batchId) => {
    if (!batchId) return '-';
    const batch = substrateBatches.find(b => b.id === batchId);
    return batch ? (batch.name || batch.batch_number || batch.id) : batchId;
  };

  // ステータスに応じた色を取得
  const getStatusColor = (status) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'inactive':
        return 'error';
      case 'maintenance':
        return 'warning';
      default:
        return 'default';
    }
  };

  // ステータスの日本語表示
  const getStatusLabel = (status) => {
    switch (status) {
      case 'active':
        return '稼働中';
      case 'inactive':
        return '停止中';
      case 'maintenance':
        return 'メンテナンス中';
      default:
        return status;
    }
  };

  return (
    <Box sx={{ maxWidth: 1200, margin: 'auto', p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5">センサーデバイス一覧</Typography>
        <Button
          variant="contained"
          color="primary"
          startIcon={<AddIcon />}
          onClick={handleAddDevice}
        >
          新規デバイス登録
        </Button>
      </Box>

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {devices.length > 0 ? (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>デバイスID</TableCell>
                <TableCell>デバイスタイプ</TableCell>
                <TableCell>名前</TableCell>
                <TableCell>場所</TableCell>
                <TableCell>3D位置 (X,Y,Z)</TableCell>
                <TableCell>ステータス</TableCell>
                <TableCell>基質バッチ</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {devices.map((device) => (
                <TableRow key={device.id}>
                  <TableCell>{device.device_id}</TableCell>
                  <TableCell>{device.device_type}</TableCell>
                  <TableCell>{device.name || '-'}</TableCell>
                  <TableCell>{device.location || '-'}</TableCell>
                  <TableCell>
                    {device.x_position !== null && device.y_position !== null && device.z_position !== null
                      ? `(${device.x_position}, ${device.y_position}, ${device.z_position})`
                      : '-'}
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={getStatusLabel(device.status)} 
                      color={getStatusColor(device.status)} 
                      size="small" 
                    />
                  </TableCell>
                  <TableCell>
                    {device.substrate_batch_id ? (
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <LinkIcon fontSize="small" sx={{ mr: 0.5 }} />
                        {getBatchName(device.substrate_batch_id)}
                      </Box>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell>
                    <IconButton 
                      size="small" 
                      color="primary" 
                      onClick={() => handleEditDevice(device)}
                      title="編集"
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton 
                      size="small" 
                      color="error" 
                      onClick={() => handleDeleteClick(device)}
                      title="削除"
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                    <IconButton 
                      size="small" 
                      color="success" 
                      onClick={() => handleWakeupDevice(device)}
                      disabled={wakingUpDevice === device.id || device.status === 'active'}
                      title="起動"
                    >
                      <PowerIcon fontSize="small" />
                      {wakingUpDevice === device.id && (
                        <CircularProgress
                          size={24}
                          sx={{
                            position: 'absolute',
                            color: 'green',
                          }}
                        />
                      )}
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        !loading && (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="body1" color="textSecondary">
              センサーデバイスがありません。「新規デバイス登録」ボタンから登録してください。
            </Typography>
          </Paper>
        )
      )}

      {/* デバイス登録/編集ダイアログ */}
      <Dialog 
        open={openForm} 
        onClose={() => setOpenForm(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {selectedDevice ? 'センサーデバイス編集' : 'センサーデバイス登録'}
        </DialogTitle>
        <DialogContent>
          <SensorDeviceForm 
            initialData={selectedDevice} 
            onSubmitSuccess={handleFormSubmitSuccess} 
          />
        </DialogContent>
      </Dialog>

      {/* デバイス削除確認ダイアログ */}
      <Dialog
        open={openDeleteDialog}
        onClose={() => setOpenDeleteDialog(false)}
      >
        <DialogTitle>センサーデバイスの削除</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {deviceToDelete && `デバイス「${deviceToDelete.name || deviceToDelete.device_id}」を削除しますか？`}
            <br />
            この操作は元に戻せません。
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDeleteDialog(false)} color="primary">
            キャンセル
          </Button>
          <Button onClick={handleDeleteConfirm} color="error">
            削除
          </Button>
        </DialogActions>
      </Dialog>

      {/* 通知用Snackbar */}
      <Snackbar open={openSnackbar} autoHideDuration={6000} onClose={handleSnackbarClose}>
        <Alert onClose={handleSnackbarClose} severity={snackbarSeverity} sx={{ width: '100%' }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default SensorDeviceList;
