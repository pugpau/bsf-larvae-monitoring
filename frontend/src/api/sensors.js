import apiClient from './client';

/**
 * Get all sensor data with optional filters
 * @param {Object} params - Query parameters
 * @returns {Promise} - Promise with sensor data
 */
export const getAllSensorData = async (params = {}) => {
  try {
    const response = await apiClient.get('/api/sensors/data', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching all sensor data:', error);
    throw error;
  }
};

/**
 * Get latest sensor data for a specific farm
 * @param {string} farmId - Farm ID
 * @returns {Promise} - Promise with latest sensor data
 */
export const getLatestSensorData = async (farmId) => {
  try {
    const response = await apiClient.get(`/api/sensors/latest/${farmId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching latest sensor data for farm ${farmId}:`, error);
    throw error;
  }
};

/**
 * Get sensor data for a specific device
 * @param {string} farmId - Farm ID
 * @param {string} deviceId - Device ID
 * @param {Object} params - Query parameters
 * @returns {Promise} - Promise with device sensor data
 */
export const getDeviceSensorData = async (farmId, deviceId, params = {}) => {
  try {
    const response = await apiClient.get(`/api/sensors/data/${farmId}/${deviceId}`, { params });
    return response.data;
  } catch (error) {
    console.error(`Error fetching sensor data for device ${deviceId}:`, error);
    throw error;
  }
};
