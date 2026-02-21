import { useState, useCallback } from 'react';

type Severity = 'success' | 'error' | 'warning' | 'info';

interface NotificationState {
  open: boolean;
  message: string;
  severity: Severity;
}

interface UseNotificationReturn {
  notification: NotificationState;
  notify: (message: string, severity?: Severity) => void;
  closeNotification: () => void;
}

export function useNotification(): UseNotificationReturn {
  const [notification, setNotification] = useState<NotificationState>({
    open: false,
    message: '',
    severity: 'success',
  });

  const notify = useCallback((message: string, severity: Severity = 'success') => {
    setNotification({ open: true, message, severity });
  }, []);

  const closeNotification = useCallback(() => {
    setNotification(prev => ({ ...prev, open: false }));
  }, []);

  return { notification, notify, closeNotification };
}
