import React from 'react';
import { render, screen } from '@testing-library/react';
import SensorDeviceList from './SensorDeviceList';

jest.mock('../../api/sensors', () => ({
  getLatestSensorData: jest.fn().mockResolvedValue({}),
  getAllSensorData: jest.fn().mockResolvedValue([])
}));

describe('SensorDeviceList', () => {
  it('renders loading state initially', () => {
    render(<SensorDeviceList />);
    expect(screen.getByText(/Loading sensor data/i)).toBeInTheDocument();
  });
});
