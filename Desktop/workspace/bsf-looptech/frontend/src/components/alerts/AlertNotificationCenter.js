/**
 * Alert notification center with real-time WebSocket integration.
 * Displays alerts, manages notifications, and provides alert controls.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  IconButton,
  Badge,
  Drawer,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Chip,
  Button,
  Divider,
  Fab,
  Snackbar,
  Alert as MuiAlert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Switch,
  Slider,
  Select,
  MenuItem,
  FormControl,
  InputLabel
} from '@mui/material';
import {
  Notifications as NotificationsIcon,
  NotificationsActive as NotificationsActiveIcon,
  Close as CloseIcon,
  Check as CheckIcon,
  Clear as ClearIcon,
  Settings as SettingsIcon,
  VolumeUp as VolumeUpIcon,
  VolumeOff as VolumeOffIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  CrisisAlert as CriticalIcon
} from '@mui/icons-material';
import { useFarmWebSocket, MESSAGE_TYPES } from '../../hooks/useWebSocket';
import './AlertNotificationCenter.css';

// Severity icons mapping
const SEVERITY_ICONS = {
  info: InfoIcon,
  warning: WarningIcon,
  error: ErrorIcon,
  critical: CriticalIcon
};

// Severity colors
const SEVERITY_COLORS = {
  info: '#2196f3',
  warning: '#ff9800',
  error: '#f44336',
  critical: '#d32f2f'
};

// Sound effects for alerts (using Web Audio API)
const createAlertSound = (frequency, duration, type) => {
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const oscillator = audioContext.createOscillator();
  const gainNode = audioContext.createGain();

  oscillator.connect(gainNode);
  gainNode.connect(audioContext.destination);

  oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime);
  oscillator.type = type || 'sine';

  gainNode.gain.setValueAtTime(0, audioContext.currentTime);
  gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.01);
  gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);

  oscillator.start(audioContext.currentTime);
  oscillator.stop(audioContext.currentTime + duration);
};

const AlertNotificationCenter = ({ farmId, position = 'bottom-right' }) => {
  // Alert state
  const [alerts, setAlerts] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [currentAlert, setCurrentAlert] = useState(null);

  // Settings state
  const [settings, setSettings] = useState({
    soundEnabled: true,
    popupEnabled: true,
    autoAcknowledge: false,
    soundVolume: 0.5,
    maxAlerts: 50,
    severityFilter: 'all', // 'all', 'warning', 'error', 'critical'
    notificationDuration: 5000
  });

  // Refs
  const alertSoundsRef = useRef({
    info: () => createAlertSound(400, 0.3, 'sine'),
    warning: () => createAlertSound(600, 0.5, 'square'),
    error: () => createAlertSound(800, 0.7, 'triangle'),
    critical: () => {
      // Critical alert - multiple beeps
      createAlertSound(1000, 0.2, 'square');
      setTimeout(() => createAlertSound(1000, 0.2, 'square'), 300);
      setTimeout(() => createAlertSound(1000, 0.2, 'square'), 600);
    }
  });

  // WebSocket connection
  const {
    isConnected,
    addMessageHandler,
    subscribe
  } = useFarmWebSocket(farmId, {
    onConnect: () => {
      console.log(`Connected to farm ${farmId} for alert notifications`);
      subscribe({
        types: [MESSAGE_TYPES.ALERT, MESSAGE_TYPES.SYSTEM_STATUS],
        farm_id: farmId
      });
    }
  });

  // Handle incoming alerts
  const handleAlert = useCallback((message) => {
    const { data } = message;
    
    // Apply severity filter
    if (settings.severityFilter !== 'all' && data.severity !== settings.severityFilter) {
      return;
    }

    const newAlert = {
      ...data,
      receivedAt: new Date(),
      read: false,
      acknowledged: data.status === 'acknowledged'
    };

    setAlerts(prevAlerts => {
      const updatedAlerts = [newAlert, ...prevAlerts.slice(0, settings.maxAlerts - 1)];
      return updatedAlerts;
    });

    setUnreadCount(prev => prev + 1);

    // Show popup notification
    if (settings.popupEnabled) {
      setCurrentAlert(newAlert);
      setSnackbarOpen(true);
    }

    // Play sound notification
    if (settings.soundEnabled && alertSoundsRef.current[data.severity]) {
      try {
        alertSoundsRef.current[data.severity]();
      } catch (error) {
        console.warn('Could not play alert sound:', error);
      }
    }

    // Auto-acknowledge if enabled
    if (settings.autoAcknowledge && data.status === 'active') {
      setTimeout(() => {
        acknowledgeAlert(data.id);
      }, settings.notificationDuration);
    }

    // Browser notification (if permission granted)
    if (Notification.permission === 'granted') {
      new Notification(`BSF Alert - ${data.severity.toUpperCase()}`, {
        body: data.message,
        icon: '/favicon.ico',
        tag: data.id
      });
    }

  }, [settings, farmId]);

  // Handle system status updates
  const handleSystemStatus = useCallback((message) => {
    const { data } = message;
    
    if (data.alert_summary) {
      // Could show system alert summary
      console.log('Alert summary:', data.alert_summary);
    }
  }, []);

  // Set up WebSocket message handlers
  useEffect(() => {
    const cleanupHandlers = [
      addMessageHandler(MESSAGE_TYPES.ALERT, handleAlert),
      addMessageHandler(MESSAGE_TYPES.SYSTEM_STATUS, handleSystemStatus)
    ];

    return () => {
      cleanupHandlers.forEach(cleanup => cleanup());
    };
  }, [addMessageHandler, handleAlert, handleSystemStatus]);

  // Request notification permission on mount
  useEffect(() => {
    if (Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  // Load settings from localStorage
  useEffect(() => {
    const savedSettings = localStorage.getItem('alertSettings');
    if (savedSettings) {
      setSettings(prev => ({ ...prev, ...JSON.parse(savedSettings) }));
    }
  }, []);

  // Save settings to localStorage
  useEffect(() => {
    localStorage.setItem('alertSettings', JSON.stringify(settings));
  }, [settings]);

  // Mark alert as read
  const markAsRead = useCallback((alertId) => {
    setAlerts(prevAlerts => 
      prevAlerts.map(alert => 
        alert.id === alertId ? { ...alert, read: true } : alert
      )
    );
    setUnreadCount(prev => Math.max(0, prev - 1));
  }, []);

  // Acknowledge alert (would normally send to backend)
  const acknowledgeAlert = useCallback((alertId) => {
    setAlerts(prevAlerts => 
      prevAlerts.map(alert => 
        alert.id === alertId ? { ...alert, acknowledged: true } : alert
      )
    );
    // In real implementation, send acknowledgment to backend
    console.log(`Alert ${alertId} acknowledged`);
  }, []);

  // Dismiss alert
  const dismissAlert = useCallback((alertId) => {
    setAlerts(prevAlerts => prevAlerts.filter(alert => alert.id !== alertId));
  }, []);

  // Clear all alerts
  const clearAllAlerts = useCallback(() => {
    setAlerts([]);
    setUnreadCount(0);
  }, []);

  // Mark all as read
  const markAllAsRead = useCallback(() => {
    setAlerts(prevAlerts => 
      prevAlerts.map(alert => ({ ...alert, read: true }))
    );
    setUnreadCount(0);
  }, []);

  // Get alert icon
  const getAlertIcon = (severity) => {
    const IconComponent = SEVERITY_ICONS[severity] || InfoIcon;
    return <IconComponent style={{ color: SEVERITY_COLORS[severity] }} />;
  };

  // Format time
  const formatTime = (date) => {
    return new Intl.DateTimeFormat('ja-JP', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }).format(date);
  };

  // Filter alerts by severity
  const filteredAlerts = settings.severityFilter === 'all' 
    ? alerts 
    : alerts.filter(alert => alert.severity === settings.severityFilter);

  return (
    <>
      {/* Floating Action Button */}
      <Fab
        className={`alert-fab ${position}`}
        color={unreadCount > 0 ? 'error' : 'default'}
        onClick={() => setDrawerOpen(true)}
        sx={{
          position: 'fixed',
          bottom: position.includes('bottom') ? 20 : 'auto',
          top: position.includes('top') ? 20 : 'auto',
          right: position.includes('right') ? 20 : 'auto',
          left: position.includes('left') ? 20 : 'auto',
          zIndex: 1000
        }}
      >
        <Badge badgeContent={unreadCount} color="error" max={99}>
          {unreadCount > 0 ? <NotificationsActiveIcon /> : <NotificationsIcon />}
        </Badge>
      </Fab>

      {/* Alert Drawer */}
      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        PaperProps={{
          sx: { width: 400, maxWidth: '90vw' }
        }}
      >
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">
              アラート通知 ({filteredAlerts.length})
            </Typography>
            <Box>
              <IconButton 
                size="small" 
                onClick={() => setSettingsOpen(true)}
                title="設定"
              >
                <SettingsIcon />
              </IconButton>
              <IconButton 
                size="small" 
                onClick={() => setDrawerOpen(false)}
                title="閉じる"
              >
                <CloseIcon />
              </IconButton>
            </Box>
          </Box>
          
          <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
            <Button size="small" onClick={markAllAsRead} disabled={unreadCount === 0}>
              すべて既読
            </Button>
            <Button size="small" onClick={clearAllAlerts} disabled={alerts.length === 0}>
              すべて削除
            </Button>
          </Box>

          <FormControl size="small" sx={{ mt: 1, minWidth: 120 }}>
            <InputLabel>重要度フィルタ</InputLabel>
            <Select
              value={settings.severityFilter}
              label="重要度フィルタ"
              onChange={(e) => setSettings(prev => ({ ...prev, severityFilter: e.target.value }))}
            >
              <MenuItem value="all">すべて</MenuItem>
              <MenuItem value="info">情報</MenuItem>
              <MenuItem value="warning">警告</MenuItem>
              <MenuItem value="error">エラー</MenuItem>
              <MenuItem value="critical">重大</MenuItem>
            </Select>
          </FormControl>
        </Box>

        {/* Connection status */}
        <Box sx={{ px: 2, py: 1, bgcolor: isConnected ? 'success.light' : 'error.light' }}>
          <Typography variant="caption" color={isConnected ? 'success.contrastText' : 'error.contrastText'}>
            {isConnected ? '✓ リアルタイム接続中' : '⚠ 接続が切断されています'}
          </Typography>
        </Box>

        {/* Alert List */}
        <List sx={{ flexGrow: 1, overflow: 'auto' }}>
          {filteredAlerts.length === 0 ? (
            <ListItem>
              <ListItemText 
                primary="アラートはありません"
                secondary="すべて正常に動作しています"
                sx={{ textAlign: 'center', color: 'text.secondary' }}
              />
            </ListItem>
          ) : (
            filteredAlerts.map((alert, index) => (
              <React.Fragment key={alert.id}>
                <ListItem
                  className={`alert-item ${!alert.read ? 'unread' : ''}`}
                  sx={{
                    bgcolor: !alert.read ? 'action.hover' : 'transparent',
                    borderLeft: 4,
                    borderColor: SEVERITY_COLORS[alert.severity]
                  }}
                  onClick={() => markAsRead(alert.id)}
                >
                  <ListItemIcon>
                    {getAlertIcon(alert.severity)}
                  </ListItemIcon>
                  
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" sx={{ fontWeight: alert.read ? 'normal' : 'bold' }}>
                          {alert.device_id}
                        </Typography>
                        <Chip 
                          label={alert.severity} 
                          size="small" 
                          sx={{ 
                            bgcolor: SEVERITY_COLORS[alert.severity], 
                            color: 'white',
                            fontSize: '0.7rem'
                          }} 
                        />
                        {alert.acknowledged && (
                          <Chip label="確認済み" size="small" color="success" />
                        )}
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2" sx={{ mb: 0.5 }}>
                          {alert.message}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {formatTime(new Date(alert.created_at))} • {alert.measurement_type}
                        </Typography>
                      </Box>
                    }
                  />
                  
                  <ListItemSecondaryAction>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      {!alert.acknowledged && (
                        <IconButton 
                          size="small" 
                          onClick={(e) => {
                            e.stopPropagation();
                            acknowledgeAlert(alert.id);
                          }}
                          title="確認"
                        >
                          <CheckIcon fontSize="small" />
                        </IconButton>
                      )}
                      <IconButton 
                        size="small" 
                        onClick={(e) => {
                          e.stopPropagation();
                          dismissAlert(alert.id);
                        }}
                        title="削除"
                      >
                        <ClearIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  </ListItemSecondaryAction>
                </ListItem>
                {index < filteredAlerts.length - 1 && <Divider />}
              </React.Fragment>
            ))
          )}
        </List>
      </Drawer>

      {/* Settings Dialog */}
      <Dialog open={settingsOpen} onClose={() => setSettingsOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>アラート設定</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.soundEnabled}
                  onChange={(e) => setSettings(prev => ({ ...prev, soundEnabled: e.target.checked }))}
                />
              }
              label="音声通知を有効にする"
            />
            
            <FormControlLabel
              control={
                <Switch
                  checked={settings.popupEnabled}
                  onChange={(e) => setSettings(prev => ({ ...prev, popupEnabled: e.target.checked }))}
                />
              }
              label="ポップアップ通知を有効にする"
            />
            
            <FormControlLabel
              control={
                <Switch
                  checked={settings.autoAcknowledge}
                  onChange={(e) => setSettings(prev => ({ ...prev, autoAcknowledge: e.target.checked }))}
                />
              }
              label="自動確認を有効にする"
            />

            <Box sx={{ mt: 2, mb: 2 }}>
              <Typography gutterBottom>音量</Typography>
              <Slider
                value={settings.soundVolume}
                onChange={(e, value) => setSettings(prev => ({ ...prev, soundVolume: value }))}
                min={0}
                max={1}
                step={0.1}
                marks
                valueLabelDisplay="auto"
                disabled={!settings.soundEnabled}
              />
            </Box>

            <Box sx={{ mt: 2, mb: 2 }}>
              <Typography gutterBottom>最大アラート数</Typography>
              <Slider
                value={settings.maxAlerts}
                onChange={(e, value) => setSettings(prev => ({ ...prev, maxAlerts: value }))}
                min={10}
                max={100}
                step={10}
                marks
                valueLabelDisplay="auto"
              />
            </Box>

            <Box sx={{ mt: 2, mb: 2 }}>
              <Typography gutterBottom>通知表示時間 (ミリ秒)</Typography>
              <Slider
                value={settings.notificationDuration}
                onChange={(e, value) => setSettings(prev => ({ ...prev, notificationDuration: value }))}
                min={1000}
                max={10000}
                step={1000}
                marks
                valueLabelDisplay="auto"
              />
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSettingsOpen(false)}>閉じる</Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for popup notifications */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={settings.notificationDuration}
        onClose={() => setSnackbarOpen(false)}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        {currentAlert && (
          <MuiAlert 
            onClose={() => setSnackbarOpen(false)}
            severity={currentAlert.severity === 'critical' ? 'error' : currentAlert.severity}
            sx={{ width: '100%' }}
            action={
              <IconButton
                size="small"
                color="inherit"
                onClick={() => acknowledgeAlert(currentAlert.id)}
              >
                <CheckIcon fontSize="small" />
              </IconButton>
            }
          >
            <Typography variant="body2" fontWeight="bold">
              {currentAlert.device_id} - {currentAlert.measurement_type}
            </Typography>
            <Typography variant="body2">
              {currentAlert.message}
            </Typography>
          </MuiAlert>
        )}
      </Snackbar>
    </>
  );
};

export default AlertNotificationCenter;