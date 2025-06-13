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
import LoginForm from './components/auth/LoginForm';
import PrivateRoute from './components/auth/PrivateRoute';
import SubstrateTypeForm from './components/substrate/SubstrateTypeForm.js';
import SubstrateBatchForm from './components/substrate/SubstrateBatchForm.js';
import SubstrateTypeList from './components/substrate/SubstrateTypeList.js';
import SubstrateBatchList from './components/substrate/SubstrateBatchList.js';
import SensorReadingsList from './components/sensors/SensorReadingsList.js';
import SensorDeviceList from './components/sensors/SensorDeviceList.js';
import RealTimeDashboard from './components/dashboard/RealTimeDashboard.js';

// Main Dashboard Component
const Dashboard = () => {
  const [selectedTab, setSelectedTab] = useState(0);
  const [editingSubstrateType, setEditingSubstrateType] = useState(null);
  const [editingSubstrateBatch, setEditingSubstrateBatch] = useState(null);
  const [editingSensorDevice, setEditingSensorDevice] = useState(null);
  const [anchorEl, setAnchorEl] = useState(null);
  
  const { user, logout } = useAuth();

  const handleTabChange = (_, newValue) => {
    setSelectedTab(newValue);
    // タブ切り替え時に編集状態をリセット
    setEditingSubstrateType(null);
    setEditingSubstrateBatch(null);
    setEditingSensorDevice(null);
  };

  const handleEditSubstrateType = (substrateType) => {
    setEditingSubstrateType(substrateType);
    setSelectedTab(1); // 基質タイプ登録タブに切り替え
  };

  const handleEditSubstrateBatch = (substrateBatch) => {
    setEditingSubstrateBatch(substrateBatch);
    setSelectedTab(2); // 基質バッチ登録タブに切り替え
  };
  
  const handleEditSensorDevice = (sensorDevice) => {
    setEditingSensorDevice(sensorDevice);
    setSelectedTab(6); // センサーデバイスタブに切り替え
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
    <Container maxWidth="md">
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
          <Tab label="基質タイプ登録" />
          <Tab label="基質バッチ登録" />
          <Tab label="基質タイプ一覧" />
          <Tab label="基質バッチ一覧" />
          <Tab label="センサーデータ" />
          <Tab label="センサーデバイス" />
        </Tabs>
      </Box>
      
      {selectedTab === 0 && (
        <RealTimeDashboard />
      )}
      {selectedTab === 1 && (
        <SubstrateTypeForm 
          initialData={editingSubstrateType} 
          onSubmitSuccess={() => setEditingSubstrateType(null)} 
        />
      )}
      {selectedTab === 2 && (
        <SubstrateBatchForm 
          initialData={editingSubstrateBatch} 
          onSubmitSuccess={() => setEditingSubstrateBatch(null)} 
        />
      )}
      {selectedTab === 3 && (
        <SubstrateTypeList onEdit={handleEditSubstrateType} />
      )}
      {selectedTab === 4 && (
        <SubstrateBatchList onEdit={handleEditSubstrateBatch} />
      )}
      {selectedTab === 5 && (
        <SensorReadingsList />
      )}
      {selectedTab === 6 && (
        <SensorDeviceList onEdit={handleEditSensorDevice} />
      )}
    </Container>
  );
};

// Main App Component with Routing
const App = () => {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginForm />} />
          <Route 
            path="/" 
            element={
              <PrivateRoute>
                <Dashboard />
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