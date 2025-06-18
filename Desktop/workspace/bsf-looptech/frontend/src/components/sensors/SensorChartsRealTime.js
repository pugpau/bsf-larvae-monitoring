/**
 * Real-time sensor charts component with auto-updating data.
 * Shows live updating charts with streaming sensor data.
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Button,
  ButtonGroup,
  Alert,
  CircularProgress,
  useMediaQuery,
  useTheme
} from '@mui/material';
import {
  Timeline as TimelineIcon,
  ShowChart as ShowChartIcon,
  BarChart as BarChartIcon
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { useRealtimeData } from '../../hooks/useRealtimeData';

// Color palette for different devices
const DEVICE_COLORS = [
  '#8884d8', '#82ca9d', '#ffc658', '#ff7c7c', '#8dd1e1', '#d084d0', '#ffb347', '#87ceeb'
];

// Chart configuration for different measurement types
const MEASUREMENT_CONFIG = {
  temperature: {
    unit: '°C',
    color: '#ff7c7c',
    min: 15,
    max: 35,
    optimalRange: [20, 30],
    label: '温度'
  },
  humidity: {
    unit: '%RH',
    color: '#82ca9d',
    min: 40,
    max: 80,
    optimalRange: [55, 75],
    label: '湿度'
  },
  pressure: {
    unit: 'hPa',
    color: '#8884d8',
    min: 1000,
    max: 1030,
    optimalRange: [1010, 1020],
    label: '気圧'
  },
  h2s: {
    unit: 'ppm',
    color: '#ffc658',
    min: 0,
    max: 50,
    optimalRange: [0, 10],
    label: 'H2Sガス'
  }
};

// Time range options
const TIME_RANGES = [
  { value: 300000, label: '5分' },
  { value: 900000, label: '15分' },
  { value: 1800000, label: '30分' },
  { value: 3600000, label: '1時間' },
  { value: 7200000, label: '2時間' }
];

// Chart type options
const CHART_TYPES = [
  { value: 'line', label: 'ライン', icon: TimelineIcon },
  { value: 'area', label: 'エリア', icon: ShowChartIcon },
  { value: 'bar', label: 'バー', icon: BarChartIcon }
];


// Custom tooltip for charts
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <Box
        sx={{
          backgroundColor: 'background.paper',
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
          p: 1,
          boxShadow: 2
        }}
      >
        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
          {new Date(label).toLocaleTimeString()}
        </Typography>
        {payload.map((entry, index) => (
          <Typography
            key={index}
            variant="body2"
            sx={{ color: entry.color }}
          >
            {entry.name}: {entry.value.toFixed(2)} {entry.payload.unit}
          </Typography>
        ))}
      </Box>
    );
  }
  return null;
};

// Individual chart component
const RealtimeChart = ({ 
  data, 
  measurementType, 
  chartType, 
  timeRange, 
  showOptimalRange,
  height = 300
}) => {
  // Handle responsive height
  const chartHeight = typeof height === 'object' ? height : { xs: height, sm: height, md: height, lg: height };
  const config = MEASUREMENT_CONFIG[measurementType] || MEASUREMENT_CONFIG.temperature;
  
  const theme = useTheme();
  const isSmallScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const isMediumScreen = useMediaQuery(theme.breakpoints.down('md'));
  
  // Calculate fixed time domain (current time - timeRange to current time)
  // Update every 10 seconds to reduce frequent re-renders
  const [currentTime, setCurrentTime] = useState(Date.now());
  
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(Date.now());
    }, 10000); // Update every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const timeDomain = useMemo(() => {
    const startTime = currentTime - timeRange;
    return [startTime, currentTime];
  }, [currentTime, timeRange]);

  // Filter data by time range and prepare for chart
  const chartData = useMemo(() => {
    const [startTime, endTime] = timeDomain;
    const filteredData = data
      .filter(reading => {
        const readingTime = new Date(reading.timestamp).getTime();
        return readingTime >= startTime && readingTime <= endTime;
      })
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      .map(reading => ({
        ...reading,
        time: new Date(reading.timestamp).getTime(),
        unit: config.unit,
        formattedTime: new Date(reading.timestamp).toLocaleTimeString()
      }));
    
    // Ensure we have data points at the start and end of the domain
    if (filteredData.length > 0) {
      // Add dummy points at exact domain boundaries if needed
      const firstTime = filteredData[0].time;
      const lastTime = filteredData[filteredData.length - 1].time;
      
      if (firstTime > startTime) {
        filteredData.unshift({
          ...filteredData[0],
          time: startTime,
          value: null
        });
      }
      
      if (lastTime < endTime) {
        filteredData.push({
          ...filteredData[filteredData.length - 1],
          time: endTime,
          value: null
        });
      }
    }
    
    return filteredData;
  }, [data, timeDomain, config.unit]);

  // Generate fixed time ticks (responsive to screen size)
  const timeTicks = useMemo(() => {
    const [startTime, endTime] = timeDomain;
    const ticks = [];
    // Adjust tick count based on screen size
    const tickCount = isSmallScreen ? 2 : isMediumScreen ? 3 : 4;
    
    for (let i = 0; i <= tickCount; i++) {
      const tickTime = startTime + (endTime - startTime) * (i / tickCount);
      ticks.push(tickTime);
    }
    return ticks;
  }, [timeDomain, isSmallScreen, isMediumScreen]);

  const timeTickFormatter = useMemo(() => {
    const tickMap = new Map();
    timeTicks.forEach((tick, index) => {
      // Use shorter format for better spacing
      const date = new Date(tick);
      const timeStr = date.toLocaleTimeString('ja-JP', {
        hour: '2-digit',
        minute: '2-digit'
      });
      tickMap.set(tick, timeStr);
    });
    
    return (tickValue) => {
      // Find the closest tick
      let closestTick = timeTicks[0];
      let minDiff = Math.abs(tickValue - timeTicks[0]);
      
      for (const tick of timeTicks) {
        const diff = Math.abs(tickValue - tick);
        if (diff < minDiff) {
          minDiff = diff;
          closestTick = tick;
        }
      }
      
      // Only show label if very close to a predefined tick
      if (minDiff < 60000) { // Within 1 minute
        return tickMap.get(closestTick) || '';
      }
      return '';
    };
  }, [timeTicks]);

  // Get unique devices for lines
  const devices = [...new Set(chartData.map(d => d.device_id))];

  // Render chart based on type
  const renderChart = () => {
    const commonProps = {
      data: chartData,
      margin: { 
        top: 5, 
        right: isSmallScreen ? 10 : 30, 
        left: isSmallScreen ? 10 : 20, 
        bottom: isSmallScreen ? 80 : 60 
      }
    };

    switch (chartType) {
      case 'area':
        return (
          <AreaChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="time"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              ticks={timeTicks}
              tickFormatter={timeTickFormatter}
              interval={0}
              allowDataOverflow={false}
              tick={{ fontSize: isSmallScreen ? 10 : 12 }}
              angle={isSmallScreen ? -90 : -45}
              textAnchor="end"
              height={isSmallScreen ? 80 : 60}
            />
            <YAxis 
              domain={[config.min, config.max]}
              label={{ value: config.unit, angle: -90, position: 'insideLeft' }}
            />
            <Tooltip content={<CustomTooltip />} />
            {/* <Legend wrapperStyle={{ paddingTop: '10px' }} iconType="line" /> */}
            {showOptimalRange && config.optimalRange && (
              <>
                <ReferenceLine y={config.optimalRange[0]} stroke="#green" strokeDasharray="5 5" />
                <ReferenceLine y={config.optimalRange[1]} stroke="#green" strokeDasharray="5 5" />
              </>
            )}
            {devices.map((device, index) => (
              <Area
                key={device}
                type="monotone"
                dataKey="value"
                stroke={DEVICE_COLORS[index % DEVICE_COLORS.length]}
                fill={DEVICE_COLORS[index % DEVICE_COLORS.length]}
                fillOpacity={0.3}
                name={device}
              />
            ))}
          </AreaChart>
        );

      case 'bar':
        return (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="time"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              ticks={timeTicks}
              tickFormatter={timeTickFormatter}
              interval={0}
              allowDataOverflow={false}
              tick={{ fontSize: isSmallScreen ? 10 : 12 }}
              angle={isSmallScreen ? -90 : -45}
              textAnchor="end"
              height={isSmallScreen ? 80 : 60}
            />
            <YAxis 
              domain={[config.min, config.max]}
              label={{ value: config.unit, angle: -90, position: 'insideLeft' }}
            />
            <Tooltip content={<CustomTooltip />} />
            {/* <Legend wrapperStyle={{ paddingTop: '10px' }} iconType="line" /> */}
            {devices.map((device, index) => (
              <Bar
                key={device}
                dataKey="value"
                fill={DEVICE_COLORS[index % DEVICE_COLORS.length]}
                name={device}
              />
            ))}
          </BarChart>
        );

      default: // line
        return (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="time"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              ticks={timeTicks}
              tickFormatter={timeTickFormatter}
              interval={0}
              allowDataOverflow={false}
              tick={{ fontSize: isSmallScreen ? 10 : 12 }}
              angle={isSmallScreen ? -90 : -45}
              textAnchor="end"
              height={isSmallScreen ? 80 : 60}
            />
            <YAxis 
              domain={[config.min, config.max]}
              label={{ value: config.unit, angle: -90, position: 'insideLeft' }}
            />
            <Tooltip content={<CustomTooltip />} />
            {/* <Legend wrapperStyle={{ paddingTop: '10px' }} iconType="line" /> */}
            {showOptimalRange && config.optimalRange && (
              <>
                <ReferenceLine y={config.optimalRange[0]} stroke="#green" strokeDasharray="5 5" />
                <ReferenceLine y={config.optimalRange[1]} stroke="#green" strokeDasharray="5 5" />
              </>
            )}
            {devices.map((device, index) => (
              <Line
                key={device}
                type="monotone"
                dataKey="value"
                stroke={DEVICE_COLORS[index % DEVICE_COLORS.length]}
                strokeWidth={2}
                dot={{ r: 3 }}
                name={device}
              />
            ))}
          </LineChart>
        );
    }
  };

  return (
    <Card sx={{ height: '100%', minHeight: 350 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {config.label} リアルタイムチャート
        </Typography>
        <Box sx={{ height: chartHeight }}>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%" key={`chart-${timeRange}-${Math.floor(currentTime / 10000)}`}>
              {renderChart()}
            </ResponsiveContainer>
          ) : (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                flexDirection: 'column'
              }}
            >
              <CircularProgress />
              <Typography variant="body2" sx={{ mt: 2 }}>
                データを読み込み中...
              </Typography>
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

// Main component
const SensorChartsRealTime = () => {
  const [selectedMeasurement, setSelectedMeasurement] = useState('temperature');
  const [chartType, setChartType] = useState('line');
  const [timeRange, setTimeRange] = useState(1800000); // 30 minutes
  const [showOptimalRange, setShowOptimalRange] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const {
    isRunning,
    sensorReadings,
    stats,
    startRealtime,
    stopRealtime
  } = useRealtimeData({
    autoStart: autoRefresh,
    updateInterval: 2000, // 2 seconds for smooth charts
    maxDataPoints: 500
  });

  // Group readings by measurement type
  const readingsByType = useMemo(() => {
    const grouped = {};
    sensorReadings.forEach(reading => {
      if (!grouped[reading.measurement_type]) {
        grouped[reading.measurement_type] = [];
      }
      grouped[reading.measurement_type].push(reading);
    });
    return grouped;
  }, [sensorReadings]);

  // Available measurement types from data
  const availableMeasurements = useMemo(() => {
    const fromData = Object.keys(readingsByType);
    // Always include default measurement types even if no data yet
    const defaultTypes = ['temperature', 'humidity', 'pressure', 'h2s'];
    const allTypes = [...new Set([...defaultTypes, ...fromData])];
    return allTypes;
  }, [readingsByType]);

  // Handle auto-refresh toggle
  useEffect(() => {
    if (autoRefresh && !isRunning) {
      startRealtime();
    } else if (!autoRefresh && isRunning) {
      stopRealtime();
    }
  }, [autoRefresh, isRunning, startRealtime, stopRealtime]);
  
  // Update selected measurement if current selection is not available
  useEffect(() => {
    if (availableMeasurements.length > 0 && !availableMeasurements.includes(selectedMeasurement)) {
      setSelectedMeasurement(availableMeasurements[0]);
    }
  }, [availableMeasurements, selectedMeasurement]);


  return (
    <Box sx={{ p: { xs: 2, sm: 3 }, width: '100%' }}>
      {/* Header */}
      <Typography variant="h4" gutterBottom>
        リアルタイムセンサーチャート
      </Typography>

      {/* Controls */}
      <Grid container spacing={{ xs: 2, sm: 3 }} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <FormControl fullWidth>
            <InputLabel>測定タイプ</InputLabel>
            <Select
              value={availableMeasurements.includes(selectedMeasurement) ? selectedMeasurement : ''}
              label="測定タイプ"
              onChange={(e) => setSelectedMeasurement(e.target.value)}
              disabled={availableMeasurements.length === 0}
            >
              {availableMeasurements.length === 0 ? (
                <MenuItem value="">データを読み込み中...</MenuItem>
              ) : (
                availableMeasurements.map(type => (
                  <MenuItem key={type} value={type}>
                    {MEASUREMENT_CONFIG[type]?.label || type}
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <FormControl fullWidth>
            <InputLabel>時間範囲</InputLabel>
            <Select
              value={timeRange}
              label="時間範囲"
              onChange={(e) => setTimeRange(e.target.value)}
            >
              {TIME_RANGES.map(range => (
                <MenuItem key={range.value} value={range.value}>
                  {range.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <ButtonGroup variant="outlined" fullWidth>
            {CHART_TYPES.map(type => {
              const IconComponent = type.icon;
              return (
                <Button
                  key={type.value}
                  variant={chartType === type.value ? 'contained' : 'outlined'}
                  onClick={() => setChartType(type.value)}
                  startIcon={<IconComponent />}
                >
                  {type.label}
                </Button>
              );
            })}
          </ButtonGroup>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={showOptimalRange}
                  onChange={(e) => setShowOptimalRange(e.target.checked)}
                />
              }
              label="最適範囲を表示"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                />
              }
              label="自動更新"
            />
          </Box>
        </Grid>
      </Grid>

      {/* Status Info */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Alert severity={isRunning ? 'success' : 'warning'}>
            {isRunning ? 'リアルタイム更新中' : '更新停止中'}
          </Alert>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Alert severity="info">
            データポイント: {stats.totalReadings}
          </Alert>
        </Grid>
        <Grid item xs={12} sm={6} md={6}>
          <Alert severity="info" icon={false}>
            <Typography variant="body2">
              表示範囲: 選択した時間範囲内のデータのみ表示
            </Typography>
          </Alert>
        </Grid>
      </Grid>

      {/* Active Devices */}
      {readingsByType[selectedMeasurement] && readingsByType[selectedMeasurement].length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            アクティブデバイス:
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {[...new Set(readingsByType[selectedMeasurement].map(d => d.device_id))].map((deviceId, index) => (
              <Box
                key={deviceId}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.5,
                  px: 1,
                  py: 0.5,
                  borderRadius: 1,
                  bgcolor: 'background.paper',
                  border: 1,
                  borderColor: 'divider'
                }}
              >
                <Box
                  sx={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    bgcolor: DEVICE_COLORS[index % DEVICE_COLORS.length]
                  }}
                />
                <Typography variant="caption">{deviceId}</Typography>
              </Box>
            ))}
          </Box>
        </Box>
      )}

      {/* Charts */}
      <Grid container spacing={{ xs: 2, sm: 3 }}>
        {/* Main Chart */}
        <Grid item xs={12}>
          <RealtimeChart
            data={readingsByType[selectedMeasurement] || []}
            measurementType={selectedMeasurement}
            chartType={chartType}
            timeRange={timeRange}
            showOptimalRange={showOptimalRange}
            height={{ xs: 300, sm: 350, md: 400, lg: 450 }}
          />
        </Grid>

        {/* Mini Charts for Other Measurements */}
        {availableMeasurements
          .filter(type => type !== selectedMeasurement)
          .slice(0, 3)
          .map(measurementType => (
            <Grid item xs={12} md={6} lg={4} key={measurementType}>
              <RealtimeChart
                data={readingsByType[measurementType] || []}
                measurementType={measurementType}
                chartType="line"
                timeRange={timeRange}
                showOptimalRange={false}
                height={{ xs: 180, sm: 200, md: 220 }}
              />
            </Grid>
          ))}
      </Grid>

      {sensorReadings.length === 0 && (
        <Alert severity="info" sx={{ mt: 3 }}>
          リアルタイムデータの生成を開始するには、自動更新を有効にしてください。
        </Alert>
      )}
    </Box>
  );
};

export default SensorChartsRealTime;