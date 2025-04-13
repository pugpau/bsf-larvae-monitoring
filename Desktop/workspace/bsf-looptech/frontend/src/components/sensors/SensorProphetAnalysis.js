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
 * SensorProphetAnalysis component
 * 
 * This component provides time series forecasting visualization using Prophet-like algorithms
 * implemented on the client side. Since we can't run actual Prophet (Python) in the browser,
 * this component simulates Prophet's functionality with JavaScript.
 */
const SensorProphetAnalysis = ({ readings }) => {
  // State for selected sensor and forecast parameters
  const [selectedSensor, setSelectedSensor] = useState('');
  const [forecastDays, setForecastDays] = useState(7);
  const [seasonalityMode, setSeasonalityMode] = useState('additive');
  const [changepoints, setChangepoints] = useState(25);
  const [sensors, setSensors] = useState([]);
  const [forecastData, setForecastData] = useState(null);
  const [originalData, setOriginalData] = useState([]);
  const [error, setError] = useState(null);

  // Extract unique sensors from readings
  useEffect(() => {
    if (readings && readings.length > 0) {
      // Get unique device_id + measurement_type combinations
      const uniqueSensors = [...new Set(readings.map(r => `${r.device_id}:${r.measurement_type}`))];
      setSensors(uniqueSensors);
    }
  }, [readings]);

  // Handle sensor selection change
  const handleSensorChange = (event) => {
    setSelectedSensor(event.target.value);
    
    if (event.target.value) {
      const [deviceId, measurementType] = event.target.value.split(':');
      
      // Filter readings for selected sensor
      const filteredReadings = readings.filter(
        r => r.device_id === deviceId && r.measurement_type === measurementType
      );
      
      // Sort by timestamp
      filteredReadings.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
      
      // Set original data for visualization
      setOriginalData(filteredReadings.map(r => ({
        x: new Date(r.timestamp),
        y: parseFloat(r.value)
      })));
    } else {
      setOriginalData([]);
    }
  };

  // Helper function: Calculate moving average
  const calculateMovingAverage = useCallback((data, windowSize) => {
    const result = [];
    for (let i = 0; i < data.length; i++) {
      let sum = 0;
      let count = 0;
      for (let j = Math.max(0, i - windowSize); j <= Math.min(data.length - 1, i + windowSize); j++) {
        sum += data[j];
        count++;
      }
      result.push(sum / count);
    }
    return result;
  }, []);

  // Helper function: Extract seasonality
  const extractSeasonality = useCallback((data, period) => {
    const seasonality = Array(period).fill(0);
    const counts = Array(period).fill(0);
    
    // Sum values by position in cycle
    for (let i = 0; i < data.length; i++) {
      const position = i % period;
      seasonality[position] += data[i];
      counts[position]++;
    }
    
    // Calculate average for each position
    for (let i = 0; i < period; i++) {
      if (counts[i] > 0) {
        seasonality[i] /= counts[i];
      }
    }
    
    // Normalize to have zero mean
    const mean = seasonality.reduce((sum, val) => sum + val, 0) / period;
    return seasonality.map(s => s - mean);
  }, []);

  // Helper function: Forecast trend
  const forecastTrend = useCallback((values, trend, forecastLength) => {
    // Simple linear regression for trend
    const n = values.length;
    const xMean = (n - 1) / 2;
    const yMean = trend.reduce((sum, val) => sum + val, 0) / n;
    
    let numerator = 0;
    let denominator = 0;
    
    for (let i = 0; i < n; i++) {
      numerator += (i - xMean) * (trend[i] - yMean);
      denominator += Math.pow(i - xMean, 2);
    }
    
    const slope = denominator !== 0 ? numerator / denominator : 0;
    const intercept = yMean - slope * xMean;
    
    // Generate future trend
    const futureTrend = [];
    for (let i = 0; i < forecastLength; i++) {
      futureTrend.push(intercept + slope * (n + i));
    }
    
    return futureTrend;
  }, []);

  // Helper function: Calculate standard deviation
  const calculateStdDev = useCallback((data) => {
    const mean = data.reduce((sum, val) => sum + val, 0) / data.length;
    const squaredDiffs = data.map(val => Math.pow(val - mean, 2));
    const variance = squaredDiffs.reduce((sum, val) => sum + val, 0) / data.length;
    return Math.sqrt(variance);
  }, []);

  // Generate forecast using a simplified model (Prophet-like)
  const generateForecast = useCallback(() => {
    if (originalData.length < 5) {
      setError('予測には少なくとも5つのデータポイントが必要です');
      return;
    }

    setError(null);

    // Extract x and y values
    const dates = originalData.map(d => d.x);
    const values = originalData.map(d => d.y);

    // Calculate trend using moving average
    const windowSize = Math.max(2, Math.floor(values.length / 10));
    const trend = calculateMovingAverage(values, windowSize);

    // Identify seasonality if enough data points
    let seasonality = Array(values.length).fill(0);
    if (values.length >= 24) { // At least a day of data (assuming hourly)
      seasonality = extractSeasonality(values, 24); // 24-hour seasonality
    }

    // Calculate residuals
    const residuals = values.map((v, i) => v - trend[i] - (seasonalityMode === 'additive' ? seasonality[i] : trend[i] * seasonality[i]));

    // Generate future dates
    const lastDate = dates[dates.length - 1];
    const futureDates = [];
    for (let i = 1; i <= forecastDays * 24; i++) { // Assuming hourly data
      const futureDate = new Date(lastDate);
      futureDate.setHours(futureDate.getHours() + i);
      futureDates.push(futureDate);
    }

    // Forecast trend (simple linear extrapolation)
    const futureTrend = forecastTrend(values, trend, futureDates.length);

    // Apply seasonality to forecast
    const futureSeasonality = [];
    for (let i = 0; i < futureDates.length; i++) {
      const hourOfDay = futureDates[i].getHours();
      const seasonalIndex = hourOfDay % 24;
      futureSeasonality.push(seasonality[seasonalIndex] || 0);
    }

    // Combine components for final forecast
    const forecastValues = futureTrend.map((t, i) => {
      return seasonalityMode === 'additive' 
        ? t + futureSeasonality[i]
        : t * (1 + futureSeasonality[i]);
    });

    // Calculate confidence intervals (simple approach)
    const stdDev = calculateStdDev(residuals);
    const upperBound = forecastValues.map(v => v + 1.96 * stdDev);
    const lowerBound = forecastValues.map(v => v - 1.96 * stdDev);

    // Set forecast data for visualization
    setForecastData({
      dates: futureDates,
      forecast: forecastValues,
      upper: upperBound,
      lower: lowerBound
    });
  }, [originalData, forecastDays, seasonalityMode, calculateMovingAverage, extractSeasonality, forecastTrend, calculateStdDev]);

  // Generate forecast when parameters change
  useEffect(() => {
    if (originalData.length > 0) {
      try {
        generateForecast();
      } catch (err) {
        setError(`予測の生成中にエラーが発生しました: ${err.message}`);
        setForecastData(null);
      }
    }
  }, [originalData, forecastDays, seasonalityMode, changepoints, generateForecast]);

  // Get unit based on selected sensor - wrapped in useCallback
  const getUnit = useCallback(() => {
    if (!selectedSensor) return '';
    
    const [deviceId, measurementType] = selectedSensor.split(':');
    const reading = readings.find(
      r => r.device_id === deviceId && r.measurement_type === measurementType
    );
    
    return reading ? reading.unit : '';
  }, [selectedSensor, readings]);

  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h6" gutterBottom>
        センサーデータ予測分析 (Prophet風)
      </Typography>
      
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel>センサー</InputLabel>
                <Select
                  value={selectedSensor}
                  label="センサー"
                  onChange={handleSensorChange}
                >
                  <MenuItem value="">選択してください</MenuItem>
                  {sensors.map(sensor => (
                    <MenuItem key={sensor} value={sensor}>
                      {sensor.replace(':', ' - ')}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Typography gutterBottom>予測期間 (日)</Typography>
              <Slider
                value={forecastDays}
                onChange={(e, newValue) => setForecastDays(newValue)}
                step={1}
                marks
                min={1}
                max={30}
                valueLabelDisplay="auto"
              />
            </Grid>
            
            <Grid item xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel>季節性モード</InputLabel>
                <Select
                  value={seasonalityMode}
                  label="季節性モード"
                  onChange={(e) => setSeasonalityMode(e.target.value)}
                >
                  <MenuItem value="additive">加法的 (Additive)</MenuItem>
                  <MenuItem value="multiplicative">乗法的 (Multiplicative)</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12}>
              <Typography gutterBottom>変化点の柔軟性</Typography>
              <Slider
                value={changepoints}
                onChange={(e, newValue) => setChangepoints(newValue)}
                step={5}
                marks
                min={5}
                max={50}
                valueLabelDisplay="auto"
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
      
      {selectedSensor && (
        <Box sx={{ height: 500 }}>
          <Plot
            data={[
              // Historical data
              {
                x: originalData.map(d => d.x),
                y: originalData.map(d => d.y),
                type: 'scatter',
                mode: 'lines+markers',
                name: '実測値',
                line: { color: 'blue' },
                marker: { size: 5 }
              },
              // Forecast
              ...(forecastData ? [
                {
                  x: forecastData.dates,
                  y: forecastData.forecast,
                  type: 'scatter',
                  mode: 'lines',
                  name: '予測値',
                  line: { color: 'red', dash: 'dash' }
                },
                // Upper bound
                {
                  x: forecastData.dates,
                  y: forecastData.upper,
                  type: 'scatter',
                  mode: 'lines',
                  name: '上限 (95%信頼区間)',
                  line: { width: 0 },
                  marker: { color: 'rgba(255, 0, 0, 0)' },
                  showlegend: false
                },
                // Lower bound
                {
                  x: forecastData.dates,
                  y: forecastData.lower,
                  type: 'scatter',
                  mode: 'lines',
                  name: '下限 (95%信頼区間)',
                  line: { width: 0 },
                  marker: { color: 'rgba(255, 0, 0, 0)' },
                  fill: 'tonexty',
                  fillcolor: 'rgba(255, 0, 0, 0.2)',
                  showlegend: false
                }
              ] : [])
            ]}
            layout={{
              title: `${selectedSensor.replace(':', ' - ')} の予測分析`,
              xaxis: {
                title: '時間',
                tickformat: '%Y-%m-%d %H:%M'
              },
              yaxis: {
                title: getUnit()
              },
              hovermode: 'closest',
              autosize: true,
              margin: { l: 50, r: 50, b: 100, t: 50, pad: 4 }
            }}
            config={{
              responsive: true,
              displayModeBar: true,
              displaylogo: false,
              modeBarButtonsToRemove: ['lasso2d', 'select2d']
            }}
            style={{ width: '100%', height: '100%' }}
          />
        </Box>
      )}
      
      <Box sx={{ mt: 3 }}>
        <Typography variant="subtitle2" color="text.secondary">
          注: このコンポーネントはFacebookのProphetアルゴリズムを模倣していますが、
          ブラウザ上でJavaScriptを使用して実装されているため、実際のProphetの精度とは異なります。
          より高度な分析には、バックエンドでPythonのProphetライブラリを使用することをお勧めします。
        </Typography>
      </Box>
    </Box>
  );
};

export default SensorProphetAnalysis;
