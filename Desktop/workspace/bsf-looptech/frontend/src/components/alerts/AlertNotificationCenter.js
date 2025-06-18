import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  Badge,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Button,
  Typography,
  Box,
  Chip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Drawer,
  Tooltip,
  CircularProgress,
  Grid,
  Paper,
  IconButton,
  Divider,
  Snackbar,
  Pagination
} from '@mui/material';
import {
  Notifications as BellIcon,
  Error as ExclamationCircleIcon,
  Warning as WarningIcon,
  Info as InfoCircleIcon,
  CheckCircle as CheckCircleIcon,
  AccessTime as ClockCircleIcon,
  Close as CloseIcon,
  Visibility as EyeIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';
import { useDataContext } from '../../contexts/OptimizedDataContext';
import websocketService from '../../services/websocketService';
import AlertTestingPanel from './AlertTestingPanel';
import MQTTTestPanel from './MQTTTestPanel';
import './AlertNotificationCenter.css';

// アラート重要度のアイコンと色
const SEVERITY_CONFIG = {
  info: {
    icon: <InfoCircleIcon />,
    color: 'info',
    bgColor: '#e3f2fd',
    borderColor: '#2196f3'
  },
  warning: {
    icon: <WarningIcon />,
    color: 'warning',
    bgColor: '#fff3e0',
    borderColor: '#ff9800'
  },
  error: {
    icon: <ExclamationCircleIcon />,
    color: 'error',
    bgColor: '#ffebee',
    borderColor: '#f44336'
  },
  critical: {
    icon: <ExclamationCircleIcon />,
    color: 'error',
    bgColor: '#ffebee',
    borderColor: '#d32f2f',
    animation: 'pulse'
  }
};

// アラート状態の設定
const STATUS_CONFIG = {
  active: {
    label: 'アクティブ',
    color: 'error',
    icon: <ExclamationCircleIcon />
  },
  acknowledged: {
    label: '確認済み',
    color: 'warning',
    icon: <EyeIcon />
  },
  resolved: {
    label: '解決済み',
    color: 'success',
    icon: <CheckCircleIcon />
  },
  dismissed: {
    label: '無視',
    color: 'default',
    icon: <CloseIcon />
  }
};

const AlertNotificationCenter = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [filter, setFilter] = useState('all');
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [confirmDialog, setConfirmDialog] = useState({ open: false, alertId: null });
  const { state } = useDataContext();
  const [connectionStatus, setConnectionStatus] = useState({ isConnected: false });
  const [showTestPanel, setShowTestPanel] = useState(process.env.NODE_ENV === 'development');
  const [showMQTTPanel, setShowMQTTPanel] = useState(process.env.NODE_ENV === 'development');

  // デモ用のアラートデータとWebSocket接続を初期化
  useEffect(() => {
    loadDemoAlerts();
    
    // ブラウザ通知の許可を求める
    requestNotificationPermission();
    
    // WebSocket接続を開始
    websocketService.connect();
    
    // アラートイベントリスナーを設定
    const unsubscribeAlert = websocketService.on('alert', handleNewAlert);
    const unsubscribeUpdate = websocketService.on('alert_update', handleAlertUpdate);
    const unsubscribeConnected = websocketService.on('connected', handleWebSocketConnected);
    const unsubscribeDisconnected = websocketService.on('disconnected', handleWebSocketDisconnected);
    
    // アラートの購読
    websocketService.subscribeToAlerts('farm1'); // farm1のアラートを購読
    
    return () => {
      unsubscribeAlert();
      unsubscribeUpdate();
      unsubscribeConnected();
      unsubscribeDisconnected();
      websocketService.disconnect();
    };
  }, []);

  const loadDemoAlerts = () => {
    const demoAlerts = [
      {
        id: 'alert_20250616_142330_GAS-001_high',
        rule_id: 'threshold_002',
        farm_id: 'farm1',
        device_id: 'GAS-001',
        measurement_type: 'h2s',
        severity: 'critical',
        status: 'active',
        threshold_value: 3.0,
        actual_value: 3.2,
        unit: 'ppm',
        message: 'H2S危険レベル: h2s high threshold violation. Value: 3.2 ppm, Threshold: 3.0 ppm',
        created_at: new Date(Date.now() - 300000).toISOString(), // 5分前
        updated_at: new Date(Date.now() - 300000).toISOString(),
        metadata: {
          violation_type: 'high',
          rule_name: 'H2S危険レベル',
          location: 'エリアA-1',
          substrate_batch_id: 'batch001'
        }
      },
      {
        id: 'alert_20250616_141500_TEMP-001_high',
        rule_id: 'threshold_001',
        farm_id: 'farm1',
        device_id: 'TEMP-001',
        measurement_type: 'temperature',
        severity: 'warning',
        status: 'acknowledged',
        threshold_value: 32.0,
        actual_value: 33.1,
        unit: '°C',
        message: '温度高温警告: temperature high threshold violation. Value: 33.1 °C, Threshold: 32.0 °C',
        created_at: new Date(Date.now() - 1800000).toISOString(), // 30分前
        updated_at: new Date(Date.now() - 900000).toISOString(), // 15分前
        acknowledged_by: 'admin',
        acknowledged_at: new Date(Date.now() - 900000).toISOString(),
        metadata: {
          violation_type: 'high',
          rule_name: '温度高温警告',
          location: 'エリアA-1',
          substrate_batch_id: 'batch001'
        }
      },
      {
        id: 'alert_20250616_140000_HUM-001_low',
        rule_id: 'threshold_003',
        farm_id: 'farm1',
        device_id: 'HUM-001',
        measurement_type: 'humidity',
        severity: 'warning',
        status: 'resolved',
        threshold_value: 40.0,
        actual_value: 38.5,
        unit: '%RH',
        message: '湿度低下警告: humidity low threshold violation. Value: 38.5 %RH, Threshold: 40.0 %RH',
        created_at: new Date(Date.now() - 3600000).toISOString(), // 1時間前
        updated_at: new Date(Date.now() - 1800000).toISOString(), // 30分前
        resolved_at: new Date(Date.now() - 1800000).toISOString(),
        metadata: {
          violation_type: 'low',
          rule_name: '湿度低下警告',
          location: 'エリアA-2',
          substrate_batch_id: 'batch002',
          resolved_by: 'automatic',
          resolution_reason: 'Value returned to normal range'
        }
      }
    ];
    
    setAlerts(demoAlerts);
    setLoading(false);
  };

  const handleNewAlert = (newAlert) => {
    setAlerts(prev => [newAlert, ...prev]);
    
    // 重要度が高い場合は通知音を鳴らす
    if (newAlert.severity === 'critical' || newAlert.severity === 'error') {
      playNotificationSound();
    }
    
    // ブラウザ通知
    if (Notification.permission === 'granted') {
      new Notification(`BSF Alert: ${newAlert.message}`, {
        icon: '/favicon.ico',
        badge: '/favicon.ico'
      });
    }
    
    showSnackbar(`新しい${newAlert.severity}アラート: ${newAlert.metadata?.rule_name}`);
  };

  const handleAlertUpdate = (updatedAlert) => {
    setAlerts(prev => 
      prev.map(alert => 
        alert.id === updatedAlert.id ? { ...alert, ...updatedAlert } : alert
      )
    );
  };

  const handleWebSocketConnected = () => {
    setConnectionStatus({ isConnected: true });
    showSnackbar('リアルタイム通知に接続しました');
  };

  const handleWebSocketDisconnected = () => {
    setConnectionStatus({ isConnected: false });
    showSnackbar('リアルタイム通知から切断されました');
  };

  const requestNotificationPermission = async () => {
    if ('Notification' in window && Notification.permission === 'default') {
      try {
        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
          showSnackbar('ブラウザ通知が有効になりました');
        }
      } catch (error) {
        console.error('Failed to request notification permission:', error);
      }
    }
  };

  const playNotificationSound = () => {
    // 通知音を再生（ブラウザ対応）
    const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+L');
    audio.play().catch(() => {
      // 自動再生がブロックされた場合は無視
    });
  };

  const getFilteredAlerts = () => {
    if (filter === 'all') return alerts;
    return alerts.filter(alert => {
      switch (filter) {
        case 'active':
          return alert.status === 'active';
        case 'critical':
          return alert.severity === 'critical';
        case 'today':
          return new Date(alert.created_at) > new Date(Date.now() - 24 * 60 * 60 * 1000);
        default:
          return true;
      }
    });
  };

  const getAlertStats = () => {
    return {
      total: alerts.length,
      active: alerts.filter(a => a.status === 'active').length,
      critical: alerts.filter(a => a.severity === 'critical').length,
      warning: alerts.filter(a => a.severity === 'warning').length
    };
  };

  const handleAcknowledgeAlert = async (alertId) => {
    try {
      // WebSocketでバックエンドに送信
      websocketService.acknowledgeAlert(alertId);
      
      // 楽観的更新
      setAlerts(prev => prev.map(alert => 
        alert.id === alertId 
          ? {
              ...alert,
              status: 'acknowledged',
              acknowledged_by: 'current_user',
              acknowledged_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            }
          : alert
      ));
      showSnackbar('アラートを確認済みにしました');
    } catch (error) {
      showSnackbar('アラートの確認に失敗しました');
    }
  };

  const handleDismissAlert = async (alertId) => {
    try {
      // WebSocketでバックエンドに送信
      websocketService.dismissAlert(alertId);
      
      // 楽観的更新
      setAlerts(prev => prev.map(alert => 
        alert.id === alertId 
          ? {
              ...alert,
              status: 'dismissed',
              updated_at: new Date().toISOString()
            }
          : alert
      ));
      showSnackbar('アラートを無視しました');
      setConfirmDialog({ open: false, alertId: null });
    } catch (error) {
      showSnackbar('アラートの無視に失敗しました');
    }
  };

  const showSnackbar = (message) => {
    setSnackbarMessage(message);
    setSnackbarOpen(true);
  };

  const formatTimeAgo = (timestamp) => {
    const now = new Date();
    const alertTime = new Date(timestamp);
    const diffMs = now - alertTime;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return '今すぐ';
    if (diffMins < 60) return `${diffMins}分前`;
    if (diffHours < 24) return `${diffHours}時間前`;
    return `${diffDays}日前`;
  };

  const renderAlertItem = (alert) => {
    const severityConfig = SEVERITY_CONFIG[alert.severity];
    const statusConfig = STATUS_CONFIG[alert.status];

    return (
      <ListItem
        key={alert.id}
        className={`alert-item alert-${alert.severity} ${alert.status === 'active' ? 'alert-active' : ''}`}
        sx={{
          backgroundColor: severityConfig.bgColor,
          borderLeft: `4px solid ${severityConfig.borderColor}`,
          mb: 1,
          borderRadius: 1
        }}
      >
        <ListItemIcon sx={{ fontSize: 24, color: severityConfig.borderColor }}>
          {severityConfig.icon}
        </ListItemIcon>
        <ListItemText
          primary={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="subtitle1" fontWeight="bold">
                {alert.metadata?.rule_name || alert.measurement_type}
              </Typography>
              <Chip
                label={statusConfig.label}
                color={statusConfig.color}
                size="small"
                icon={statusConfig.icon}
              />
              <Chip
                label={alert.severity.toUpperCase()}
                color={severityConfig.color}
                size="small"
              />
            </Box>
          }
          secondary={
            <Box>
              <Typography variant="body2" sx={{ mb: 1 }}>
                {alert.message}
              </Typography>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  <ClockCircleIcon sx={{ fontSize: 14, mr: 0.5, verticalAlign: 'middle' }} />
                  {formatTimeAgo(alert.created_at)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  デバイス: {alert.device_id}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  場所: {alert.metadata?.location}
                </Typography>
              </Box>
            </Box>
          }
        />
        <ListItemSecondaryAction>
          {alert.status === 'active' && (
            <>
              <Tooltip title="確認済みにする">
                <IconButton onClick={() => handleAcknowledgeAlert(alert.id)}>
                  <EyeIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="無視する">
                <IconButton 
                  color="error" 
                  onClick={() => setConfirmDialog({ open: true, alertId: alert.id })}
                >
                  <CloseIcon />
                </IconButton>
              </Tooltip>
            </>
          )}
          <Button
            size="small"
            onClick={() => {
              setSelectedAlert(alert);
              setDrawerOpen(true);
            }}
          >
            詳細
          </Button>
        </ListItemSecondaryAction>
      </ListItem>
    );
  };

  const stats = getAlertStats();
  const filteredAlerts = getFilteredAlerts();
  const itemsPerPage = 10;
  const pageCount = Math.ceil(filteredAlerts.length / itemsPerPage);
  const displayedAlerts = filteredAlerts.slice((page - 1) * itemsPerPage, page * itemsPerPage);

  return (
    <Box className="alert-notification-center">
      {/* 開発用テストパネル */}
      {showTestPanel && (
        <Box sx={{ mb: 2 }}>
          <AlertTestingPanel />
        </Box>
      )}
      
      {/* MQTT テストパネル */}
      {showMQTTPanel && (
        <Box sx={{ mb: 2 }}>
          <MQTTTestPanel />
        </Box>
      )}
      
      {/* アラート統計 */}
      <div className="alert-stats-grid">
        <Paper sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="body2" color="text.secondary">
              総アラート数
            </Typography>
            <BellIcon color="action" />
          </Box>
          <Typography variant="h4">{stats.total}</Typography>
        </Paper>
        <Paper sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="body2" color="text.secondary">
              アクティブ
            </Typography>
            <ExclamationCircleIcon color="error" />
          </Box>
          <Typography variant="h4" color="error">
            {stats.active}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="body2" color="text.secondary">
              重大
            </Typography>
            <ExclamationCircleIcon color="error" />
          </Box>
          <Typography variant="h4" color="error">
            {stats.critical}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="body2" color="text.secondary">
              警告
            </Typography>
            <WarningIcon color="warning" />
          </Box>
          <Typography variant="h4" color="warning.main">
            {stats.warning}
          </Typography>
        </Paper>
      </div>

      {/* フィルターボタン */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box className="alert-filters">
            <Button
              variant={filter === 'all' ? 'contained' : 'outlined'}
              onClick={() => setFilter('all')}
            >
              すべて
            </Button>
            <Button
              variant={filter === 'active' ? 'contained' : 'outlined'}
              onClick={() => setFilter('active')}
            >
              アクティブ
            </Button>
            <Button
              variant={filter === 'critical' ? 'contained' : 'outlined'}
              onClick={() => setFilter('critical')}
            >
              重大
            </Button>
            <Button
              variant={filter === 'today' ? 'contained' : 'outlined'}
              onClick={() => setFilter('today')}
            >
              今日
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* アラートリスト */}
      <Card>
        <CardHeader
          title={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <BellIcon />
              <Typography variant="h5">
                アラート通知
              </Typography>
              <Badge badgeContent={stats.active} color="error" />
              <Chip
                label={connectionStatus.isConnected ? 'リアルタイム接続中' : 'オフライン'}
                color={connectionStatus.isConnected ? 'success' : 'default'}
                size="small"
                sx={{ ml: 1 }}
              />
            </Box>
          }
        />
        <CardContent>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : displayedAlerts.length > 0 ? (
            <>
              <List>
                {displayedAlerts.map(alert => renderAlertItem(alert))}
              </List>
              {pageCount > 1 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                  <Pagination
                    count={pageCount}
                    page={page}
                    onChange={(e, value) => setPage(value)}
                    color="primary"
                  />
                </Box>
              )}
            </>
          ) : (
            <Box sx={{ textAlign: 'center', py: 5 }}>
              <Typography variant="body1" color="text.secondary">
                アラートはありません
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* アラート詳細ドロワー */}
      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        sx={{ 
          '& .MuiDrawer-paper': { 
            width: { xs: '100vw', sm: 500 },
            maxWidth: '100vw'
          } 
        }}
        className="alert-drawer-mobile"
      >
        {selectedAlert && (
          <Box className="alert-drawer-content">
            <Typography variant="h5" gutterBottom>
              アラート詳細
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                {selectedAlert.metadata?.rule_name}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                <Chip
                  label={selectedAlert.severity.toUpperCase()}
                  color={SEVERITY_CONFIG[selectedAlert.severity].color}
                />
                <Chip
                  label={STATUS_CONFIG[selectedAlert.status].label}
                  color={STATUS_CONFIG[selectedAlert.status].color}
                />
              </Box>
            </Box>

            <Alert 
              severity={selectedAlert.severity === 'critical' ? 'error' : selectedAlert.severity}
              sx={{ mb: 3 }}
            >
              {selectedAlert.message}
            </Alert>

            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                基本情報
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    デバイスID:
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    {selectedAlert.device_id}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    測定タイプ:
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    {selectedAlert.measurement_type}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    場所:
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    {selectedAlert.metadata?.location}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    バッチID:
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    {selectedAlert.metadata?.substrate_batch_id}
                  </Typography>
                </Grid>
              </Grid>
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                閾値情報
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    閾値:
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    {selectedAlert.threshold_value} {selectedAlert.unit}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    実測値:
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="error" fontWeight="bold">
                    {selectedAlert.actual_value} {selectedAlert.unit}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    違反タイプ:
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    {selectedAlert.metadata?.violation_type === 'high' ? '上限超過' : '下限下回り'}
                  </Typography>
                </Grid>
              </Grid>
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                タイムライン
              </Typography>
              <Box sx={{ pl: 2 }}>
                <Typography variant="body2" color="error" fontWeight="bold">
                  アラート発生
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {new Date(selectedAlert.created_at).toLocaleString()}
                </Typography>
                {selectedAlert.acknowledged_at && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="body2" color="warning.main" fontWeight="bold">
                      確認済み
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(selectedAlert.acknowledged_at).toLocaleString()}
                      {selectedAlert.acknowledged_by && ` by ${selectedAlert.acknowledged_by}`}
                    </Typography>
                  </Box>
                )}
                {selectedAlert.resolved_at && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="body2" color="success.main" fontWeight="bold">
                      解決済み
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(selectedAlert.resolved_at).toLocaleString()}
                      {selectedAlert.metadata?.resolved_by && ` by ${selectedAlert.metadata.resolved_by}`}
                    </Typography>
                    {selectedAlert.metadata?.resolution_reason && (
                      <Typography variant="caption" display="block" color="text.secondary">
                        {selectedAlert.metadata.resolution_reason}
                      </Typography>
                    )}
                  </Box>
                )}
              </Box>
            </Box>

            {selectedAlert.status === 'active' && (
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="contained"
                  onClick={() => {
                    handleAcknowledgeAlert(selectedAlert.id);
                    setDrawerOpen(false);
                  }}
                >
                  確認済みにする
                </Button>
                <Button
                  variant="outlined"
                  color="error"
                  onClick={() => {
                    handleDismissAlert(selectedAlert.id);
                    setDrawerOpen(false);
                  }}
                >
                  無視する
                </Button>
              </Box>
            )}
          </Box>
        )}
      </Drawer>

      {/* 確認ダイアログ */}
      <Dialog
        open={confirmDialog.open}
        onClose={() => setConfirmDialog({ open: false, alertId: null })}
      >
        <DialogTitle>アラートを無視しますか？</DialogTitle>
        <DialogContent>
          <Typography>
            このアラートを無視すると、通知されなくなります。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialog({ open: false, alertId: null })}>
            キャンセル
          </Button>
          <Button
            onClick={() => handleDismissAlert(confirmDialog.alertId)}
            color="error"
          >
            無視
          </Button>
        </DialogActions>
      </Dialog>

      {/* スナックバー */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={() => setSnackbarOpen(false)}
        message={snackbarMessage}
      />
    </Box>
  );
};

export default AlertNotificationCenter;