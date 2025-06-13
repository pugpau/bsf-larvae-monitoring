/**
 * Real-time sensor charts component with WebSocket integration.
 * Extends the existing SensorCharts with live data updates.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  Box, 
  Typography, 
  Card, 
  CardContent, 
  Grid, 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem,
  ToggleButtonGroup,
  ToggleButton,
  Tabs,
  Tab,
  Switch,
  FormControlLabel,
  Chip
} from '@mui/material';
import { 
  Chart as ChartJS, 
  CategoryScale, 
  LinearScale, 
  PointElement, 
  LineElement, 
  Title, 
  Tooltip, 
  Legend,
  TimeScale
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import 'chartjs-adapter-date-fns';
import { ja } from 'date-fns/locale';
import { useFarmWebSocket, MESSAGE_TYPES } from '../../hooks/useWebSocket';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  TimeScale,
  Title,
  Tooltip,
  Legend
);

// Chart color palette
const COLORS = [
  'rgba(75, 192, 192, 1)',   // Teal
  'rgba(255, 99, 132, 1)',   // Pink
  'rgba(54, 162, 235, 1)',   // Blue
  'rgba(255, 206, 86, 1)',   // Yellow
  'rgba(153, 102, 255, 1)',  // Purple
  'rgba(255, 159, 64, 1)',   // Orange
  'rgba(199, 199, 199, 1)',  // Gray
];

const BACKGROUND_COLORS = COLORS.map(color => color.replace('1)', '0.2)'));

const SensorChartsRealTime = ({ farmId, initialReadings = [], maxDataPoints = 100 }) => {
  const [chartType, setChartType] = useState('time');
  const [selectedTab, setSelectedTab] = useState(0);
  const [selectedLocation, setSelectedLocation] = useState('all');
  const [realTimeEnabled, setRealTimeEnabled] = useState(true);
  const [autoScale, setAutoScale] = useState(true);
  
  // Data state
  const [locations, setLocations] = useState([]);
  const [measurementTypes, setMeasurementTypes] = useState([]);
  const [chartData, setChartData] = useState({});
  const [dataBuffer, setDataBuffer] = useState(new Map()); // Device-measurement buffer
  const [lastUpdate, setLastUpdate] = useState(null);
  const [dataStats, setDataStats] = useState({
    totalPoints: 0,
    lastReceived: null,
    updateCount: 0
  });

  // Refs for managing data efficiently
  const chartRefs = useRef({});
  const updateTimeoutRef = useRef(null);

  // WebSocket connection
  const {
    isConnected,
    connectionState,
    addMessageHandler,
    subscribe
  } = useFarmWebSocket(farmId, {
    onConnect: () => {
      console.log(`Connected to farm ${farmId} for real-time charts`);
      if (realTimeEnabled) {
        subscribe({
          types: [MESSAGE_TYPES.SENSOR_DATA],
          farm_id: farmId
        });
      }
    }
  });

  // Initialize with existing readings
  useEffect(() => {
    if (initialReadings && initialReadings.length > 0) {
      processInitialReadings(initialReadings);
    }
  }, [initialReadings]);

  // Handle real-time toggle
  useEffect(() => {
    if (isConnected && realTimeEnabled) {
      subscribe({
        types: [MESSAGE_TYPES.SENSOR_DATA],
        farm_id: farmId
      });
    }
  }, [realTimeEnabled, isConnected, farmId, subscribe]);

  // Process initial readings
  const processInitialReadings = (readings) => {
    const buffer = new Map();
    const locationSet = new Set();
    const measurementSet = new Set();

    readings.forEach(reading => {
      const key = `${reading.device_id}_${reading.measurement_type}`;
      
      if (!buffer.has(key)) {
        buffer.set(key, []);
      }
      
      buffer.get(key).push({
        ...reading,
        timestamp: new Date(reading.timestamp),
        value: parseFloat(reading.value)
      });

      if (reading.location) locationSet.add(reading.location);
      if (reading.measurement_type) measurementSet.add(reading.measurement_type);
    });

    // Sort and limit data points
    buffer.forEach((points, key) => {
      points.sort((a, b) => a.timestamp - b.timestamp);
      if (points.length > maxDataPoints) {
        buffer.set(key, points.slice(-maxDataPoints));
      }
    });

    setDataBuffer(buffer);
    setLocations(Array.from(locationSet));
    setMeasurementTypes(Array.from(measurementSet));
    
    updateChartData(buffer, selectedLocation, chartType);
  };

  // Handle incoming real-time sensor data
  const handleSensorData = useCallback((message) => {
    if (!realTimeEnabled) return;

    const { data } = message;
    const key = `${data.device_id}_${data.measurement_type}`;

    setDataBuffer(prevBuffer => {
      const newBuffer = new Map(prevBuffer);
      
      if (!newBuffer.has(key)) {
        newBuffer.set(key, []);
      }

      const points = newBuffer.get(key);
      const newPoint = {
        ...data,
        timestamp: new Date(data.timestamp),
        value: parseFloat(data.value)
      };

      // Add new point and maintain max size
      points.push(newPoint);
      if (points.length > maxDataPoints) {
        points.shift(); // Remove oldest point
      }

      // Sort by timestamp to ensure order
      points.sort((a, b) => a.timestamp - b.timestamp);

      return newBuffer;
    });

    // Update locations and measurement types
    setLocations(prev => {
      const set = new Set(prev);
      if (data.location) set.add(data.location);
      return Array.from(set);
    });

    setMeasurementTypes(prev => {
      const set = new Set(prev);
      if (data.measurement_type) set.add(data.measurement_type);
      return Array.from(set);
    });

    // Update stats
    setDataStats(prev => ({
      totalPoints: prev.totalPoints + 1,
      lastReceived: new Date(),
      updateCount: prev.updateCount + 1
    }));

    setLastUpdate(new Date());

    // Debounced chart update
    if (updateTimeoutRef.current) {
      clearTimeout(updateTimeoutRef.current);
    }
    updateTimeoutRef.current = setTimeout(() => {
      setDataBuffer(currentBuffer => {
        updateChartData(currentBuffer, selectedLocation, chartType);
        return currentBuffer;
      });
    }, 200); // Update charts every 200ms max

  }, [realTimeEnabled, selectedLocation, chartType, maxDataPoints]);

  // Set up WebSocket message handler
  useEffect(() => {
    const cleanup = addMessageHandler(MESSAGE_TYPES.SENSOR_DATA, handleSensorData);
    return cleanup;
  }, [addMessageHandler, handleSensorData]);

  // Update chart data when filters change
  useEffect(() => {
    updateChartData(dataBuffer, selectedLocation, chartType);
  }, [dataBuffer, selectedLocation, chartType]);

  // Update chart data function
  const updateChartData = (buffer, location, chartType) => {
    if (buffer.size === 0) return;

    const newChartData = {};

    // Group data by measurement type
    const groupedByMeasurement = {};
    
    for (const [key, points] of buffer) {
      const measurementType = key.split('_').slice(1).join('_'); // Handle measurement types with underscores
      
      if (!groupedByMeasurement[measurementType]) {
        groupedByMeasurement[measurementType] = new Map();
      }
      
      const deviceId = key.split('_')[0];
      groupedByMeasurement[measurementType].set(deviceId, points);
    }

    // Create chart data for each measurement type
    Object.keys(groupedByMeasurement).forEach(measurementType => {
      const deviceData = groupedByMeasurement[measurementType];
      
      if (chartType === 'time') {
        // Time series chart
        const datasets = [];
        let colorIndex = 0;

        for (const [deviceId, points] of deviceData) {
          // Apply location filter
          const filteredPoints = location === 'all' 
            ? points 
            : points.filter(point => point.location === location);

          if (filteredPoints.length > 0) {
            datasets.push({
              label: `${deviceId} (${filteredPoints[0]?.location || 'Unknown'})`,
              data: filteredPoints.map(point => ({
                x: point.timestamp,
                y: point.value
              })),
              borderColor: COLORS[colorIndex % COLORS.length],
              backgroundColor: BACKGROUND_COLORS[colorIndex % BACKGROUND_COLORS.length],
              tension: 0.1,
              pointRadius: 1,
              pointHoverRadius: 4,
              borderWidth: 2,
            });
            colorIndex++;
          }
        }

        newChartData[measurementType] = {
          datasets
        };
      } else {
        // Comparison chart - latest values
        const deviceIds = [];
        const values = [];
        const backgroundColors = [];
        const borderColors = [];
        let colorIndex = 0;

        for (const [deviceId, points] of deviceData) {
          // Apply location filter
          const filteredPoints = location === 'all' 
            ? points 
            : points.filter(point => point.location === location);

          if (filteredPoints.length > 0) {
            const latestPoint = filteredPoints[filteredPoints.length - 1];
            deviceIds.push(deviceId);
            values.push(latestPoint.value);
            backgroundColors.push(BACKGROUND_COLORS[colorIndex % BACKGROUND_COLORS.length]);
            borderColors.push(COLORS[colorIndex % COLORS.length]);
            colorIndex++;
          }
        }

        newChartData[measurementType] = {
          labels: deviceIds,
          datasets: [{
            label: measurementType,
            data: values,
            backgroundColor: backgroundColors,
            borderColor: borderColors,
            borderWidth: 1,
          }]
        };
      }
    });

    setChartData(newChartData);
  };

  // Chart options with real-time optimizations
  const getChartOptions = (measurementType) => {
    let unit = '';
    
    if (measurementType === 'temperature') unit = '°C';
    else if (measurementType === 'humidity') unit = '%RH';
    else if (measurementType === 'pressure') unit = 'hPa';
    else if (measurementType === 'h2s') unit = 'ppm';
    else if (measurementType === 'nh3') unit = 'ppm';

    const options = {
      responsive: true,
      maintainAspectRatio: false,
      animation: realTimeEnabled ? {
        duration: 200,
        easing: 'linear'
      } : {
        duration: 0
      },
      plugins: {
        legend: {
          position: 'top',
        },
        title: {
          display: true,
          text: `${measurementType.charAt(0).toUpperCase() + measurementType.slice(1)} - Real-time`,
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return `${context.dataset.label}: ${context.parsed.y} ${unit}`;
            }
          }
        }
      },
      scales: {
        y: {
          title: {
            display: true,
            text: unit
          }
        }
      },
      elements: {
        point: {
          radius: realTimeEnabled ? 1 : 3
        },
        line: {
          tension: 0.1
        }
      }
    };

    // Time scale for time series
    if (chartType === 'time') {
      options.scales.x = {
        type: 'time',
        time: {
          unit: 'minute',
          displayFormats: {
            minute: 'HH:mm',
            hour: 'MM/dd HH:mm'
          },
          tooltipFormat: 'yyyy/MM/dd HH:mm:ss'
        },
        adapters: {
          date: {
            locale: ja
          }
        },
        title: {
          display: true,
          text: '時間'
        }
      };

      // Auto-scale for real-time
      if (autoScale && realTimeEnabled) {
        options.scales.x.min = function(scale) {
          const now = new Date();
          return new Date(now.getTime() - 10 * 60 * 1000); // Last 10 minutes
        };
      }
    }

    return options;
  };

  return (
    <Box sx={{ mt: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          リアルタイムセンサーデータ可視化
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Chip 
            label={isConnected ? '接続中' : '切断中'}
            color={isConnected ? 'success' : 'error'}
            size="small"
          />
          {lastUpdate && (
            <Typography variant="caption" color="textSecondary">
              最終更新: {lastUpdate.toLocaleTimeString()}
            </Typography>
          )}
        </Box>
      </Box>

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} sm={6} md={3}>
          <FormControl fullWidth size="small">
            <InputLabel>場所</InputLabel>
            <Select
              value={selectedLocation}
              label="場所"
              onChange={(e) => setSelectedLocation(e.target.value)}
            >
              <MenuItem value="all">すべての場所</MenuItem>
              {locations.map(location => (
                <MenuItem key={location} value={location}>{location}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <ToggleButtonGroup
            value={chartType}
            exclusive
            onChange={(e, newType) => newType && setChartType(newType)}
            size="small"
            fullWidth
          >
            <ToggleButton value="time">時系列</ToggleButton>
            <ToggleButton value="comparison">比較</ToggleButton>
          </ToggleButtonGroup>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <FormControlLabel
            control={
              <Switch
                checked={realTimeEnabled}
                onChange={(e) => setRealTimeEnabled(e.target.checked)}
                size="small"
              />
            }
            label="リアルタイム"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <FormControlLabel
            control={
              <Switch
                checked={autoScale}
                onChange={(e) => setAutoScale(e.target.checked)}
                size="small"
              />
            }
            label="自動スケール"
          />
        </Grid>
      </Grid>

      {/* Data statistics */}
      <Card sx={{ mb: 2 }}>
        <CardContent sx={{ py: 1 }}>
          <Grid container spacing={2}>
            <Grid item xs={3}>
              <Typography variant="caption" color="textSecondary">総データ点数</Typography>
              <Typography variant="body2">{dataStats.totalPoints}</Typography>
            </Grid>
            <Grid item xs={3}>
              <Typography variant="caption" color="textSecondary">更新回数</Typography>
              <Typography variant="body2">{dataStats.updateCount}</Typography>
            </Grid>
            <Grid item xs={3}>
              <Typography variant="caption" color="textSecondary">接続状態</Typography>
              <Typography variant="body2">{connectionState}</Typography>
            </Grid>
            <Grid item xs={3}>
              <Typography variant="caption" color="textSecondary">バッファサイズ</Typography>
              <Typography variant="body2">{dataBuffer.size}</Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {measurementTypes.length > 0 ? (
        <>
          <Tabs 
            value={selectedTab} 
            onChange={(e, newValue) => setSelectedTab(newValue)}
            variant="scrollable"
            scrollButtons="auto"
            sx={{ mb: 2 }}
          >
            {measurementTypes.map((type, index) => (
              <Tab key={type} label={type} value={index} />
            ))}
          </Tabs>
          
          {measurementTypes.map((type, index) => (
            <Box 
              key={type} 
              sx={{ 
                display: selectedTab === index ? 'block' : 'none',
                height: 400,
                mb: 2
              }}
            >
              {chartData[type] ? (
                <Line 
                  ref={el => chartRefs.current[type] = el}
                  data={chartData[type]} 
                  options={getChartOptions(type)} 
                />
              ) : (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                  <Typography color="textSecondary">
                    {realTimeEnabled ? 'リアルタイムデータを待機中...' : 'データがありません'}
                  </Typography>
                </Box>
              )}
            </Box>
          ))}
        </>
      ) : (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
          <Typography color="textSecondary">
            {realTimeEnabled ? 'センサーデータを待機中...' : 'データがありません'}
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default SensorChartsRealTime;