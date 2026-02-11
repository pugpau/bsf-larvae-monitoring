import React, { useState } from 'react';
import { Box, Tabs, Tab } from '@mui/material';
import SupplierList from './SupplierList';
import SolidificationMaterialList from './SolidificationMaterialList';
import LeachingSuppressantList from './LeachingSuppressantList';

interface TabPanelProps {
  children: React.ReactNode;
  value: number;
  index: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <Box role="tabpanel" hidden={value !== index} sx={{ pt: 2 }}>
    {value === index && children}
  </Box>
);

const MasterManagement: React.FC = () => {
  const [subTab, setSubTab] = useState(0);

  return (
    <Box>
      <Tabs
        value={subTab}
        onChange={(_, v) => setSubTab(v)}
        variant="scrollable"
        scrollButtons="auto"
        sx={{
          borderBottom: 1,
          borderColor: 'divider',
          '& .MuiTab-root': {
            fontSize: '0.8rem',
            minHeight: 40,
            py: 0.5,
          },
        }}
      >
        <Tab label="搬入先" />
        <Tab label="固化材" />
        <Tab label="溶出抑制剤" />
      </Tabs>

      <TabPanel value={subTab} index={0}>
        <SupplierList />
      </TabPanel>
      <TabPanel value={subTab} index={1}>
        <SolidificationMaterialList />
      </TabPanel>
      <TabPanel value={subTab} index={2}>
        <LeachingSuppressantList />
      </TabPanel>
    </Box>
  );
};

export default MasterManagement;
