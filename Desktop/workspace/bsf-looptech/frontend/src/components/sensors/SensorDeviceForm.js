import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Button, 
  TextField, 
  Typography, 
  Grid,
  Select, 
  MenuItem, 
  FormControl, 
  InputLabel,
  Snackbar,
  Alert,
  FormHelperText,
  LinearProgress,
  Tooltip
} from '@mui/material';
import axios from 'axios';

const SensorDeviceForm = ({ initialData, onSubmitSuccess }) => {
  const [id, setId] = useState('');
  const [farmId, setFarmId] = useState('');
  const [deviceId, setDeviceId] = useState('');
  const [deviceType, setDeviceType] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState('');
  const [xPosition, setXPosition] = useState('');
  const [yPosition, setYPosition] = useState('');
  const [zPosition, setZPosition] = useState('');
  const [status, setStatus] = useState('active');
  const [substrateBatchId, setSubstrateBatchId] = useState('');

  const [substrateBatches, setSubstrateBatches] = useState([]);
  const [openSnackbar, setOpenSnackbar] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState('success'); // 'success' or 'error'
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  
  // バリデーション状態
  const [errors, setErrors] = useState({
    farmId: '',
    deviceId: '',
    deviceType: '',
    name: '',
    xPosition: '',
    yPosition: '',
    zPosition: ''
  });

  // 基質バッチの一覧を取得
  useEffect(() => {
    const fetchSubstrateBatches = async () => {
      setLoading(true);
      try {
        const response = await axios.get('http://localhost:8000/substrate/batches');
        setSubstrateBatches(response.data);
      } catch (error) {
        console.error('基質バッチの取得に失敗しました', error);
        setSnackbarMessage('基質バッチの取得に失敗しました。再読み込みしてください。');
        setSnackbarSeverity('error');
        setOpenSnackbar(true);
      } finally {
        setLoading(false);
      }
    };

    fetchSubstrateBatches();
  }, []);

  // 初期データがある場合はフォームに設定
  useEffect(() => {
    if (initialData) {
      setId(initialData.id || '');
      setFarmId(initialData.farm_id || '');
      setDeviceId(initialData.device_id || '');
      setDeviceType(initialData.device_type || '');
      setName(initialData.name || '');
      setDescription(initialData.description || '');
      setLocation(initialData.location || '');
      setXPosition(initialData.x_position !== undefined ? initialData.x_position.toString() : '');
      setYPosition(initialData.y_position !== undefined ? initialData.y_position.toString() : '');
      setZPosition(initialData.z_position !== undefined ? initialData.z_position.toString() : '');
      setStatus(initialData.status || 'active');
      setSubstrateBatchId(initialData.substrate_batch_id || '');
      
      setIsEditing(true);
    } else {
      resetForm();
      setIsEditing(false);
    }
  }, [initialData]);

  const resetForm = () => {
    setId('');
    setFarmId('');
    setDeviceId('');
    setDeviceType('');
    setName('');
    setDescription('');
    setLocation('');
    setXPosition('');
    setYPosition('');
    setZPosition('');
    setStatus('active');
    setSubstrateBatchId('');
  };

  // フォームバリデーション
  const validateForm = () => {
    const newErrors = {
      farmId: '',
      deviceId: '',
      deviceType: '',
      name: '',
      xPosition: '',
      yPosition: '',
      zPosition: ''
    };
    
    let isValid = true;
    
    // ファームIDのバリデーション
    if (!farmId.trim()) {
      newErrors.farmId = 'ファームIDは必須です';
      isValid = false;
    }
    
    // デバイスIDのバリデーション
    if (!deviceId.trim()) {
      newErrors.deviceId = 'デバイスIDは必須です';
      isValid = false;
    }
    
    // デバイスタイプのバリデーション
    if (!deviceType.trim()) {
      newErrors.deviceType = 'デバイスタイプは必須です';
      isValid = false;
    }
    
    // 名前のバリデーション
    if (name.length > 100) {
      newErrors.name = 'デバイス名は100文字以内で入力してください';
      isValid = false;
    }
    
    // X座標のバリデーション
    if (xPosition && isNaN(parseFloat(xPosition))) {
      newErrors.xPosition = 'X座標は数値で入力してください';
      isValid = false;
    }
    
    // Y座標のバリデーション
    if (yPosition && isNaN(parseFloat(yPosition))) {
      newErrors.yPosition = 'Y座標は数値で入力してください';
      isValid = false;
    }
    
    // Z座標のバリデーション
    if (zPosition && isNaN(parseFloat(zPosition))) {
      newErrors.zPosition = 'Z座標は数値で入力してください';
      isValid = false;
    }
    
    setErrors(newErrors);
    return isValid;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // フォームバリデーション
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    
    const data = {
      farm_id: farmId,
      device_id: deviceId,
      device_type: deviceType,
      name,
      description,
      location,
      x_position: xPosition ? parseFloat(xPosition) : null,
      y_position: yPosition ? parseFloat(yPosition) : null,
      z_position: zPosition ? parseFloat(zPosition) : null,
      status,
      substrate_batch_id: substrateBatchId || null
    };

    try {
      let response;
      if (isEditing) {
        // 更新処理
        response = await axios.patch(`http://localhost:8000/sensors/devices/${id}`, data);
        setSnackbarMessage('センサーデバイスを更新しました。');
      } else {
        // 新規作成処理
        response = await axios.post('http://localhost:8000/sensors/devices', data);
        setSnackbarMessage('センサーデバイスを登録しました。');
      }
      
      console.log('センサーデバイス操作成功:', response.data);
      setSnackbarSeverity('success');
      setOpenSnackbar(true);
      resetForm();
      
      if (onSubmitSuccess) {
        onSubmitSuccess();
      }
    } catch (error) {
      console.error('センサーデバイス操作エラー:', error);
      
      // エラーメッセージの設定
      let errorMessage = isEditing ? 'センサーデバイスの更新に失敗しました。' : 'センサーデバイスの登録に失敗しました。';
      
      if (error.response) {
        // サーバーからのレスポンスがある場合
        if (error.response.data && error.response.data.detail) {
          if (Array.isArray(error.response.data.detail)) {
            errorMessage += ' ' + error.response.data.detail.map(err => err.msg).join(', ');
          } else {
            errorMessage += ' ' + error.response.data.detail;
          }
        } else if (error.response.status === 400) {
          errorMessage += ' 入力データが不正です。';
        } else if (error.response.status === 404) {
          errorMessage += ' 指定されたデバイスが見つかりません。';
        } else if (error.response.status === 409) {
          errorMessage += ' 同じIDのデバイスが既に存在します。';
        }
      } else if (error.request) {
        // リクエストは送信されたがレスポンスがない場合
        errorMessage += ' サーバーに接続できません。ネットワーク接続を確認してください。';
      } else {
        // リクエスト設定中にエラーが発生した場合
        errorMessage += ' ' + error.message;
      }
      
      setSnackbarMessage(errorMessage);
      setSnackbarSeverity('error');
      setOpenSnackbar(true);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    resetForm();
    if (onSubmitSuccess) {
      onSubmitSuccess();
    }
  };

  const handleSnackbarClose = (event, reason) => {
    if (reason === 'clickaway') {
      return;
    }
    setOpenSnackbar(false);
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ maxWidth: 600, margin: 'auto', p: 2 }}>
      <Typography variant="h6" gutterBottom>
        {isEditing ? 'センサーデバイス編集' : 'センサーデバイス登録'}
      </Typography>
      
      {loading && <LinearProgress sx={{ mb: 2 }} />}
      
      <Grid container spacing={2}>
        <Grid item xs={12}>
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
        
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="デバイスID"
            value={deviceId}
            onChange={(e) => setDeviceId(e.target.value)}
            required
            error={!!errors.deviceId}
            helperText={errors.deviceId}
            onBlur={() => {
              if (!deviceId.trim()) {
                setErrors({...errors, deviceId: 'デバイスIDは必須です'});
              } else {
                setErrors({...errors, deviceId: ''});
              }
            }}
          />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <FormControl fullWidth error={!!errors.deviceType}>
            <InputLabel>デバイスタイプ</InputLabel>
            <Select
              value={deviceType}
              label="デバイスタイプ"
              onChange={(e) => setDeviceType(e.target.value)}
              required
              onBlur={() => {
                if (!deviceType.trim()) {
                  setErrors({...errors, deviceType: 'デバイスタイプは必須です'});
                } else {
                  setErrors({...errors, deviceType: ''});
                }
              }}
            >
              <MenuItem value="temperature_sensor">温度センサー</MenuItem>
              <MenuItem value="humidity_sensor">湿度センサー</MenuItem>
              <MenuItem value="pressure_sensor">気圧センサー</MenuItem>
              <MenuItem value="gas_sensor">ガスセンサー</MenuItem>
              <MenuItem value="light_sensor">光センサー</MenuItem>
              <MenuItem value="motion_sensor">モーションセンサー</MenuItem>
              <MenuItem value="camera">カメラ</MenuItem>
              <MenuItem value="other">その他</MenuItem>
            </Select>
            {errors.deviceType && <FormHelperText>{errors.deviceType}</FormHelperText>}
          </FormControl>
        </Grid>
        
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="デバイス名"
            value={name}
            onChange={(e) => setName(e.target.value)}
            error={!!errors.name}
            helperText={errors.name}
            onBlur={() => {
              if (name.length > 100) {
                setErrors({...errors, name: 'デバイス名は100文字以内で入力してください'});
              } else {
                setErrors({...errors, name: ''});
              }
            }}
          />
        </Grid>
        
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="説明"
            multiline
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </Grid>
        
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="設置場所"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
        </Grid>
        
        <Grid item xs={12}>
          <Typography variant="subtitle1" gutterBottom>
            3D位置情報
          </Typography>
        </Grid>
        
        <Grid item xs={4}>
          <TextField
            fullWidth
            label="X座標"
            type="number"
            value={xPosition}
            onChange={(e) => setXPosition(e.target.value)}
            error={!!errors.xPosition}
            helperText={errors.xPosition}
            onBlur={() => {
              if (xPosition && isNaN(parseFloat(xPosition))) {
                setErrors({...errors, xPosition: 'X座標は数値で入力してください'});
              } else {
                setErrors({...errors, xPosition: ''});
              }
            }}
            inputProps={{ step: 0.1 }}
          />
        </Grid>
        
        <Grid item xs={4}>
          <TextField
            fullWidth
            label="Y座標"
            type="number"
            value={yPosition}
            onChange={(e) => setYPosition(e.target.value)}
            error={!!errors.yPosition}
            helperText={errors.yPosition}
            onBlur={() => {
              if (yPosition && isNaN(parseFloat(yPosition))) {
                setErrors({...errors, yPosition: 'Y座標は数値で入力してください'});
              } else {
                setErrors({...errors, yPosition: ''});
              }
            }}
            inputProps={{ step: 0.1 }}
          />
        </Grid>
        
        <Grid item xs={4}>
          <TextField
            fullWidth
            label="Z座標"
            type="number"
            value={zPosition}
            onChange={(e) => setZPosition(e.target.value)}
            error={!!errors.zPosition}
            helperText={errors.zPosition}
            onBlur={() => {
              if (zPosition && isNaN(parseFloat(zPosition))) {
                setErrors({...errors, zPosition: 'Z座標は数値で入力してください'});
              } else {
                setErrors({...errors, zPosition: ''});
              }
            }}
            inputProps={{ step: 0.1 }}
          />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <FormControl fullWidth>
            <InputLabel>ステータス</InputLabel>
            <Select
              value={status}
              label="ステータス"
              onChange={(e) => setStatus(e.target.value)}
            >
              <MenuItem value="active">稼働中</MenuItem>
              <MenuItem value="inactive">停止中</MenuItem>
              <MenuItem value="maintenance">メンテナンス中</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <FormControl fullWidth>
            <InputLabel>基質バッチ</InputLabel>
            <Select
              value={substrateBatchId}
              label="基質バッチ"
              onChange={(e) => setSubstrateBatchId(e.target.value)}
            >
              <MenuItem value="">なし</MenuItem>
              {substrateBatches.map((batch) => (
                <MenuItem key={batch.id} value={batch.id}>
                  {batch.name || batch.batch_number || batch.id}
                </MenuItem>
              ))}
            </Select>
            <FormHelperText>このセンサーに関連付ける基質バッチを選択してください</FormHelperText>
          </FormControl>
        </Grid>
        
        <Grid item xs={6}>
          <Button 
            type="submit" 
            variant="contained" 
            color="primary"
            fullWidth
          >
            {isEditing ? '更新' : '登録'}
          </Button>
        </Grid>
        
        <Grid item xs={6}>
          <Button 
            variant="outlined" 
            color="secondary"
            fullWidth
            onClick={handleCancel}
          >
            キャンセル
          </Button>
        </Grid>
      </Grid>
      <Snackbar open={openSnackbar} autoHideDuration={6000} onClose={handleSnackbarClose}>
        <Alert onClose={handleSnackbarClose} severity={snackbarSeverity} sx={{ width: '100%' }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default SensorDeviceForm;
