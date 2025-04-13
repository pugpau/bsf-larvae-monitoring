import apiClient from './client';

/**
 * Register a new sensor device
 * @param {string} farmId - Farm ID
 * @param {Object} deviceData - Device data
 * @returns {Promise} - Promise with registration result
 */
export const registerSensorDevice = async (farmId, deviceData) => {
  try {
    const response = await apiClient.post(`/api/sensors/devices/${farmId}`, deviceData);
    return response.data;
  } catch (error) {
    console.error(`Error registering sensor device:`, error);
    throw error;
  }
};

/**
 * Update an existing sensor device
 * @param {string} farmId - Farm ID
 * @param {string} deviceId - Device ID
 * @param {Object} deviceData - Updated device data
 * @returns {Promise} - Promise with update result
 */
export const updateSensorDevice = async (farmId, deviceId, deviceData) => {
  try {
    const response = await apiClient.put(`/api/sensors/devices/${farmId}/${deviceId}`, deviceData);
    return response.data;
  } catch (error) {
    console.error(`Error updating sensor device ${deviceId}:`, error);
    throw error;
  }
};

/**
 * Delete a sensor device
 * @param {string} farmId - Farm ID
 * @param {string} deviceId - Device ID
 * @returns {Promise} - Promise with deletion result
 */
export const deleteSensorDevice = async (farmId, deviceId) => {
  try {
    const response = await apiClient.delete(`/api/sensors/devices/${farmId}/${deviceId}`);
    return response.data;
  } catch (error) {
    console.error(`Error deleting sensor device ${deviceId}:`, error);
    throw error;
  }
};
