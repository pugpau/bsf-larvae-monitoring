import React, { useState } from 'react';
import { 
  Container, 
  AppBar, 
  Toolbar, 
  Typography, 
  Tabs, 
  Tab, 
  Box 
} from '@mui/material';
import SubstrateTypeForm from './components/substrate/SubstrateTypeForm.js';
import SubstrateBatchForm from './components/substrate/SubstrateBatchForm.js';
import SubstrateTypeList from './components/substrate/SubstrateTypeList.js';
import SubstrateBatchList from './components/substrate/SubstrateBatchList.js';
import SensorReadingsList from './components/sensors/SensorReadingsList.js';
import SensorDeviceList from './components/sensors/SensorDeviceList.js';

const App = () => {
  const [selectedTab, setSelectedTab] = useState(0);
  const [editingSubstrateType, setEditingSubstrateType] = useState(null);
  const [editingSubstrateBatch, setEditingSubstrateBatch] = useState(null);
  const [editingSensorDevice, setEditingSensorDevice] = useState(null);

  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue);
    // タブ切り替え時に編集状態をリセット
    setEditingSubstrateType(null);
    setEditingSubstrateBatch(null);
    setEditingSensorDevice(null);
  };

  const handleEditSubstrateType = (substrateType) => {
    setEditingSubstrateType(substrateType);
    setSelectedTab(0); // 基質タイプ登録タブに切り替え
  };

  const handleEditSubstrateBatch = (substrateBatch) => {
    setEditingSubstrateBatch(substrateBatch);
    setSelectedTab(1); // 基質バッチ登録タブに切り替え
  };
  
  const handleEditSensorDevice = (sensorDevice) => {
    setEditingSensorDevice(sensorDevice);
    setSelectedTab(5); // センサーデバイスタブに切り替え
  };

  return (
    <Container maxWidth="md">
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6">
            BSF幼虫養殖環境管理システム
          </Typography>
        </Toolbar>
      </AppBar>
      
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mt: 2 }}>
        <Tabs value={selectedTab} onChange={handleTabChange} variant="scrollable" scrollButtons="auto">
          <Tab label="基質タイプ登録" />
          <Tab label="基質バッチ登録" />
          <Tab label="基質タイプ一覧" />
          <Tab label="基質バッチ一覧" />
          <Tab label="センサーデータ" />
          <Tab label="センサーデバイス" />
        </Tabs>
      </Box>
      
      {selectedTab === 0 && (
        <SubstrateTypeForm 
          initialData={editingSubstrateType} 
          onSubmitSuccess={() => setEditingSubstrateType(null)} 
        />
      )}
      {selectedTab === 1 && (
        <SubstrateBatchForm 
          initialData={editingSubstrateBatch} 
          onSubmitSuccess={() => setEditingSubstrateBatch(null)} 
        />
      )}
      {selectedTab === 2 && (
        <SubstrateTypeList onEdit={handleEditSubstrateType} />
      )}
      {selectedTab === 3 && (
        <SubstrateBatchList onEdit={handleEditSubstrateBatch} />
      )}
      {selectedTab === 4 && (
        <SensorReadingsList />
      )}
      {selectedTab === 5 && (
        <SensorDeviceList onEdit={handleEditSensorDevice} />
      )}
    </Container>
  );
};

export default App;
