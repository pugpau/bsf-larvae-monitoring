import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Tabs,
  Tab,
  Box,
  Menu,
  MenuItem,
  IconButton,
  ThemeProvider,
  CssBaseline
} from '@mui/material';
import { AccountCircle } from '@mui/icons-material';
import theme from './theme/materialTheme';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import LoginForm from './components/auth/LoginForm';
import PrivateRoute from './components/auth/PrivateRoute';
import SubstrateTypeForm from './components/substrate/SubstrateTypeForm.js';
import SubstrateBatchForm from './components/substrate/SubstrateBatchForm.js';
import SubstrateTypeList from './components/substrate/SubstrateTypeList.js';
import SubstrateBatchList from './components/substrate/SubstrateBatchList.js';
import AnalyticsDashboard from './components/analytics/AnalyticsDashboard.js';
import CorrelationAnalysis from './components/analytics/CorrelationAnalysis.js';
import BatchComparison from './components/batch/BatchComparison.js';
import { initializeFromApi } from './utils/storage';


const Dashboard = () => {
  const [selectedTab, setSelectedTab] = useState(0);

  // Try to sync data from backend API on mount
  useEffect(() => {
    initializeFromApi();
  }, []);
  const [editingSubstrateType, setEditingSubstrateType] = useState(null);
  const [editingSubstrateBatch, setEditingSubstrateBatch] = useState(null);
  const [anchorEl, setAnchorEl] = useState(null);

  const { user, logout } = useAuth();

  const handleTabChange = (_, newValue) => {
    setSelectedTab(newValue);
    setEditingSubstrateType(null);
    setEditingSubstrateBatch(null);
  };

  const handleEditSubstrateType = (substrateType) => {
    setEditingSubstrateType(substrateType);
    setSelectedTab(4);
  };

  const handleEditSubstrateBatch = (substrateBatch) => {
    setEditingSubstrateBatch(substrateBatch);
    setSelectedTab(0);
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
    <Container maxWidth="xl" sx={{ px: { xs: 2, sm: 3, md: 4 } }}>
      {/* Dashboard Header */}
      <Box className="dashboard-header">
        <Box>
          <Typography className="dashboard-header__title" component="h1">
            BSF-LoopTech
          </Typography>
          <Typography className="dashboard-header__subtitle">
            廃棄物処理配合最適化システム
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Typography
            variant="body2"
            sx={{ mr: 1, color: 'text.secondary', fontFamily: "'Fira Sans', sans-serif" }}
          >
            {user?.username}
          </Typography>
          <IconButton
            size="small"
            aria-label="ユーザーメニュー"
            aria-controls="menu-appbar"
            aria-haspopup="true"
            onClick={handleMenuOpen}
            sx={{ color: 'text.secondary' }}
          >
            <AccountCircle />
          </IconButton>
          <Menu
            id="menu-appbar"
            anchorEl={anchorEl}
            anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            keepMounted
            transformOrigin={{ vertical: 'top', horizontal: 'right' }}
            open={Boolean(anchorEl)}
            onClose={handleMenuClose}
          >
            <MenuItem onClick={handleLogout}>ログアウト</MenuItem>
          </Menu>
        </Box>
      </Box>

      {/* Tab Navigation — MASTER.md 5-tab structure */}
      <Box className="industrial-tabs">
        <Tabs
          value={selectedTab}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="搬入管理" />
          <Tab label="配合管理" />
          <Tab label="分析ダッシュボード" />
          <Tab label="品質管理" />
          <Tab label="マスタ管理" />
        </Tabs>
      </Box>

      {/* Tab 0: 搬入管理 — 搬入予定、分析結果入力、履歴 */}
      {selectedTab === 0 && (
        <Box>
          {editingSubstrateBatch ? (
            <SubstrateBatchForm
              initialData={editingSubstrateBatch}
              onSubmitSuccess={() => setEditingSubstrateBatch(null)}
            />
          ) : (
            <SubstrateBatchList onEdit={handleEditSubstrateBatch} />
          )}
        </Box>
      )}

      {/* Tab 1: 配合管理 — 固化剤・溶出抑制材の配合レシピ、AI推奨 */}
      {selectedTab === 1 && (
        <Box>
          <BatchComparison />
        </Box>
      )}

      {/* Tab 2: 分析ダッシュボード — 相関グラフ、統計、トレンド */}
      {selectedTab === 2 && (
        <Box>
          <CorrelationAnalysis />
        </Box>
      )}

      {/* Tab 3: 品質管理 — 規制基準チェック、合否判定履歴 */}
      {selectedTab === 3 && (
        <Box>
          <AnalyticsDashboard />
        </Box>
      )}

      {/* Tab 4: マスタ管理 — 材料マスタ、基準値設定 */}
      {selectedTab === 4 && (
        <Box>
          {editingSubstrateType ? (
            <SubstrateTypeForm
              initialData={editingSubstrateType}
              onSubmitSuccess={() => setEditingSubstrateType(null)}
            />
          ) : (
            <SubstrateTypeList onEdit={handleEditSubstrateType} />
          )}
        </Box>
      )}
    </Container>
  );
};

const App = () => {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
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
    </ThemeProvider>
  );
};

export default App;
