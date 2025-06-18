import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { 
  Container, 
  AppBar, 
  Toolbar, 
  Typography, 
  Tabs, 
  Tab, 
  Box,
  Menu,
  MenuItem,
  IconButton
} from '@mui/material';
import { AccountCircle } from '@mui/icons-material';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { OptimizedDataProvider } from './contexts/OptimizedDataContext';
import LoginForm from './components/auth/LoginForm';
import PrivateRoute from './components/auth/PrivateRoute';
import SubstrateTypeForm from './components/substrate/SubstrateTypeForm.js';
import SubstrateBatchForm from './components/substrate/SubstrateBatchForm.js';
import SubstrateTypeList from './components/substrate/SubstrateTypeList.js';
import SubstrateBatchList from './components/substrate/SubstrateBatchList.js';
import SensorReadingsList from './components/sensors/SensorReadingsList.js';
import SensorDeviceList from './components/sensors/SensorDeviceList.js';
import SensorRealTimeDisplay from './components/sensors/SensorRealTimeDisplay.js';
import SensorChartsRealTime from './components/sensors/SensorChartsRealTime.js';
import RealTimeDashboard from './components/dashboard/RealTimeDashboard.js';
import AnalyticsDashboard from './components/analytics/AnalyticsDashboard.js';
import CorrelationAnalysis from './components/analytics/CorrelationAnalysis.js';
import AlertSettings from './components/alerts/AlertSettings.js';
import AlertHistory from './components/alerts/AlertHistory.js';
import NotificationSettings from './components/alerts/NotificationSettings.js';
import ThresholdSettings from './components/alerts/ThresholdSettings.js';
import AlertNotificationCenter from './components/alerts/AlertNotificationCenter.js';
import BatchComparison from './components/batch/BatchComparison.js';
import ProfitabilityDashboard from './components/batch/ProfitabilityDashboard.js';
import FeedEfficiencyTracker from './components/batch/FeedEfficiencyTracker.js';

// Main Dashboard Component
const Dashboard = () => {
  const [selectedTab, setSelectedTab] = useState(0);
  const [editingSubstrateType, setEditingSubstrateType] = useState(null);
  const [editingSubstrateBatch, setEditingSubstrateBatch] = useState(null);
  const [anchorEl, setAnchorEl] = useState(null);
  
  const { user, logout } = useAuth();

  const handleTabChange = (_, newValue) => {
    setSelectedTab(newValue);
    // タブ切り替え時に編集状態をリセット
    setEditingSubstrateType(null);
    setEditingSubstrateBatch(null);
  };

  const handleEditSubstrateType = (substrateType) => {
    setEditingSubstrateType(substrateType);
    setSelectedTab(5); // 基質タイプ登録タブに切り替え
  };

  const handleEditSubstrateBatch = (substrateBatch) => {
    setEditingSubstrateBatch(substrateBatch);
    setSelectedTab(6); // 基質バッチ登録タブに切り替え
  };
  

  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    handleMenuClose();
    logout();
  };

  return (
    <Container maxWidth="xl" sx={{ px: { xs: 2, sm: 3, md: 4, lg: 5 } }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            BSF幼虫養殖環境管理システム
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Typography variant="body2" sx={{ mr: 2 }}>
              {user?.username} ({user?.role})
            </Typography>
            <IconButton
              size="large"
              edge="end"
              aria-label="account of current user"
              aria-controls="menu-appbar"
              aria-haspopup="true"
              onClick={handleMenuOpen}
              color="inherit"
            >
              <AccountCircle />
            </IconButton>
            <Menu
              id="menu-appbar"
              anchorEl={anchorEl}
              anchorOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              keepMounted
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              open={Boolean(anchorEl)}
              onClose={handleMenuClose}
            >
              <MenuItem onClick={handleMenuClose}>Profile</MenuItem>
              <MenuItem onClick={handleLogout}>Logout</MenuItem>
            </Menu>
          </Box>
        </Toolbar>
      </AppBar>
      
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mt: 2 }}>
        <Tabs value={selectedTab} onChange={handleTabChange} variant="scrollable" scrollButtons="auto">
          <Tab label="リアルタイムダッシュボード" />
          <Tab label="ライブセンサー監視" />
          <Tab label="リアルタイムチャート" />
          <Tab label="アナリティクス" />
          <Tab label="相関分析" />
          <Tab label="基質タイプ登録" />
          <Tab label="基質バッチ登録" />
          <Tab label="基質タイプ一覧" />
          <Tab label="基質バッチ一覧" />
          <Tab label="センサーデータ" />
          <Tab label="センサーデバイス" />
          <Tab label="閾値設定" />
          <Tab label="アラート通知" />
          <Tab label="アラート設定" />
          <Tab label="アラート履歴" />
          <Tab label="通知設定" />
          <Tab label="バッチ比較" />
          <Tab label="収益性分析" />
          <Tab label="飼料効率追跡" />
        </Tabs>
      </Box>
      
      {selectedTab === 0 && (
        <RealTimeDashboard />
      )}
      {selectedTab === 1 && (
        <SensorRealTimeDisplay farmId="farm1" />
      )}
      {selectedTab === 2 && (
        <SensorChartsRealTime />
      )}
      {selectedTab === 3 && (
        <AnalyticsDashboard />
      )}
      {selectedTab === 4 && (
        <CorrelationAnalysis />
      )}
      {selectedTab === 5 && (
        <SubstrateTypeForm 
          initialData={editingSubstrateType} 
          onSubmitSuccess={() => setEditingSubstrateType(null)} 
        />
      )}
      {selectedTab === 6 && (
        <SubstrateBatchForm 
          initialData={editingSubstrateBatch} 
          onSubmitSuccess={() => setEditingSubstrateBatch(null)} 
        />
      )}
      {selectedTab === 7 && (
        <SubstrateTypeList onEdit={handleEditSubstrateType} />
      )}
      {selectedTab === 8 && (
        <SubstrateBatchList onEdit={handleEditSubstrateBatch} />
      )}
      {selectedTab === 9 && (
        <SensorReadingsList />
      )}
      {selectedTab === 10 && (
        <SensorDeviceList />
      )}
      {selectedTab === 11 && (
        <ThresholdSettings />
      )}
      {selectedTab === 12 && (
        <AlertNotificationCenter />
      )}
      {selectedTab === 13 && (
        <AlertSettings />
      )}
      {selectedTab === 14 && (
        <AlertHistory />
      )}
      {selectedTab === 15 && (
        <NotificationSettings />
      )}
      {selectedTab === 16 && (
        <BatchComparison />
      )}
      {selectedTab === 17 && (
        <ProfitabilityDashboard />
      )}
      {selectedTab === 18 && (
        <FeedEfficiencyTracker />
      )}
    </Container>
  );
};

// Main App Component with Routing
const App = () => {
  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginForm />} />
          <Route 
            path="/" 
            element={
              <PrivateRoute>
                <OptimizedDataProvider>
                  <Dashboard />
                </OptimizedDataProvider>
              </PrivateRoute>
            } 
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
};

export default App;