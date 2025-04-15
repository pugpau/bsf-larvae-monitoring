import React, { useState } from 'react';
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
  TextField,
  Button,
  Grid,
  CircularProgress,
  Alert,
  Snackbar,
  FormHelperText,
  LinearProgress,
  Card,
  CardContent,
  Divider,
  Chip,
  Tabs,
  Tab,
  IconButton,
  Tooltip
} from '@mui/material';
import { 
  Search as SearchIcon, 
  Refresh as RefreshIcon,
  BarChart as ChartIcon,
  TableChart as TableIcon,
  Timeline as TimelineIcon,
  ViewInAr as View3DIcon,
  Visibility as VisibilityIcon
} from '@mui/icons-material';
import SensorCharts from './SensorCharts';
import SensorProphetAnalysis from './SensorProphetAnalysis';
import Sensor3DVisualization from './Sensor3DVisualization';
import SensorReadingDetail from './SensorReadingDetail';
import axios from 'axios';

const SensorReadingsList = () => {
  const [readings, setReadings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [farmId, setFarmId] = useState('112'); // Default farm ID
  const [deviceType, setDeviceType] = useState('');
  const [deviceId, setDeviceId] = useState('');
  const [measurementType, setMeasurementType] = useState('');
  const [location, setLocation] = useState('');
  const [startTime, setStartTime] = useState(new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString().slice(0, 16)); // 24 hours ago
  const [endTime, setEndTime] = useState(new Date().toISOString().slice(0, 16));
  const [limit, setLimit] = useState(100);
  const [openSnackbar, setOpenSnackbar] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState('success');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [viewMode, setViewMode] = useState('table'); // 'table', 'chart', 'prophet', or '3d'
  const [selectedReading, setSelectedReading] = useState(null);
  const [openDetailDialog, setOpenDetailDialog] = useState(false);
  
  // バリデーション状態
  const [errors, setErrors] = useState({
    farmId: '',
    startTime: '',
    endTime: '',
    limit: ''
  });

  // フォームバリデーション
  const validateForm = () => {
    const newErrors = {
      farmId: '',
      startTime: '',
      endTime: '',
      limit: ''
    };
    
    let isValid = true;
    
    // ファームIDのバリデーション
    if (!farmId.trim()) {
      newErrors.farmId = 'ファームIDは必須です';
      isValid = false;
    }
    
    // 時間範囲のバリデーション
    if (startTime && endTime) {
      const start = new Date(startTime);
      const end = new Date(endTime);
      
      if (start > end) {
        newErrors.startTime = '開始時間は終了時間より前である必要があります';
        newErrors.endTime = '終了時間は開始時間より後である必要があります';
        isValid = false;
      }
      
      // 範囲が広すぎないかチェック (例: 30日以上)
      const diffDays = Math.abs(end - start) / (1000 * 60 * 60 * 24);
      if (diffDays > 30) {
        newErrors.startTime = '時間範囲は30日以内にしてください';
        isValid = false;
      }
    }
    
    // 表示件数のバリデーション
    if (!limit) {
      newErrors.limit = '表示件数は必須です';
      isValid = false;
    } else if (isNaN(parseInt(limit)) || parseInt(limit) <= 0) {
      newErrors.limit = '表示件数は正の整数で入力してください';
      isValid = false;
    } else if (parseInt(limit) > 1000) {
      newErrors.limit = '表示件数は1000以下にしてください';
      isValid = false;
    }
    
    setErrors(newErrors);
    return isValid;
  };

  // Fetch sensor readings
  const fetchSensorReadings = async () => {
    // フォームバリデーション
    if (!validateForm()) {
      return;
    }
    
    setLoading(true);
    setError(null);
    try {
      // クエリパラメータの構築
      const params = new URLSearchParams();
      if (farmId) params.append('farm_id', farmId);
      if (deviceType) params.append('device_type', deviceType);
      if (deviceId) params.append('device_id', deviceId);
      if (measurementType) params.append('measurement_type', measurementType);
      if (location) params.append('location', location);
      if (startTime) params.append('start_time', new Date(startTime).toISOString());
      if (endTime) params.append('end_time', new Date(endTime).toISOString());
      if (limit) params.append('limit', limit.toString());
      
      // APIリクエスト
      const response = await axios.get(`http://localhost:8000/sensors/readings?${params.toString()}`);
      
      setReadings(response.data);
      setLastUpdated(new Date());
      
      setSnackbarMessage(`${response.data.length}件のセンサーデータを取得しました。`);
      setSnackbarSeverity('success');
      setOpenSnackbar(true);
    } catch (err) {
      console.error('Failed to fetch sensor readings:', err);
      
      // エラーメッセージの設定
      let errorMessage = 'センサーデータの取得に失敗しました。';
      
      if (err.response) {
        // サーバーからのレスポンスがある場合
        if (err.response.data && err.response.data.detail) {
          if (Array.isArray(err.response.data.detail)) {
            errorMessage += ' ' + err.response.data.detail.map(e => e.msg).join(', ');
          } else {
            errorMessage += ' ' + err.response.data.detail;
          }
        } else if (err.response.status === 404) {
          errorMessage = 'データが見つかりませんでした。';
        } else if (err.response.status === 500) {
          errorMessage = 'サーバーエラーが発生しました。';
        }
      } else if (err.request) {
        // リクエストは送信されたがレスポンスがない場合
        errorMessage = 'サーバーに接続できません。ネットワーク接続を確認してください。';
      } else {
        // リクエスト設定中にエラーが発生した場合
        errorMessage += ' ' + err.message;
      }
      
      setError(errorMessage);
      setSnackbarMessage(errorMessage);
      setSnackbarSeverity('error');
      setOpenSnackbar(true);
    } finally {
      setLoading(false);
    }
  };

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    fetchSensorReadings();
  };

  // Handle snackbar close
  const handleSnackbarClose = (event, reason) => {
    if (reason === 'clickaway') {
      return;
    }
    setOpenSnackbar(false);
  };

  // Format timestamp for display
  const formatTimestamp = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString();
    } catch (error) {
      return timestamp;
    }
  };
  
  // Handle opening the detail dialog
  const handleOpenDetail = (reading) => {
    setSelectedReading(reading);
    setOpenDetailDialog(true);
  };
  
  // Handle closing the detail dialog
  const handleCloseDetail = () => {
    setOpenDetailDialog(false);
  };

  return (
    <Box sx={{ maxWidth: 1200, margin: 'auto', p: 2 }}>
      <Typography variant="h5" gutterBottom>
        センサーデータ一覧
      </Typography>

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* Filter Form */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            検索条件
          </Typography>
          <Divider sx={{ mb: 2 }} />
          
          <form onSubmit={handleSubmit}>
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="ファームID"
                  value={farmId}
                  onChange={(e) => setFarmId(e.target.value)}
                  required
                  error={!!errors.farmId}
                  helperText={errors.farmId}
                  onBlur={() => {
                    if (!farmId.trim()) {
                      setErrors({...errors, farmId: 'ファームIDは必須です'});
                    } else {
                      setErrors({...errors, farmId: ''});
                    }
                  }}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="開始時間"
                  type="datetime-local"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  InputLabelProps={{
                    shrink: true,
                  }}
                  error={!!errors.startTime}
                  helperText={errors.startTime}
                  onBlur={() => {
                    if (startTime && endTime) {
                      const start = new Date(startTime);
                      const end = new Date(endTime);
                      
                      if (start > end) {
                        setErrors({
                          ...errors, 
                          startTime: '開始時間は終了時間より前である必要があります',
                          endTime: '終了時間は開始時間より後である必要があります'
                        });
                      } else {
                        const diffDays = Math.abs(end - start) / (1000 * 60 * 60 * 24);
                        if (diffDays > 30) {
                          setErrors({...errors, startTime: '時間範囲は30日以内にしてください'});
                        } else {
                          setErrors({...errors, startTime: '', endTime: ''});
                        }
                      }
                    }
                  }}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="終了時間"
                  type="datetime-local"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  InputLabelProps={{
                    shrink: true,
                  }}
                  error={!!errors.endTime}
                  helperText={errors.endTime}
                  onBlur={() => {
                    if (startTime && endTime) {
                      const start = new Date(startTime);
                      const end = new Date(endTime);
                      
                      if (start > end) {
                        setErrors({
                          ...errors, 
                          startTime: '開始時間は終了時間より前である必要があります',
                          endTime: '終了時間は開始時間より後である必要があります'
                        });
                      } else {
                        setErrors({...errors, startTime: '', endTime: ''});
                      }
                    }
                  }}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="表示件数"
                  type="number"
                  value={limit}
                  onChange={(e) => setLimit(e.target.value)}
                  inputProps={{ min: 1, max: 1000 }}
                  error={!!errors.limit}
                  helperText={errors.limit}
                  onBlur={() => {
                    if (!limit) {
                      setErrors({...errors, limit: '表示件数は必須です'});
                    } else if (isNaN(parseInt(limit)) || parseInt(limit) <= 0) {
                      setErrors({...errors, limit: '表示件数は正の整数で入力してください'});
                    } else if (parseInt(limit) > 1000) {
                      setErrors({...errors, limit: '表示件数は1000以下にしてください'});
                    } else {
                      setErrors({...errors, limit: ''});
                    }
                  }}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="デバイスタイプ"
                  value={deviceType}
                  onChange={(e) => setDeviceType(e.target.value)}
                  placeholder="例: temperature_sensor"
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="デバイスID"
                  value={deviceId}
                  onChange={(e) => setDeviceId(e.target.value)}
                  placeholder="例: sensor_001"
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="測定タイプ"
                  value={measurementType}
                  onChange={(e) => setMeasurementType(e.target.value)}
                  placeholder="例: temperature"
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="場所"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="例: area_1"
                />
              </Grid>

              <Grid item xs={12} sm={6}>
                <Button
                  type="submit"
                  variant="contained"
                  color="primary"
                  fullWidth
                  disabled={loading}
                  startIcon={<SearchIcon />}
                >
                  検索
                </Button>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Button
                  variant="outlined"
                  color="secondary"
                  fullWidth
                  onClick={() => {
                    // 検索条件をリセット（ファームIDと時間範囲以外）
                    setDeviceType('');
                    setDeviceId('');
                    setMeasurementType('');
                    setLocation('');
                  }}
                  startIcon={<RefreshIcon />}
                >
                  条件クリア
                </Button>
              </Grid>
            </Grid>
          </form>
        </CardContent>
      </Card>

      {/* Error Message */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Results Summary and View Toggle */}
      {readings.length > 0 && (
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Typography variant="subtitle1" sx={{ mr: 2 }}>
              検索結果: {readings.length}件
            </Typography>
            <Tabs 
              value={viewMode} 
              onChange={(e, newValue) => setViewMode(newValue)}
              aria-label="view mode tabs"
              sx={{ minHeight: 'auto' }}
              variant="scrollable"
              scrollButtons="auto"
            >
              <Tab 
                icon={<TableIcon fontSize="small" />} 
                label="テーブル" 
                value="table" 
                sx={{ minHeight: 'auto', py: 1 }}
              />
              <Tab 
                icon={<ChartIcon fontSize="small" />} 
                label="グラフ" 
                value="chart" 
                sx={{ minHeight: 'auto', py: 1 }}
              />
              <Tab 
                icon={<TimelineIcon fontSize="small" />} 
                label="予測分析" 
                value="prophet" 
                sx={{ minHeight: 'auto', py: 1 }}
              />
              <Tab 
                icon={<View3DIcon fontSize="small" />} 
                label="3D可視化" 
                value="3d" 
                sx={{ minHeight: 'auto', py: 1 }}
              />
            </Tabs>
          </Box>
          {lastUpdated && (
            <Chip 
              label={`最終更新: ${new Date(lastUpdated).toLocaleString()}`} 
              variant="outlined" 
              size="small"
            />
          )}
        </Box>
      )}

      {/* Data View (Table, Chart, Prophet, or 3D) */}
      {readings.length > 0 ? (
        viewMode === 'table' ? (
          // Table View
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>タイムスタンプ</TableCell>
                  <TableCell>ファームID</TableCell>
                  <TableCell>デバイスID</TableCell>
                  <TableCell>デバイスタイプ</TableCell>
                  <TableCell>測定タイプ</TableCell>
                  <TableCell>値</TableCell>
                  <TableCell>単位</TableCell>
                  <TableCell>場所</TableCell>
                  <TableCell align="center">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {readings.map((reading) => (
                  <TableRow key={reading.id} hover>
                    <TableCell>{formatTimestamp(reading.timestamp)}</TableCell>
                    <TableCell>{reading.farm_id}</TableCell>
                    <TableCell>{reading.device_id}</TableCell>
                    <TableCell>{reading.device_type}</TableCell>
                    <TableCell>{reading.measurement_type}</TableCell>
                    <TableCell>{reading.value}</TableCell>
                    <TableCell>{reading.unit}</TableCell>
                    <TableCell>{reading.location || '-'}</TableCell>
                    <TableCell align="center">
                      <Tooltip title="詳細を表示">
                        <IconButton 
                          size="small" 
                          color="primary" 
                          onClick={() => handleOpenDetail(reading)}
                        >
                          <VisibilityIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : viewMode === 'chart' ? (
          // Chart View
          <SensorCharts readings={readings} />
        ) : viewMode === 'prophet' ? (
          // Prophet Analysis View
          <SensorProphetAnalysis readings={readings} />
        ) : (
          // 3D Visualization View
          <Sensor3DVisualization readings={readings} />
        )
      ) : (
        !loading && (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="body1" color="textSecondary">
              データがありません。検索条件を変更してください。
            </Typography>
          </Paper>
        )
      )}

      {/* Snackbar for notifications */}
      <Snackbar
        open={openSnackbar}
        autoHideDuration={6000}
        onClose={handleSnackbarClose}
      >
        <Alert onClose={handleSnackbarClose} severity={snackbarSeverity} sx={{ width: '100%' }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>

      {/* Detail Dialog */}
      <SensorReadingDetail 
        open={openDetailDialog}
        onClose={handleCloseDetail}
        reading={selectedReading}
      />
    </Box>
  );
};

export default SensorReadingsList;
