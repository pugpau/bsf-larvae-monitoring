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
  IconButton,
  Snackbar,
  Alert,
  FormHelperText,
  LinearProgress,
  Tooltip,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Paper,
  Divider
} from '@mui/material';
import { 
  Add as AddIcon, 
  Delete as DeleteIcon, 
  Sensors as SensorsIcon,
  Link as LinkIcon
} from '@mui/icons-material';
import axios from 'axios';

const SubstrateBatchForm = ({ initialData, onSubmitSuccess }) => {
  const [id, setId] = useState('');
  const [farmId, setFarmId] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [totalWeight, setTotalWeight] = useState('');
  const [weightUnit, setWeightUnit] = useState('kg');
  const [batchNumber, setBatchNumber] = useState('');
  const [location, setLocation] = useState('');

  const [substrateTypes, setSubstrateTypes] = useState([]);
  const [components, setComponents] = useState([]);
  const [sensorDevices, setSensorDevices] = useState([]);
  const [availableSensorDevices, setAvailableSensorDevices] = useState([]);
  const [selectedSensorDevice, setSelectedSensorDevice] = useState('');
  const [openSnackbar, setOpenSnackbar] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState('success'); // 'success' or 'error'
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  
  // バリデーション状態
  const [errors, setErrors] = useState({
    farmId: '',
    name: '',
    totalWeight: '',
    components: []
  });
  
  // 比率の合計
  const [totalRatio, setTotalRatio] = useState(0);

  // 基質タイプとセンサーデバイスの一覧を取得
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // 基質タイプを取得
        const typesResponse = await axios.get('http://localhost:8000/substrate/types');
        setSubstrateTypes(typesResponse.data);
        
        // センサーデバイスを取得
        const devicesResponse = await axios.get('http://localhost:8000/sensors/devices');
        setAvailableSensorDevices(devicesResponse.data);
      } catch (error) {
        console.error('データの取得に失敗しました', error);
        setSnackbarMessage('データの取得に失敗しました。再読み込みしてください。');
        setSnackbarSeverity('error');
        setOpenSnackbar(true);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);
  
  // 比率の合計を計算
  useEffect(() => {
    const total = components.reduce((sum, comp) => sum + (parseFloat(comp.ratio) || 0), 0);
    setTotalRatio(total);
  }, [components]);

  // 初期データがある場合はフォームに設定
  useEffect(() => {
    if (initialData) {
      setId(initialData.id || '');
      setFarmId(initialData.farm_id || '');
      setName(initialData.name || '');
      setDescription(initialData.description || '');
      setTotalWeight(initialData.total_weight || '');
      setWeightUnit(initialData.weight_unit || 'kg');
      setBatchNumber(initialData.batch_number || '');
      setLocation(initialData.location || '');
      
      // コンポーネントの設定
      if (initialData.components && initialData.components.length > 0 && substrateTypes.length > 0) {
        // 基質タイプIDが選択肢に存在するかチェック
        const validComponents = initialData.components.map(comp => {
          // 基質タイプIDが選択肢に存在するかチェック
          const typeExists = substrateTypes.some(type => type.id === comp.substrate_type_id);
          if (!typeExists) {
            // 存在しない場合は空の値に設定
            return { ...comp, substrate_type_id: '' };
          }
          return comp;
        });
        setComponents(validComponents);
      } else {
        setComponents([]);
      }
      
      // 関連センサーデバイスを取得
      const fetchLinkedSensors = async () => {
        try {
          const response = await axios.get(`http://localhost:8000/sensors/devices?substrate_batch_id=${initialData.id}`);
          setSensorDevices(response.data);
        } catch (error) {
          console.error('関連センサーデバイスの取得に失敗しました', error);
        }
      };
      
      if (initialData.id) {
        fetchLinkedSensors();
      }
      
      setIsEditing(true);
    } else {
      resetForm();
      setIsEditing(false);
    }
  }, [initialData, substrateTypes]);

  // 利用可能なセンサーデバイスを更新
  useEffect(() => {
    if (availableSensorDevices.length > 0) {
      // 既に関連付けられているデバイスを除外
      const linkedDeviceIds = sensorDevices.map(device => device.id);
      const available = availableSensorDevices.filter(device => !linkedDeviceIds.includes(device.id));
      
      // 他の基質バッチに関連付けられていないデバイスのみを表示
      const unlinkedDevices = available.filter(device => !device.substrate_batch_id || device.substrate_batch_id === id);
      setAvailableSensorDevices(unlinkedDevices);
    }
  }, [sensorDevices, availableSensorDevices, id]);

  const resetForm = () => {
    setId('');
    setFarmId('');
    setName('');
    setDescription('');
    setTotalWeight('');
    setWeightUnit('kg');
    setBatchNumber('');
    setLocation('');
    setComponents([]);
    setSensorDevices([]);
    setSelectedSensorDevice('');
  };

  const addComponent = () => {
    setComponents([...components, { substrate_type_id: '', ratio: 0 }]);
  };

  const updateComponent = (index, field, value) => {
    const newComponents = [...components];
    if (field === 'ratio') {
      newComponents[index][field] = parseFloat(value) || 0;
      
      // エラーをクリア
      if (errors.components[index]) {
        const newComponentErrors = [...errors.components];
        newComponentErrors[index] = '';
        setErrors({...errors, components: newComponentErrors});
      }
    } else {
      newComponents[index][field] = value;
      
      // substrate_type_idが選択されたらエラーをクリア
      if (field === 'substrate_type_id' && value && errors.components[index]) {
        const newComponentErrors = [...errors.components];
        newComponentErrors[index] = '';
        setErrors({...errors, components: newComponentErrors});
      }
    }
    setComponents(newComponents);
  };

  const removeComponent = (index) => {
    const newComponents = components.filter((_, i) => i !== index);
    setComponents(newComponents);
  };

  // フォームバリデーション
  const validateForm = () => {
    const newErrors = {
      farmId: '',
      name: '',
      totalWeight: '',
      components: Array(components.length).fill('')
    };
    
    let isValid = true;
    
    // ファームIDのバリデーション
    if (!farmId.trim()) {
      newErrors.farmId = 'ファームIDは必須です';
      isValid = false;
    }
    
    // 名前のバリデーション
    if (name.length > 100) {
      newErrors.name = 'バッチ名は100文字以内で入力してください';
      isValid = false;
    }
    
    // 総重量のバリデーション
    if (!totalWeight) {
      newErrors.totalWeight = '総重量は必須です';
      isValid = false;
    } else if (isNaN(parseFloat(totalWeight)) || parseFloat(totalWeight) <= 0) {
      newErrors.totalWeight = '総重量は正の数値で入力してください';
      isValid = false;
    }
    
    // コンポーネントのバリデーション
    if (components.length === 0) {
      setSnackbarMessage('少なくとも1つの基質コンポーネントを追加してください');
      setSnackbarSeverity('error');
      setOpenSnackbar(true);
      isValid = false;
    } else {
      components.forEach((comp, index) => {
        if (!comp.substrate_type_id) {
          newErrors.components[index] = '基質タイプを選択してください';
          isValid = false;
        }
        
        if (isNaN(parseFloat(comp.ratio)) || parseFloat(comp.ratio) <= 0) {
          newErrors.components[index] = '比率は正の数値で入力してください';
          isValid = false;
        }
      });
      
      // 比率の合計が100%になっているか確認
      if (totalRatio !== 100) {
        setSnackbarMessage(`コンポーネントの比率の合計が100%になるように設定してください（現在: ${totalRatio}%）`);
        setSnackbarSeverity('error');
        setOpenSnackbar(true);
        isValid = false;
      }
      
      // 同じ基質タイプが複数選択されていないか確認
      const typeIds = components.map(comp => comp.substrate_type_id);
      const uniqueTypeIds = new Set(typeIds);
      if (typeIds.length !== uniqueTypeIds.size) {
        setSnackbarMessage('同じ基質タイプが複数選択されています。それぞれ異なる基質タイプを選択してください。');
        setSnackbarSeverity('error');
        setOpenSnackbar(true);
        isValid = false;
      }
    }
    
    setErrors(newErrors);
    return isValid;
  };

  // センサーデバイスを追加
  const addSensorDevice = async () => {
    if (!selectedSensorDevice) return;
    
    const device = availableSensorDevices.find(d => d.id === selectedSensorDevice);
    if (!device) return;
    
    setLoading(true);
    try {
      // デバイスを基質バッチに関連付ける
      await axios.patch(`http://localhost:8000/sensors/devices/${device.id}`, {
        substrate_batch_id: id
      });
      
      // 関連付けられたデバイスリストを更新
      setSensorDevices([...sensorDevices, device]);
      setSelectedSensorDevice('');
      
      setSnackbarMessage('センサーデバイスを関連付けました。');
      setSnackbarSeverity('success');
      setOpenSnackbar(true);
    } catch (error) {
      console.error('センサーデバイスの関連付けに失敗しました', error);
      setSnackbarMessage('センサーデバイスの関連付けに失敗しました。');
      setSnackbarSeverity('error');
      setOpenSnackbar(true);
    } finally {
      setLoading(false);
    }
  };
  
  // センサーデバイスの関連付けを解除
  const removeSensorDevice = async (deviceId) => {
    setLoading(true);
    try {
      // デバイスの関連付けを解除
      await axios.patch(`http://localhost:8000/sensors/devices/${deviceId}`, {
        substrate_batch_id: null
      });
      
      // 関連付けられたデバイスリストを更新
      setSensorDevices(sensorDevices.filter(d => d.id !== deviceId));
      
      setSnackbarMessage('センサーデバイスの関連付けを解除しました。');
      setSnackbarSeverity('success');
      setOpenSnackbar(true);
    } catch (error) {
      console.error('センサーデバイスの関連付け解除に失敗しました', error);
      setSnackbarMessage('センサーデバイスの関連付け解除に失敗しました。');
      setSnackbarSeverity('error');
      setOpenSnackbar(true);
    } finally {
      setLoading(false);
    }
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
      name,
      description,
      components,
      total_weight: parseFloat(totalWeight),
      weight_unit: weightUnit,
      batch_number: batchNumber,
      location
    };

    try {
      let response;
      if (isEditing) {
        // 更新（PATCHメソッドを使用）
        // バックエンドの期待するデータ形式に合わせる
        const updateData = {
          name,
          description,
          total_weight: parseFloat(totalWeight),
          location,
          change_reason: "基質バッチの更新"
        };
        response = await axios.patch(`http://localhost:8000/substrate/batches/${id}`, updateData);
        setSnackbarMessage('基質バッチを更新しました。');
      } else {
        // 新規作成
        response = await axios.post('http://localhost:8000/substrate/batches', data);
        
        // 新規作成の場合、IDを設定して編集モードに移行
        if (response.data && response.data.id) {
          setId(response.data.id);
          setIsEditing(true);
        }
        
        setSnackbarMessage('基質バッチを登録しました。');
      }
      
      console.log('基質バッチ操作成功:', response.data);
      setSnackbarSeverity('success');
      setOpenSnackbar(true);
      
      if (!isEditing) {
        resetForm();
      }
      
      if (onSubmitSuccess) {
        onSubmitSuccess();
      }
    } catch (error) {
      console.error('基質バッチ操作エラー:', error);
      
      // エラーレスポンスの詳細を取得
      let errorMessage = isEditing ? '基質バッチの更新に失敗しました。' : '基質バッチの登録に失敗しました。';
      
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
          errorMessage += ' 指定された基質バッチが見つかりません。';
        } else if (error.response.status === 500) {
          errorMessage += ' サーバーエラーが発生しました。';
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

  // デバイスタイプの日本語表示
  const getDeviceTypeLabel = (deviceType) => {
    switch (deviceType) {
      case 'temperature_sensor':
        return '温度センサー';
      case 'humidity_sensor':
        return '湿度センサー';
      case 'pressure_sensor':
        return '気圧センサー';
      case 'gas_sensor':
        return 'ガスセンサー';
      case 'light_sensor':
        return '光センサー';
      case 'motion_sensor':
        return 'モーションセンサー';
      case 'camera':
        return 'カメラ';
      default:
        return deviceType;
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ maxWidth: 800, margin: 'auto', p: 2 }}>
      <Typography variant="h6" gutterBottom>
        {isEditing ? '基質バッチ編集' : '基質バッチ登録'}
      </Typography>
      
      {loading && <LinearProgress sx={{ mb: 2 }} />}
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              基本情報
            </Typography>
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
              
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="バッチ名"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  error={!!errors.name}
                  helperText={errors.name}
                  onBlur={() => {
                    if (name.length > 100) {
                      setErrors({...errors, name: 'バッチ名は100文字以内で入力してください'});
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
              
              <Grid item xs={8}>
                <TextField
                  fullWidth
                  label="総重量"
                  type="number"
                  value={totalWeight}
                  onChange={(e) => setTotalWeight(e.target.value)}
                  required
                  error={!!errors.totalWeight}
                  helperText={errors.totalWeight}
                  onBlur={() => {
                    if (!totalWeight) {
                      setErrors({...errors, totalWeight: '総重量は必須です'});
                    } else if (isNaN(parseFloat(totalWeight)) || parseFloat(totalWeight) <= 0) {
                      setErrors({...errors, totalWeight: '総重量は正の数値で入力してください'});
                    } else {
                      setErrors({...errors, totalWeight: ''});
                    }
                  }}
                  inputProps={{ min: 0.1, step: 0.1 }}
                />
              </Grid>
              
              <Grid item xs={4}>
                <FormControl fullWidth>
                  <InputLabel>単位</InputLabel>
                  <Select
                    value={weightUnit}
                    label="単位"
                    onChange={(e) => setWeightUnit(e.target.value)}
                  >
                    <MenuItem value="kg">kg</MenuItem>
                    <MenuItem value="g">g</MenuItem>
                    <MenuItem value="t">t</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={6}>
                <TextField
                  fullWidth
                  label="バッチ番号"
                  value={batchNumber}
                  onChange={(e) => setBatchNumber(e.target.value)}
                />
              </Grid>
              
              <Grid item xs={6}>
                <TextField
                  fullWidth
                  label="保管場所"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                />
              </Grid>
            </Grid>
          </Paper>
          
          <Paper sx={{ p: 2, mt: 2 }}>
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1" gutterBottom>
                基質コンポーネント
              </Typography>
              
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Typography variant="body2" sx={{ mr: 1 }}>
                  比率の合計: {totalRatio}%
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={Math.min(totalRatio, 100)} 
                  color={totalRatio === 100 ? "success" : totalRatio > 100 ? "error" : "primary"}
                  sx={{ flexGrow: 1, height: 8, borderRadius: 4 }}
                />
              </Box>
            </Box>
            
            {components.map((comp, index) => (
              <Grid container spacing={1} key={index} sx={{ mb: 1 }}>
                <Grid item xs={8}>
                  <FormControl fullWidth error={!!errors.components[index]}>
                    <InputLabel>基質タイプ</InputLabel>
                    <Select
                      value={comp.substrate_type_id}
                      label="基質タイプ"
                      onChange={(e) => updateComponent(index, 'substrate_type_id', e.target.value)}
                      required
                    >
                      {substrateTypes.map((type) => (
                        <MenuItem key={type.id} value={type.id}>
                          {type.name}
                        </MenuItem>
                      ))}
                    </Select>
                    {errors.components[index] && <FormHelperText>{errors.components[index]}</FormHelperText>}
                  </FormControl>
                </Grid>
                <Grid item xs={3}>
                  <Tooltip title={`現在の合計: ${totalRatio}%`} placement="top">
                    <TextField
                      fullWidth
                      label="比率 (%)"
                      type="number"
                      value={comp.ratio}
                      onChange={(e) => updateComponent(index, 'ratio', e.target.value)}
                      inputProps={{ min: 0, max: 100, step: 0.1 }}
                      required
                      error={!!errors.components[index]}
                    />
                  </Tooltip>
                </Grid>
                <Grid item xs={1}>
                  <IconButton onClick={() => removeComponent(index)}>
                    <DeleteIcon />
                  </IconButton>
                </Grid>
              </Grid>
            ))}
            
            <Button 
              startIcon={<AddIcon />} 
              onClick={addComponent}
              variant="outlined"
            >
              コンポーネントを追加
            </Button>
          </Paper>
          
          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between' }}>
            <Button 
              type="submit" 
              variant="contained" 
              color="primary"
              sx={{ width: '48%' }}
            >
              {isEditing ? '更新' : '登録'}
            </Button>
            
            <Button 
              variant="outlined" 
              color="secondary"
              sx={{ width: '48%' }}
              onClick={handleCancel}
            >
              キャンセル
            </Button>
          </Box>
        </Grid>
        
        <Grid item xs={12} md={4}>
          {isEditing && (
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle1" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                <SensorsIcon sx={{ mr: 1 }} />
                関連センサーデバイス
              </Typography>
              
              {sensorDevices.length > 0 ? (
                <List dense>
                  {sensorDevices.map((device) => (
                    <ListItem key={device.id}>
                      <ListItemText 
                        primary={device.name || device.device_id} 
                        secondary={getDeviceTypeLabel(device.device_type)}
                      />
                      <ListItemSecondaryAction>
                        <IconButton 
                          edge="end" 
                          size="small" 
                          onClick={() => removeSensorDevice(device.id)}
                          title="関連付けを解除"
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  関連付けられたセンサーデバイスはありません
                </Typography>
              )}
              
              <Divider sx={{ my: 2 }} />
              
              <Typography variant="subtitle2" gutterBottom>
                センサーデバイスを関連付ける
              </Typography>
              
              <FormControl fullWidth sx={{ mb: 1 }}>
                <InputLabel>デバイスを選択</InputLabel>
                <Select
                  value={selectedSensorDevice}
                  label="デバイスを選択"
                  onChange={(e) => setSelectedSensorDevice(e.target.value)}
                  disabled={availableSensorDevices.length === 0}
                >
                  <MenuItem value="">選択してください</MenuItem>
                  {availableSensorDevices.map((device) => (
                    <MenuItem key={device.id} value={device.id}>
                      {device.name || device.device_id} ({getDeviceTypeLabel(device.device_type)})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              <Button
                variant="outlined"
                color="primary"
                startIcon={<LinkIcon />}
                onClick={addSensorDevice}
                disabled={!selectedSensorDevice}
                fullWidth
              >
                関連付ける
              </Button>
              
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                * 他の基質バッチに関連付けられていないデバイスのみ表示されます
              </Typography>
            </Paper>
          )}
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

export default SubstrateBatchForm;
