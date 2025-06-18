/**
 * Real-time sensor data display component.
 * Shows live sensor readings with auto-refresh using realistic data simulation.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  IconButton,
  Button,
  LinearProgress,
  Alert,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Tooltip
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Refresh as RefreshIcon,
  Speed as SpeedIcon,
  Sensors as SensorsIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  CheckCircle as CheckIcon,
  Build as MaintenanceIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon
} from '@mui/icons-material';
import { useRealtimeData } from '../../hooks/useRealtimeData';

// Helper function to get status color and icon
const getStatusInfo = (status) => {
  switch (status) {
    case 'active':
      return { color: 'success', icon: CheckIcon, label: '正常' };
    case 'warning':
      return { color: 'warning', icon: WarningIcon, label: '警告' };
    case 'error':
      return { color: 'error', icon: ErrorIcon, label: 'エラー' };
    case 'maintenance':
      return { color: 'info', icon: MaintenanceIcon, label: 'メンテナンス' };
    default:
      return { color: 'default', icon: SensorsIcon, label: '不明' };
  }
};

// Helper function to get trend information
const getTrendInfo = (currentValue, previousValue) => {
  if (!previousValue) return { trend: 'stable', icon: null, color: 'default' };
  
  const diff = currentValue - previousValue;
  const threshold = Math.abs(previousValue) * 0.05; // 5% threshold
  
  if (Math.abs(diff) < threshold) {
    return { trend: 'stable', icon: null, color: 'default' };
  } else if (diff > 0) {
    return { trend: 'up', icon: TrendingUpIcon, color: 'success' };
  } else {
    return { trend: 'down', icon: TrendingDownIcon, color: 'error' };
  }
};

// Individual sensor card component
const SensorCard = ({ reading, deviceStatus, previousReading }) => {
  const statusInfo = getStatusInfo(deviceStatus?.status || 'active');
  const trendInfo = getTrendInfo(reading?.value, previousReading?.value);
  const StatusIcon = statusInfo.icon;
  const TrendIcon = trendInfo.icon;

  const lastUpdate = reading ? new Date(reading.timestamp).toLocaleTimeString() : 'N/A';
  const batteryLevel = deviceStatus?.battery_level || 0;
  const signalStrength = deviceStatus?.signal_strength || 0;

  return (
    <Card sx={{ height: '100%', position: 'relative', minHeight: 320 }}>
      <CardContent>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <SensorsIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant="h6" component="div">
              {reading?.device_id || 'Unknown Device'}
            </Typography>
          </Box>
          <Chip
            icon={<StatusIcon />}
            label={statusInfo.label}
            color={statusInfo.color}
            size="small"
          />
        </Box>

        {/* Main Value */}
        <Box sx={{ textAlign: 'center', mb: 2 }}>
          <Typography variant="h3" component="div" sx={{ fontWeight: 'bold', mb: 1 }}>
            {reading ? reading.value.toFixed(1) : '--'}
          </Typography>
          <Typography variant="h6" color="text.secondary">
            {reading?.unit || 'N/A'}
          </Typography>
          {TrendIcon && (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mt: 1 }}>
              <TrendIcon sx={{ color: trendInfo.color + '.main', mr: 0.5 }} />
              <Typography variant="body2" color={trendInfo.color + '.main'}>
                {trendInfo.trend === 'up' ? '上昇中' : '下降中'}
              </Typography>
            </Box>
          )}
        </Box>

        <Divider sx={{ mb: 2 }} />

        {/* Device Info */}
        <Grid container spacing={1}>
          <Grid item xs={6}>
            <Typography variant="body2" color="text.secondary">
              場所
            </Typography>
            <Typography variant="body2">
              {reading?.location || 'N/A'}
            </Typography>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="body2" color="text.secondary">
              最終更新
            </Typography>
            <Typography variant="body2">
              {lastUpdate}
            </Typography>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="body2" color="text.secondary">
              バッテリー
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <LinearProgress
                variant="determinate"
                value={batteryLevel}
                sx={{ width: 30, mr: 1, height: 4 }}
                color={batteryLevel > 20 ? 'success' : 'error'}
              />
              <Typography variant="body2">
                {batteryLevel}%
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="body2" color="text.secondary">
              信号強度
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <LinearProgress
                variant="determinate"
                value={signalStrength}
                sx={{ width: 30, mr: 1, height: 4 }}
                color={signalStrength > 50 ? 'success' : 'warning'}
              />
              <Typography variant="body2">
                {signalStrength}%
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

