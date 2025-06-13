/**
 * Integrated real-time dashboard page.
 * Combines real-time sensor display, charts, and alert notifications.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Typography,
  Card,
  CardContent,
  CardHeader,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Button,
  Chip,
  IconButton,
  Tooltip,
  Divider
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  Fullscreen as FullscreenIcon,
  FullscreenExit as FullscreenExitIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon
} from '@mui/icons-material';
import SensorRealTimeDisplay from '../sensors/SensorRealTimeDisplay';
import SensorChartsRealTime from '../sensors/SensorChartsRealTime';
import AlertNotificationCenter from '../alerts/AlertNotificationCenter';
import { useFarmWebSocket, MESSAGE_TYPES } from '../../hooks/useWebSocket';

const RealTimeDashboard = () => {
  // State management
  const [selectedFarm, setSelectedFarm] = useState('farm001'); // Default farm
  const [dashboardSettings, setDashboardSettings] = useState({
    autoRefresh: true,
    refreshInterval: 5000,
    showAlerts: true,
    showCharts: true,
    showDeviceStatus: true,
    chartHeight: 400,
    fullscreen: false
  });
  const [isPaused, setIsPaused] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  
  // Available farms (in real app, this would come from API)
  const [availableFarms, setAvailableFarms] = useState([
    { id: 'farm001', name: 'メインファーム', location: '東京都' },
    { id: 'farm002', name: 'サブファーム', location: '神奈川県' },
    { id: 'farm003', name: 'テストファーム', location: '埼玉県' }
  ]);

  // Dashboard stats
  const [dashboardStats, setDashboardStats] = useState({
    connectedDevices: 0,
    totalAlerts: 0,
    dataPoints: 0,
    uptime: 0
  });

  // WebSocket connection for dashboard
  const {
    isConnected,
    connectionState,
    stats,
    getConnectionInfo
  } = useFarmWebSocket(selectedFarm, {
    onConnect: () => {
      console.log(`Dashboard connected to farm ${selectedFarm}`);
      setLastRefresh(new Date());
    },
    onMessage: (message) => {
      // Update dashboard stats based on incoming messages
      if (message.message_type === MESSAGE_TYPES.SENSOR_DATA) {
        setDashboardStats(prev => ({
          ...prev,
          dataPoints: prev.dataPoints + 1
        }));
      }
    }
  });

  // Auto-refresh functionality
  useEffect(() => {
    if (!dashboardSettings.autoRefresh || isPaused) return;

    const interval = setInterval(() => {
      setLastRefresh(new Date());
      // Force refresh of components by updating a counter or similar
      setDashboardStats(prev => ({ ...prev, uptime: prev.uptime + 1 }));
    }, dashboardSettings.refreshInterval);

    return () => clearInterval(interval);
  }, [dashboardSettings.autoRefresh, dashboardSettings.refreshInterval, isPaused]);

  // Handle farm selection change
  const handleFarmChange = (event) => {
    setSelectedFarm(event.target.value);
    setLastRefresh(new Date());
  };

  // Toggle fullscreen
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setDashboardSettings(prev => ({ ...prev, fullscreen: true }));
    } else {
      document.exitFullscreen();
      setDashboardSettings(prev => ({ ...prev, fullscreen: false }));
    }
  };

  // Handle settings change
  const handleSettingChange = (setting, value) => {
    setDashboardSettings(prev => ({
      ...prev,
      [setting]: value
    }));
  };

  // Manual refresh
  const handleRefresh = () => {
    setLastRefresh(new Date());
    // Could trigger refresh events to child components
  };

  // Pause/Resume
  const togglePause = () => {
    setIsPaused(!isPaused);
  };

  // Connection status color
  const getConnectionStatusColor = () => {
    switch (connectionState) {
      case 'connected': return 'success';
      case 'connecting': case 'reconnecting': return 'warning';
      case 'disconnected': case 'error': return 'error';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ p: 2, minHeight: '100vh', bgcolor: '#f5f5f5' }}>
      {/* Dashboard Header */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h4" component="h1" gutterBottom>
              BSF リアルタイムダッシュボード
            </Typography>
            
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Chip 
                label={connectionState}
                color={getConnectionStatusColor()}
                size="small"
              />
              
              <Tooltip title={isPaused ? "再開" : "一時停止"}>
                <IconButton onClick={togglePause} color={isPaused ? "error" : "primary"}>
                  {isPaused ? <PlayIcon /> : <PauseIcon />}
                </IconButton>
              </Tooltip>
              
              <Tooltip title="手動更新">
                <IconButton onClick={handleRefresh}>
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
              
              <Tooltip title={dashboardSettings.fullscreen ? "全画面終了" : "全画面表示"}>
                <IconButton onClick={toggleFullscreen}>
                  {dashboardSettings.fullscreen ? <FullscreenExitIcon /> : <FullscreenIcon />}
                </IconButton>
              </Tooltip>
            </Box>
          </Box>

          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>ファーム選択</InputLabel>
                <Select
                  value={selectedFarm}
                  label="ファーム選択"
                  onChange={handleFarmChange}
                >
                  {availableFarms.map(farm => (
                    <MenuItem key={farm.id} value={farm.id}>
                      {farm.name} ({farm.location})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <FormControlLabel
                control={
                  <Switch
                    checked={dashboardSettings.autoRefresh}
                    onChange={(e) => handleSettingChange('autoRefresh', e.target.checked)}
                    size="small"
                  />
                }
                label="自動更新"
              />
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <FormControlLabel
                control={
                  <Switch
                    checked={dashboardSettings.showAlerts}
                    onChange={(e) => handleSettingChange('showAlerts', e.target.checked)}
                    size="small"
                  />
                }
                label="アラート表示"
              />
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="caption" color="textSecondary">
                最終更新: {lastRefresh.toLocaleTimeString()}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Dashboard Stats */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="primary">
                {stats?.messagesReceived || 0}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                受信メッセージ数
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="success.main">
                {isConnected ? '接続中' : '切断'}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                接続状態
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="info.main">
                {dashboardStats.dataPoints}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                データポイント数
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="warning.main">
                {Math.floor(dashboardStats.uptime / 60)}m
              </Typography>
              <Typography variant="body2" color="textSecondary">
                稼働時間
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Main Dashboard Content */}
      <Grid container spacing={2}>
        {/* Real-time Sensor Display */}
        <Grid item xs={12} lg={6}>
          <Card>
            <CardHeader 
              title="リアルタイムセンサーデータ"
              action={
                <FormControlLabel
                  control={
                    <Switch
                      checked={dashboardSettings.showDeviceStatus}
                      onChange={(e) => handleSettingChange('showDeviceStatus', e.target.checked)}
                      size="small"
                    />
                  }
                  label="デバイス状態"
                />
              }
            />
            <CardContent sx={{ height: 600, overflow: 'auto' }}>
              <SensorRealTimeDisplay 
                farmId={selectedFarm}
                showAlerts={dashboardSettings.showAlerts}
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Real-time Charts */}
        {dashboardSettings.showCharts && (
          <Grid item xs={12} lg={6}>
            <Card>
              <CardHeader 
                title="リアルタイムチャート"
                action={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="caption">高さ:</Typography>
                    <Select
                      value={dashboardSettings.chartHeight}
                      onChange={(e) => handleSettingChange('chartHeight', e.target.value)}
                      size="small"
                      sx={{ minWidth: 80 }}
                    >
                      <MenuItem value={300}>小</MenuItem>
                      <MenuItem value={400}>中</MenuItem>
                      <MenuItem value={500}>大</MenuItem>
                    </Select>
                  </Box>
                }
              />
              <CardContent sx={{ height: dashboardSettings.chartHeight + 200, overflow: 'auto' }}>
                <SensorChartsRealTime 
                  farmId={selectedFarm}
                  maxDataPoints={100}
                />
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* System Information */}
        <Grid item xs={12}>
          <Card>
            <CardHeader title="システム情報" />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>接続情報</Typography>
                  <Box sx={{ pl: 2 }}>
                    <Typography variant="body2">
                      ファーム: {availableFarms.find(f => f.id === selectedFarm)?.name}
                    </Typography>
                    <Typography variant="body2">
                      WebSocket URL: ws://localhost:8000/ws/farm/{selectedFarm}
                    </Typography>
                    <Typography variant="body2">
                      接続状態: {connectionState}
                    </Typography>
                    <Typography variant="body2">
                      最終接続: {stats?.lastConnectedAt ? new Date(stats.lastConnectedAt).toLocaleString() : 'なし'}
                    </Typography>
                  </Box>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>統計情報</Typography>
                  <Box sx={{ pl: 2 }}>
                    <Typography variant="body2">
                      受信メッセージ: {stats?.messagesReceived || 0}
                    </Typography>
                    <Typography variant="body2">
                      送信メッセージ: {stats?.messagesSent || 0}
                    </Typography>
                    <Typography variant="body2">
                      接続試行回数: {stats?.connectionAttempts || 0}
                    </Typography>
                    <Typography variant="body2">
                      ダッシュボード稼働: {Math.floor(dashboardStats.uptime / 60)}分
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Alert Notification Center */}
      {dashboardSettings.showAlerts && (
        <AlertNotificationCenter 
          farmId={selectedFarm}
          position="bottom-right"
        />
      )}
    </Box>
  );
};

export default RealTimeDashboard;