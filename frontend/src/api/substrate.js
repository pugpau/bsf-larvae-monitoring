import api from './index';

/**
 * Get all substrate types
 * @returns {Promise<Array>} Array of substrate types
 */
export const getAllSubstrateTypes = async () => {
  try {
    const response = await api.get('/substrate/types');
    return response.data;
  } catch (error) {
    console.error('Error fetching substrate types:', error);
    throw error;
  }
};

/**
 * Get a substrate type by ID
 * @param {string} id - Substrate type ID
 * @returns {Promise<Object>} Substrate type
 */
export const getSubstrateType = async (id) => {
  try {
    const response = await api.get(`/substrate/types/${id}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching substrate type:', error);
    throw error;
  }
};

/**
 * Create a new substrate type
 * @param {Object} data - Substrate type data
 * @returns {Promise<Object>} Created substrate type
 */
export const createSubstrateType = async (data) => {
  try {
    const response = await api.post('/substrate/types', data);
    return response.data;
  } catch (error) {
    console.error('Error creating substrate type:', error);
    throw error;
  }
};

/**
 * Get substrate batches for a farm
 * @param {string} farmId - Farm ID
 * @param {boolean} activeOnly - Filter for active batches only
 * @returns {Promise<Array>} Array of substrate batches
 */
export const getSubstrateBatches = async (farmId, activeOnly = false) => {
  try {
    const response = await api.get('/substrate/batches', { 
      params: { farm_id: farmId, active_only: activeOnly } 
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching substrate batches:', error);
    throw error;
  }
};

/**
 * Get a substrate batch by ID
 * @param {string} id - Substrate batch ID
 * @returns {Promise<Object>} Substrate batch
 */
export const getSubstrateBatch = async (id) => {
  try {
    const response = await api.get(`/substrate/batches/${id}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching substrate batch:', error);
    throw error;
  }
};

/**
 * Create a new substrate batch
 * @param {Object} data - Substrate batch data
 * @returns {Promise<Object>} Created substrate batch
 */
export const createSubstrateBatch = async (data) => {
  try {
    const response = await api.post('/substrate/batches', data);
    return response.data;
  } catch (error) {
    console.error('Error creating substrate batch:', error);
    throw error;
  }
};

/**
 * Update a substrate batch
 * @param {string} id - Substrate batch ID
 * @param {Object} data - Update data
 * @returns {Promise<boolean>} Success status
 */
export const updateSubstrateBatch = async (id, data) => {
  try {
    const response = await api.patch(`/substrate/batches/${id}`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating substrate batch:', error);
    throw error;
  }
};

/**
 * Update the status of a substrate batch
 * @param {string} id - Substrate batch ID
 * @param {Object} data - Status update data
 * @returns {Promise<boolean>} Success status
 */
export const updateBatchStatus = async (id, data) => {
  try {
    const response = await api.patch(`/substrate/batches/${id}/status`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating batch status:', error);
    throw error;
  }
};

/**
 * Get the change history for a substrate batch
 * @param {string} id - Substrate batch ID
 * @returns {Promise<Array>} Batch change history
 */
export const getBatchHistory = async (id) => {
  try {
    const response = await api.get(`/substrate/batches/${id}/history`);
    return response.data;
  } catch (error) {
    console.error('Error fetching batch history:', error);
    throw error;
  }
};
