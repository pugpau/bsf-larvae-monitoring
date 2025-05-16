import api from './index';

/**
 * Get all sensor data with optional filters
 * @param {Object} params - Query parameters
 * @returns {Promise<Array>} Array of sensor data
 */
export const getSensorData = async (params = {}) => {
  try {
    const response = await api.get('/sensors/data', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching sensor data:', error);
    throw error;
  }
};

/**
 * Get sensor data for a specific device
 * @param {string} farmId - Farm ID
 * @param {string} deviceId - Device ID
 * @param {Object} params - Additional query parameters
 * @returns {Promise<Array>} Array of sensor data
 */
export const getDeviceSensorData = async (farmId, deviceId, params = {}) => {
  try {
    const response = await api.get(`/sensors/data/${farmId}/${deviceId}`, { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching device sensor data:', error);
    throw error;
  }
};

/**
 * Get the latest sensor readings for all devices in a farm
 * @param {string} farmId - Farm ID
 * @returns {Promise<Object>} Latest sensor readings
 */
export const getLatestFarmData = async (farmId) => {
  try {
    const response = await api.get(`/sensors/latest/${farmId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching latest farm data:', error);
    throw error;
  }
};
