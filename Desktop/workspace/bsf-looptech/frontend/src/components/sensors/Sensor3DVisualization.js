import React, { useState, useEffect, useCallback } from 'react';
import { 
  Box, 
  Typography, 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem,
  Grid,
  Card,
  CardContent,
  Slider,
  Alert
} from '@mui/material';
import Plot from 'react-plotly.js';

/**
 * Sensor3DVisualization component
 * 
 * This component provides 3D visualization of sensor data using Plotly.js
 * It allows users to visualize relationships between different sensor measurements
 * (temperature, humidity, gas, etc.) in a 3D space.
 */
const Sensor3DVisualization = ({ readings }) => {
  // State for selected sensors and visualization parameters
  const [xAxis, setXAxis] = useState('');
  const [yAxis, setYAxis] = useState('');
  const [zAxis, setZAxis] = useState('');
  const [colorBy, setColorBy] = useState('device_id');
  const [timeRange, setTimeRange] = useState([0, 100]);
  const [sensorOptions, setSensorOptions] = useState([]);
  const [filteredReadings, setFilteredReadings] = useState([]);
  const [error, setError] = useState(null);
  const [plotData, setPlotData] = useState([]);
  const [plotLayout, setPlotLayout] = useState({});

  // Extract unique measurement types from readings
  useEffect(() => {
    if (readings && readings.length > 0) {
      // Get unique device_id + measurement_type combinations
      const uniqueCombinations = [...new Set(readings.map(r => `${r.device_id}:${r.measurement_type}`))];
      setSensorOptions(uniqueCombinations);
      
      // Set default axes if not already set
      if (!xAxis && uniqueCombinations.length > 0) {
        setXAxis(uniqueCombinations[0]);
      }
      if (!yAxis && uniqueCombinations.length > 1) {
        setYAxis(uniqueCombinations[1]);
      }
      if (!zAxis && uniqueCombinations.length > 2) {
        setZAxis(uniqueCombinations[2]);
      }
    }
  }, [readings, xAxis, yAxis, zAxis]);

  // Get unit for a given sensor - wrapped in useCallback
  const getUnit = useCallback((sensorKey) => {
    if (!sensorKey) return '';
    
    const [deviceId, measurementType] = sensorKey.split(':');
    const reading = readings.find(
      r => r.device_id === deviceId && r.measurement_type === measurementType
    );
    
    return reading ? reading.unit : '';
  }, [readings]);

  // Filter readings based on time range
  useEffect(() => {
    if (readings && readings.length > 0) {
      // Sort readings by timestamp
      const sortedReadings = [...readings].sort((a, b) => 
        new Date(a.timestamp) - new Date(b.timestamp)
      );
      
      // Calculate time range indices
      const startIdx = Math.floor(sortedReadings.length * (timeRange[0] / 100));
      const endIdx = Math.ceil(sortedReadings.length * (timeRange[1] / 100));
      
      // Filter readings by time range
      const filtered = sortedReadings.slice(startIdx, endIdx);
      setFilteredReadings(filtered);
    }
  }, [readings, timeRange]);

  // Generate plot data function wrapped in useCallback
  const generatePlotData = useCallback(() => {
    // Check if we should use physical coordinates or sensor measurements
    const usePhysicalCoordinates = xAxis === 'x_position' && yAxis === 'y_position' && zAxis === 'z_position';
    
    if (usePhysicalCoordinates) {
      // Use physical X, Y, Z coordinates from sensor devices
      setError(null);
      
      // Prepare data for 3D plot
      const xValues = [];
      const yValues = [];
      const zValues = [];
      const colors = [];
      const labels = [];
      const deviceIds = [];
      
      // Group readings by device_id to get the latest reading for each device
      const deviceReadings = {};
      
      filteredReadings.forEach(reading => {
        const deviceId = reading.device_id;
        
        if (!deviceReadings[deviceId] || new Date(reading.timestamp) > new Date(deviceReadings[deviceId].timestamp)) {
          deviceReadings[deviceId] = reading;
        }
      });
      
      // Collect data points where all three coordinates exist
      Object.values(deviceReadings).forEach(reading => {
        if (reading.x_position !== null && reading.y_position !== null && reading.z_position !== null) {
          xValues.push(reading.x_position);
          yValues.push(reading.y_position);
          zValues.push(reading.z_position);
          deviceIds.push(reading.device_id);
          
          // Color by selected attribute
          if (colorBy === 'device_id') {
            colors.push(reading.device_id);
          } else if (colorBy === 'location') {
            colors.push(reading.location);
          } else if (colorBy === 'measurement_type') {
            colors.push(reading.measurement_type);
          }
          
          // Create hover label
          labels.push(`
            デバイスID: ${reading.device_id}<br>
            タイプ: ${reading.device_type}<br>
            測定値: ${reading.value} ${reading.unit}<br>
            場所: ${reading.location || '不明'}<br>
            座標: (${reading.x_position}, ${reading.y_position}, ${reading.z_position})
          `);
        }
      });
      
      // Create plot data
      const data = [{
        type: 'scatter3d',
        mode: 'markers',
        x: xValues,
        y: yValues,
        z: zValues,
        text: labels,
        hoverinfo: 'text',
        marker: {
          size: 8,
          color: colors,
          colorscale: 'Viridis',
          opacity: 0.8,
          colorbar: {
            title: colorBy === 'measurement_type' ? '測定タイプ' : colorBy === 'location' ? '場所' : 'デバイスID'
          }
        }
      }];
      
      // Create layout
      const layout = {
        title: '3Dセンサー位置可視化',
        scene: {
          xaxis: {
            title: 'X座標',
            titlefont: { size: 12 }
          },
          yaxis: {
            title: 'Y座標',
            titlefont: { size: 12 }
          },
          zaxis: {
            title: 'Z座標',
            titlefont: { size: 12 }
          }
        },
        margin: { l: 0, r: 0, b: 0, t: 50, pad: 0 },
        hovermode: 'closest',
        autosize: true
      };
      
      setPlotData(data);
      setPlotLayout(layout);
      return;
    }
    
    // Traditional sensor measurement visualization
    if (!xAxis || !yAxis || !zAxis) {
      setError('X軸、Y軸、Z軸のすべてを選択してください');
      return;
    }

    setError(null);

    // Parse axis selections
    const [, xMeasurementType] = xAxis.split(':');
    const [, yMeasurementType] = yAxis.split(':');
    const [, zMeasurementType] = zAxis.split(':');

    // Group readings by timestamp (approximately)
    const groupedByTime = {};
    
    filteredReadings.forEach(reading => {
      // Round timestamp to nearest minute to group readings
      const timestamp = new Date(reading.timestamp);
      const roundedTime = new Date(
        timestamp.getFullYear(),
        timestamp.getMonth(),
        timestamp.getDate(),
        timestamp.getHours(),
        timestamp.getMinutes()
      ).toISOString();
      
      if (!groupedByTime[roundedTime]) {
        groupedByTime[roundedTime] = {};
      }
      
      const key = `${reading.device_id}:${reading.measurement_type}`;
      groupedByTime[roundedTime][key] = reading;
    });

    // Prepare data for 3D plot
    const xValues = [];
    const yValues = [];
    const zValues = [];
    const colors = [];
    const labels = [];
    const timestamps = [];
    
    // Collect data points where all three measurements exist
    Object.entries(groupedByTime).forEach(([time, readings]) => {
      if (readings[xAxis] && readings[yAxis] && readings[zAxis]) {
        xValues.push(parseFloat(readings[xAxis].value));
        yValues.push(parseFloat(readings[yAxis].value));
        zValues.push(parseFloat(readings[zAxis].value));
        
        // Color by selected attribute
        if (colorBy === 'device_id') {
          colors.push(readings[xAxis].device_id);
        } else if (colorBy === 'location') {
          colors.push(readings[xAxis].location);
        } else if (colorBy === 'time') {
          colors.push(new Date(time).getTime());
        }
        
        // Create hover label
        labels.push(`
          時間: ${new Date(time).toLocaleString()}<br>
          ${xMeasurementType}: ${readings[xAxis].value} ${readings[xAxis].unit}<br>
          ${yMeasurementType}: ${readings[yAxis].value} ${readings[yAxis].unit}<br>
          ${zMeasurementType}: ${readings[zAxis].value} ${readings[zAxis].unit}<br>
          場所: ${readings[xAxis].location}
        `);
        
        timestamps.push(new Date(time));
      }
    });

    // Create plot data
    const data = [{
      type: 'scatter3d',
      mode: 'markers',
      x: xValues,
      y: yValues,
      z: zValues,
      text: labels,
      hoverinfo: 'text',
      marker: {
        size: 5,
        color: colors,
        colorscale: 'Viridis',
        opacity: 0.8,
        colorbar: {
          title: colorBy === 'time' ? '時間' : colorBy === 'location' ? '場所' : 'デバイスID'
        }
      }
    }];

    // Create layout
    const layout = {
      title: '3Dセンサーデータ可視化',
      scene: {
        xaxis: {
          title: `${xMeasurementType} (${getUnit(xAxis)})`,
          titlefont: { size: 12 }
        },
        yaxis: {
          title: `${yMeasurementType} (${getUnit(yAxis)})`,
          titlefont: { size: 12 }
        },
        zaxis: {
          title: `${zMeasurementType} (${getUnit(zAxis)})`,
          titlefont: { size: 12 }
        }
      },
      margin: { l: 0, r: 0, b: 0, t: 50, pad: 0 },
      hovermode: 'closest',
      autosize: true
    };

    setPlotData(data);
    setPlotLayout(layout);
  }, [xAxis, yAxis, zAxis, filteredReadings, colorBy, getUnit]);

  // Generate 3D plot data when axes or filtered readings change
  useEffect(() => {
    if (filteredReadings.length > 0 && xAxis && yAxis && zAxis) {
      try {
        generatePlotData();
      } catch (err) {
        setError(`3Dプロットの生成中にエラーが発生しました: ${err.message}`);
      }
    }
  }, [filteredReadings, xAxis, yAxis, zAxis, colorBy, generatePlotData]);



  // Format time range label
  const formatTimeRangeLabel = (value) => {
    if (!readings || readings.length === 0) return '';
    
    // Sort readings by timestamp
    const sortedReadings = [...readings].sort((a, b) => 
      new Date(a.timestamp) - new Date(b.timestamp)
    );
    
    // Calculate index based on percentage
    const idx = Math.floor(sortedReadings.length * (value / 100));
    if (idx >= sortedReadings.length) return '';
    
    // Format timestamp
    return new Date(sortedReadings[idx].timestamp).toLocaleString();
  };

  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h6" gutterBottom>
        センサーデータ3D可視化
      </Typography>
      
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>可視化モード</InputLabel>
                <Select
                  value={xAxis === 'x_position' && yAxis === 'y_position' && zAxis === 'z_position' ? 'physical' : 'measurements'}
                  label="可視化モード"
                  onChange={(e) => {
                    if (e.target.value === 'physical') {
                      setXAxis('x_position');
                      setYAxis('y_position');
                      setZAxis('z_position');
                      setColorBy('device_id');
                    } else if (sensorOptions.length >= 3) {
                      // デフォルトの測定値を設定
                      setXAxis(sensorOptions[0]);
                      setYAxis(sensorOptions[1]);
                      setZAxis(sensorOptions[2]);
                    }
                  }}
                >
                  <MenuItem value="physical">物理的位置（X,Y,Z座標）</MenuItem>
                  <MenuItem value="measurements">センサー測定値</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            {xAxis !== 'x_position' && (
              <>
                <Grid item xs={12} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>X軸</InputLabel>
                    <Select
                      value={xAxis}
                      label="X軸"
                      onChange={(e) => setXAxis(e.target.value)}
                    >
                      <MenuItem value="">選択してください</MenuItem>
                      {sensorOptions.map(option => (
                        <MenuItem key={`x-${option}`} value={option}>
                          {option.replace(':', ' - ')}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Y軸</InputLabel>
                    <Select
                      value={yAxis}
                      label="Y軸"
                      onChange={(e) => setYAxis(e.target.value)}
                    >
                      <MenuItem value="">選択してください</MenuItem>
                      {sensorOptions.map(option => (
                        <MenuItem key={`y-${option}`} value={option}>
                          {option.replace(':', ' - ')}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Z軸</InputLabel>
                    <Select
                      value={zAxis}
                      label="Z軸"
                      onChange={(e) => setZAxis(e.target.value)}
                    >
                      <MenuItem value="">選択してください</MenuItem>
                      {sensorOptions.map(option => (
                        <MenuItem key={`z-${option}`} value={option}>
                          {option.replace(':', ' - ')}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              </>
            )}
            
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>色分け</InputLabel>
                <Select
                  value={colorBy}
                  label="色分け"
                  onChange={(e) => setColorBy(e.target.value)}
                >
                  <MenuItem value="device_id">デバイスID</MenuItem>
                  <MenuItem value="location">場所</MenuItem>
                  {xAxis === 'x_position' ? (
                    <MenuItem value="measurement_type">測定タイプ</MenuItem>
                  ) : (
                    <MenuItem value="time">時間</MenuItem>
                  )}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Typography gutterBottom>時間範囲</Typography>
              <Slider
                value={timeRange}
                onChange={(e, newValue) => setTimeRange(newValue)}
                valueLabelDisplay="auto"
                valueLabelFormat={value => formatTimeRangeLabel(value)}
                min={0}
                max={100}
                step={1}
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      {plotData.length > 0 ? (
        <Box sx={{ height: 600 }}>
          <Plot
            data={plotData}
            layout={plotLayout}
            config={{
              responsive: true,
              displayModeBar: true,
              displaylogo: false,
              modeBarButtonsToRemove: ['lasso2d', 'select2d']
            }}
            style={{ width: '100%', height: '100%' }}
          />
        </Box>
      ) : (
        <Box sx={{ p: 4, textAlign: 'center' }}>
          <Typography>
            データを表示するには、X軸、Y軸、Z軸を選択してください。
          </Typography>
        </Box>
      )}
      
      <Box sx={{ mt: 3 }}>
        <Typography variant="subtitle2" color="text.secondary">
          注: 3D可視化では、センサーの物理的な位置関係や、異なるセンサー間の測定値の相関関係を視覚的に確認できます。
          「物理的位置」モードではセンサーの実際の配置を、「センサー測定値」モードでは測定値間の関係性を表示します。
          マウスでドラッグして視点を変更したり、ホイールでズームしたりできます。
        </Typography>
      </Box>
    </Box>
  );
};

export default Sensor3DVisualization;
