import React from 'react';
import { Box, Skeleton } from '@mui/material';

interface ChartSkeletonProps {
  height?: number;
}

const ChartSkeleton: React.FC<ChartSkeletonProps> = ({ height = 280 }) => (
  <Box sx={{ width: '100%', py: 2 }}>
    <Skeleton variant="rectangular" animation="wave" width="100%" height={height} sx={{ borderRadius: 1 }} />
  </Box>
);

export default ChartSkeleton;
