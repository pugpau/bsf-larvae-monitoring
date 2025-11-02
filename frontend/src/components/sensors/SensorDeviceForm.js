import React, { useState, useEffect } from 'react';
import { registerSensorDevice, updateSensorDevice } from '../../api/devices';
import './SensorDeviceForm.css';

/**
 * SensorDeviceForm Component
 * 
 * Form for registering or updating sensor devices.
 * Allows users to input device details and submit to the API.
 */
const SensorDeviceForm = ({ farmId, onSubmitSuccess, initialData }) => {
  const [formData, setFormData] = useState({
    deviceId: '',
    deviceType: '',
    location: '',
    description: '',
    ...initialData
  });
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (initialData) {
      setFormData({
        deviceId: '',
        deviceType: '',
        location: '',
        description: '',
        ...initialData
      });
    }
  }, [initialData]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      if (initialData) {
        await updateSensorDevice(farmId, formData.deviceId, formData);
      } else {
        await registerSensorDevice(farmId, formData);
      }
      
      if (!initialData) {
        setFormData({
          deviceId: '',
          deviceType: '',
          location: '',
          description: ''
        });
      }
      
      setSuccess(true);
      
      if (onSubmitSuccess) {
        onSubmitSuccess();
      }
    } catch (err) {
      console.error('Error registering device:', err);
      setError(initialData 
        ? 'Failed to update device. Please try again.' 
        : 'Failed to register device. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="sensor-device-form-container">
      <h2>{initialData ? 'Update Sensor Device' : 'Register New Sensor Device'}</h2>
      
      {error && (
        <div className="form-error-message">{error}</div>
      )}
      
      {success && (
        <div className="form-success-message">
          {initialData ? 'Device updated successfully!' : 'Device registered successfully!'}
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="sensor-device-form">
        <div className="form-group">
          <label htmlFor="deviceId">Device ID</label>
          <input
            type="text"
            id="deviceId"
            name="deviceId"
            value={formData.deviceId}
            onChange={handleChange}
            required
            disabled={loading || (initialData && initialData.deviceId)}
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="deviceType">Device Type</label>
          <select
            id="deviceType"
            name="deviceType"
            value={formData.deviceType}
            onChange={handleChange}
            required
            disabled={loading}
          >
            <option value="">Select Device Type</option>
            <option value="temperature">Temperature Sensor</option>
            <option value="humidity">Humidity Sensor</option>
            <option value="pressure">Pressure Sensor</option>
            <option value="gas">Gas Sensor</option>
            <option value="multi">Multi-sensor</option>
          </select>
        </div>
        
        <div className="form-group">
          <label htmlFor="location">Location</label>
          <input
            type="text"
            id="location"
            name="location"
            value={formData.location}
            onChange={handleChange}
            required
            disabled={loading}
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            rows="3"
            disabled={loading}
          />
        </div>
        
        <div className="form-actions">
          <button 
            type="submit" 
            className="submit-button"
            disabled={loading}
          >
            {loading ? 'Processing...' : initialData ? 'Update Device' : 'Register Device'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default SensorDeviceForm;
