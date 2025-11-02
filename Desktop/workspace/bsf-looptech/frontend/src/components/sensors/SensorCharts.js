import React, { useState, useEffect } from 'react';
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
  Tab
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
// Import date-fns locale
import { ja } from 'date-fns/locale';

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

// Background colors with opacity
const BACKGROUND_COLORS = COLORS.map(color => color.replace('1)', '0.2)'));

const SensorCharts = ({ readings }) => {
  const [chartType, setChartType] = useState('time'); // 'time' or 'comparison'
  const [selectedTab, setSelectedTab] = useState(0);
  const [selectedLocation, setSelectedLocation] = useState('all');
  const [locations, setLocations] = useState([]);
  const [measurementTypes, setMeasurementTypes] = useState([]);
  const [chartData, setChartData] = useState({});

  // Extract unique locations and measurement types from readings
  useEffect(() => {
    if (readings && readings.length > 0) {
      // Extract unique locations
      const uniqueLocations = [...new Set(readings.map(reading => reading.location))].filter(Boolean);
      setLocations(uniqueLocations);
      
      // Extract unique measurement types
      const uniqueMeasurementTypes = [...new Set(readings.map(reading => reading.measurement_type))].filter(Boolean);
      setMeasurementTypes(uniqueMeasurementTypes);
      
      // Process data for charts
      processChartData(readings, selectedLocation, chartType);
    }
  }, [readings, selectedLocation, chartType]);

  // Process data for charts
  const processChartData = (readings, location, chartType) => {
    if (!readings || readings.length === 0) return;

    // Filter readings by location if needed
    const filteredReadings = location === 'all' 
      ? readings 
      : readings.filter(reading => reading.location === location);

    // Group readings by measurement type
    const groupedByMeasurementType = {};
    
    filteredReadings.forEach(reading => {
      const measurementType = reading.measurement_type;
      if (!groupedByMeasurementType[measurementType]) {
        groupedByMeasurementType[measurementType] = [];
      }
      groupedByMeasurementType[measurementType].push(reading);
    });

    // Create chart data for each measurement type
    const newChartData = {};
    
    Object.keys(groupedByMeasurementType).forEach(measurementType => {
      const readings = groupedByMeasurementType[measurementType];
      
      if (chartType === 'time') {
        // Time series chart - group by device
        const groupedByDevice = {};
        
        readings.forEach(reading => {
          const deviceId = reading.device_id;
          if (!groupedByDevice[deviceId]) {
            groupedByDevice[deviceId] = [];
          }
          groupedByDevice[deviceId].push(reading);
        });
        
        // Sort readings by timestamp for each device
        Object.keys(groupedByDevice).forEach(deviceId => {
          groupedByDevice[deviceId].sort((a, b) => 
            new Date(a.timestamp) - new Date(b.timestamp)
          );
        });
        
        // Create chart data
        newChartData[measurementType] = {
          labels: readings.length > 0 ? readings.map(reading => new Date(reading.timestamp)) : [],
          datasets: Object.keys(groupedByDevice).map((deviceId, index) => {
            const deviceReadings = groupedByDevice[deviceId];
            return {
              label: `${deviceId} (${deviceReadings[0]?.location || 'Unknown'})`,
              data: deviceReadings.map(reading => ({
                x: new Date(reading.timestamp),
                y: parseFloat(reading.value)
              })),
              borderColor: COLORS[index % COLORS.length],
              backgroundColor: BACKGROUND_COLORS[index % BACKGROUND_COLORS.length],
              tension: 0.1,
              pointRadius: 2,
              pointHoverRadius: 5,
            };
          })
        };
      } else {
        // Comparison chart - latest reading for each device
        const latestReadingsByDevice = {};
        
        readings.forEach(reading => {
          const deviceId = reading.device_id;
          if (!latestReadingsByDevice[deviceId] || 
              new Date(reading.timestamp) > new Date(latestReadingsByDevice[deviceId].timestamp)) {
            latestReadingsByDevice[deviceId] = reading;
          }
        });
        
        // Create chart data
        newChartData[measurementType] = {
          labels: Object.keys(latestReadingsByDevice),
          datasets: [{
            label: measurementType,
            data: Object.values(latestReadingsByDevice).map(reading => parseFloat(reading.value)),
            backgroundColor: Object.keys(latestReadingsByDevice).map((_, index) => 
              BACKGROUND_COLORS[index % BACKGROUND_COLORS.length]
            ),
            borderColor: Object.keys(latestReadingsByDevice).map((_, index) => 
              COLORS[index % COLORS.length]
            ),
            borderWidth: 1,
          }]
        };
      }
    });
    
    setChartData(newChartData);
  };

  // Handle chart type change
  const handleChartTypeChange = (event, newChartType) => {
    if (newChartType !== null) {
      setChartType(newChartType);
    }
  };

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue);
  };

  // Handle location change
  const handleLocationChange = (event) => {
    setSelectedLocation(event.target.value);
  };

  // Chart options
  const getChartOptions = (measurementType) => {
    let unit = '';
    
    // Set unit based on measurement type
    if (measurementType === 'temperature') {
      unit = '°C';
    } else if (measurementType === 'humidity') {
      unit = '%RH';
    } else if (measurementType === 'pressure') {
      unit = 'hPa';
    }
    
    const options = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
        },
        title: {
          display: true,
          text: `${measurementType.charAt(0).toUpperCase() + measurementType.slice(1)} Readings`,
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
      }
    };
    
    // Add time scale for time series charts
    if (chartType === 'time') {
      options.scales.x = {
        type: 'time',
        time: {
          unit: 'hour',
          displayFormats: {
            hour: 'MM/dd HH:mm'
          },
          tooltipFormat: 'yyyy/MM/dd HH:mm'
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
    }
    
    return options;
  };

  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h6" gutterBottom>
        センサーデータ可視化
      </Typography>
      
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} sm={6} md={4}>
          <FormControl fullWidth>
            <InputLabel>場所</InputLabel>
            <Select
              value={selectedLocation}
              label="場所"
              onChange={handleLocationChange}
            >
              <MenuItem value="all">すべての場所</MenuItem>
              {locations.map(location => (
                <MenuItem key={location} value={location}>{location}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <ToggleButtonGroup
            value={chartType}
            exclusive
            onChange={handleChartTypeChange}
            aria-label="chart type"
            fullWidth
          >
            <ToggleButton value="time" aria-label="time series">
              時系列
            </ToggleButton>
            <ToggleButton value="comparison" aria-label="comparison">
              比較
            </ToggleButton>
          </ToggleButtonGroup>
        </Grid>
      </Grid>
      
      {measurementTypes.length > 0 ? (
        <>
          <Tabs 
            value={selectedTab} 
            onChange={handleTabChange} 
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
                height: 400
              }}
            >
              {chartData[type] ? (
                <Line 
                  data={chartData[type]} 
                  options={getChartOptions(type)} 
                />
              ) : (
                <Typography>データがありません</Typography>
              )}
            </Box>
          ))}
        </>
      ) : (
        <Typography>データがありません</Typography>
      )}
    </Box>
  );
};

export default SensorCharts;
