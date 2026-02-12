import React from 'react';
import { Snackbar, Alert } from '@mui/material';

interface NotificationSnackbarProps {
  open: boolean;
  message: string;
  severity: 'success' | 'error' | 'warning' | 'info';
  onClose: () => void;
}

const NotificationSnackbar: React.FC<NotificationSnackbarProps> = ({
  open, message, severity, onClose,
}) => (
  <Snackbar open={open} autoHideDuration={3000} onClose={onClose}>
    <Alert severity={severity} variant="filled">{message}</Alert>
  </Snackbar>
);

export default NotificationSnackbar;