// Main component
const SensorRealTimeDisplay = ({ farmId = 'farm1' }) => {
  const [previousReadings, setPreviousReadings] = useState(new Map());
  const [filterDeviceType, setFilterDeviceType] = useState('all');
  const [showOnlyActive, setShowOnlyActive] = useState(false);

  const {
    isRunning,
    latestReadings,
    deviceStatuses,
    stats,
    startRealtime,
    stopRealtime,
    clearData,
    updateInterval
  } = useRealtimeData({
    autoStart: true,
    updateInterval: 3000, // 3 seconds for real-time feel
    maxDataPoints: 200,
    farmId
  });

  // Track previous readings for trend calculation
  useEffect(() => {
    const newPreviousReadings = new Map();
    latestReadings.forEach(reading => {
      const previous = previousReadings.get(reading.device_id);
      if (previous) {
        newPreviousReadings.set(reading.device_id, previous);
      }
    });
    
    // Update previous readings with current readings
    setTimeout(() => {
      latestReadings.forEach(reading => {
        newPreviousReadings.set(reading.device_id, reading);
      });
      setPreviousReadings(newPreviousReadings);
    }, 1000);
  }, [latestReadings]);

  // Filter readings based on device type and status
  const filteredReadings = latestReadings.filter(reading => {
    if (filterDeviceType !== 'all' && reading.device_type !== filterDeviceType) {
      return false;
    }
    
    if (showOnlyActive) {
      const deviceStatus = deviceStatuses.find(status => status.device_id === reading.device_id);
      return deviceStatus?.status === 'active';
    }
    
    return true;
  });

  // Get unique device types for filter
  const deviceTypes = [...new Set(latestReadings.map(reading => reading.device_type))];

  const handleToggleRealtime = () => {
    if (isRunning) {
      stopRealtime();
    } else {
      startRealtime();
    }
  };

  return (
    <Box sx={{ p: { xs: 2, sm: 3 }, width: '100%' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          リアルタイムセンサー監視
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Chip
            icon={<SpeedIcon />}
            label={`更新間隔: ${updateInterval / 1000}秒`}
            variant="outlined"
          />
          <Button
            variant="contained"
            startIcon={isRunning ? <PauseIcon /> : <PlayIcon />}
            onClick={handleToggleRealtime}
            color={isRunning ? 'error' : 'success'}
          >
            {isRunning ? '停止' : '開始'}
          </Button>
          <Tooltip title="データをクリア">
            <IconButton onClick={clearData}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Stats Summary */}
      <Grid container spacing={{ xs: 1, sm: 2 }} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="primary">
                {stats.totalReadings}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                総データポイント数
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="success.main">
                {stats.activeDevices}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                稼働中デバイス
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="error.main">
                {stats.errorDevices}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                エラーデバイス
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="info.main">
                {stats.averageSignalStrength}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                平均信号強度
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters */}
      <Grid container spacing={{ xs: 1, sm: 2 }} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={4}>
          <FormControl fullWidth>
            <InputLabel>デバイスタイプ</InputLabel>
            <Select
              value={filterDeviceType}
              label="デバイスタイプ"
              onChange={(e) => setFilterDeviceType(e.target.value)}
            >
              <MenuItem value="all">すべて</MenuItem>
              {deviceTypes.map(type => (
                <MenuItem key={type} value={type}>
                  {type.replace('_sensor', '').replace('_', ' ')}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <FormControlLabel
            control={
              <Switch
                checked={showOnlyActive}
                onChange={(e) => setShowOnlyActive(e.target.checked)}
              />
            }
            label="稼働中のみ表示"
          />
        </Grid>
      </Grid>

      {/* Real-time Status */}
      {isRunning && (
        <Alert severity="info" sx={{ mb: 3 }}>
          リアルタイムデータ更新中... 次回更新まで {updateInterval / 1000} 秒
        </Alert>
      )}

      {/* Sensor Cards */}
      <Grid container spacing={{ xs: 2, sm: 3 }}>
        {filteredReadings.map((reading) => {
          const deviceStatus = deviceStatuses.find(status => status.device_id === reading.device_id);
          const previousReading = previousReadings.get(reading.device_id);
          
          return (
            <Grid item xs={12} sm={6} md={6} lg={4} xl={3} key={reading.device_id}>
              <SensorCard
                reading={reading}
                deviceStatus={deviceStatus}
                previousReading={previousReading}
              />
            </Grid>
          );
        })}
      </Grid>

      {filteredReadings.length === 0 && (
        <Alert severity="warning" sx={{ mt: 3 }}>
          フィルタ条件に一致するセンサーデータがありません。
        </Alert>
      )}
    </Box>
  );
};

export default SensorRealTimeDisplay;