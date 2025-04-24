import React from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  Button, 
  Typography, 
  Grid, 
  Paper, 
  Box,
  Divider,
  Chip
} from '@mui/material';
import { 
  AccessTime as TimeIcon,
  LocationOn as LocationIcon,
  DeviceHub as DeviceIcon,
  Speed as ValueIcon,
  Category as TypeIcon,
  Business as FarmIcon
} from '@mui/icons-material';

const SensorReadingDetail = ({ open, onClose, reading }) => {
  if (!reading) return null;

  const formatTimestamp = (timestamp) => {
    try {
      if (timestamp instanceof Date) {
        return timestamp.toLocaleString();
      }
      
      if (typeof timestamp === 'string' && timestamp.includes('T')) {
        const date = new Date(timestamp);
        return date.toLocaleString();
      }
      
      if (typeof timestamp === 'number') {
        const date = timestamp > 9999999999 
          ? new Date(timestamp) // milliseconds
          : new Date(timestamp * 1000); // seconds
        return date.toLocaleString();
      }
      
      return timestamp;
    } catch (error) {
      console.error('Error formatting timestamp:', error, timestamp);
      return 'Invalid Date';
    }
  };

  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">センサーデータ詳細</Typography>
          <Chip 
            label={`ID: ${reading.id || 'N/A'}`} 
            color="primary" 
            variant="outlined" 
            size="small" 
          />
        </Box>
      </DialogTitle>
      <DialogContent>
        <Paper elevation={0} sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>基本情報</Typography>
          <Divider sx={{ mb: 2 }} />
          
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Box display="flex" alignItems="center" mb={1}>
                <TimeIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="body1" component="span" fontWeight="bold" sx={{ mr: 1 }}>
                  タイムスタンプ:
                </Typography>
                <Typography variant="body1" component="span">
                  {formatTimestamp(reading.time) || formatTimestamp(reading.timestamp) || 'Invalid Date'}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Box display="flex" alignItems="center" mb={1}>
                <FarmIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="body1" component="span" fontWeight="bold" sx={{ mr: 1 }}>
                  ファームID:
                </Typography>
                <Typography variant="body1" component="span">
                  {reading.farm_id}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Box display="flex" alignItems="center" mb={1}>
                <DeviceIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="body1" component="span" fontWeight="bold" sx={{ mr: 1 }}>
                  デバイスID:
                </Typography>
                <Typography variant="body1" component="span">
                  {reading.device_id}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Box display="flex" alignItems="center" mb={1}>
                <TypeIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="body1" component="span" fontWeight="bold" sx={{ mr: 1 }}>
                  デバイスタイプ:
                </Typography>
                <Typography variant="body1" component="span">
                  {reading.device_type}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </Paper>

        <Paper elevation={0} sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>測定データ</Typography>
          <Divider sx={{ mb: 2 }} />
          
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Box display="flex" alignItems="center" mb={1}>
                <TypeIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="body1" component="span" fontWeight="bold" sx={{ mr: 1 }}>
                  測定タイプ:
                </Typography>
                <Typography variant="body1" component="span">
                  {reading.field || '-'}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Box display="flex" alignItems="center" mb={1}>
                <ValueIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="body1" component="span" fontWeight="bold" sx={{ mr: 1 }}>
                  測定値:
                </Typography>
                <Typography variant="body1" component="span">
                  {reading.value} {reading.unit}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Box display="flex" alignItems="center" mb={1}>
                <LocationIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="body1" component="span" fontWeight="bold" sx={{ mr: 1 }}>
                  場所:
                </Typography>
                <Typography variant="body1" component="span">
                  {reading.location || '-'}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </Paper>

        {reading.metadata && (
          <Paper elevation={0} sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>メタデータ</Typography>
            <Divider sx={{ mb: 2 }} />
            
            <Box sx={{ backgroundColor: '#f5f5f5', p: 2, borderRadius: 1 }}>
              <pre style={{ margin: 0, overflow: 'auto' }}>
                {JSON.stringify(reading.metadata, null, 2)}
              </pre>
            </Box>
          </Paper>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="primary">
          閉じる
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SensorReadingDetail;
