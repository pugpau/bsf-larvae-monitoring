import React, { useState, useCallback } from 'react';
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
import DeliveryScheduleList from './components/delivery/DeliveryScheduleList';
import AnalyticsDashboard from './components/analytics/AnalyticsDashboard';
import CorrelationAnalysis from './components/analytics/CorrelationAnalysis';
import MasterManagement from './components/master/MasterManagement';
import RecipeList from './components/recipe/RecipeList';
import FormulationPanel from './components/formulation/FormulationPanel';
import MLPredictionPanel from './components/analytics/MLPredictionPanel';
import OptimizationPanel from './components/analytics/OptimizationPanel';
import TrendAnalysis from './components/analytics/TrendAnalysis';
import PredictionAccuracy from './components/analytics/PredictionAccuracy';
import KPIDashboard from './components/analytics/KPIDashboard';
import IntegrationOverview from './components/analytics/IntegrationOverview';
import ActivityBell from './components/activity/ActivityBell';
import ChatFab from './components/chat/ChatFab';
import ErrorBoundary from './components/common/ErrorBoundary';

const Dashboard: React.FC = () => {
  const [selectedTab, setSelectedTab] = useState(0);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [pendingWasteRecordId, setPendingWasteRecordId] = useState<string | null>(null);

  const { user, logout } = useAuth();

  /** Tab 0 → Tab 1 連携: 搬入記録IDを渡して配合管理タブへ遷移 */
  const handleStartFormulation = useCallback((wasteRecordId: string) => {
    setPendingWasteRecordId(wasteRecordId);
    setSelectedTab(1);
  }, []);

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setSelectedTab(newValue);
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
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
            ERC製品管理システム
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
          <ActivityBell />
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
          <Tab label="搬入予定" />
          <Tab label="配合管理" />
          <Tab label="分析ダッシュボード" />
          <Tab label="品質管理" />
          <Tab label="マスタ管理" />
        </Tabs>
      </Box>

      {/* Tab 0: 搬入予定 — 搬入予定CRUD、ステータス管理 */}
      {selectedTab === 0 && (
        <ErrorBoundary fallbackTitle="搬入予定でエラーが発生しました">
          <Box>
            <DeliveryScheduleList onStartFormulation={handleStartFormulation} />
          </Box>
        </ErrorBoundary>
      )}

      {/* Tab 1: 配合管理 — 配合ワークフロー、レシピCRUD、ML予測、コスト最適化 */}
      {selectedTab === 1 && (
        <ErrorBoundary fallbackTitle="配合管理でエラーが発生しました">
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <FormulationPanel
              initialWasteRecordId={pendingWasteRecordId}
              onConsumeWasteRecordId={() => setPendingWasteRecordId(null)}
            />
            <RecipeList />
            <MLPredictionPanel />
            <OptimizationPanel />
          </Box>
        </ErrorBoundary>
      )}

      {/* Tab 2: 分析ダッシュボード — 統合ビュー、KPI、相関グラフ、トレンド、精度 */}
      {selectedTab === 2 && (
        <ErrorBoundary fallbackTitle="分析ダッシュボードでエラーが発生しました">
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <IntegrationOverview />
            <KPIDashboard />
            <CorrelationAnalysis />
            <TrendAnalysis />
            <PredictionAccuracy />
          </Box>
        </ErrorBoundary>
      )}

      {/* Tab 3: 品質管理 — 規制基準チェック、合否判定履歴 */}
      {selectedTab === 3 && (
        <ErrorBoundary fallbackTitle="品質管理でエラーが発生しました">
          <Box>
            <AnalyticsDashboard />
          </Box>
        </ErrorBoundary>
      )}

      {/* Tab 4: マスタ管理 — 搬入先、固化材、溶出抑制剤マスタ */}
      {selectedTab === 4 && (
        <ErrorBoundary fallbackTitle="マスタ管理でエラーが発生しました">
          <Box>
            <MasterManagement />
          </Box>
        </ErrorBoundary>
      )}

      {/* Floating AI Chat Button */}
      <ChatFab />
    </Container>
  );
};

const App: React.FC = () => {
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
