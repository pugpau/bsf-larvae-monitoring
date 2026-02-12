import React, { useState, useCallback } from 'react';
import {
  Box,
  TextField,
  IconButton,
  CircularProgress,
} from '@mui/material';
import { Send as SendIcon } from '@mui/icons-material';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  loading?: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled = false, loading = false }) => {
  const [value, setValue] = useState('');

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled || loading) return;
    onSend(trimmed);
    setValue('');
  }, [value, disabled, loading, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'flex-end',
        gap: 1,
        p: 2,
        borderTop: '1px solid',
        borderColor: 'divider',
        backgroundColor: 'background.paper',
      }}
    >
      <TextField
        fullWidth
        multiline
        maxRows={3}
        size="small"
        placeholder="質問を入力..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled || loading}
        sx={{
          '& .MuiOutlinedInput-root': {
            borderRadius: '20px',
            fontSize: '0.875rem',
          },
        }}
      />
      <IconButton
        color="primary"
        onClick={handleSend}
        disabled={!value.trim() || disabled || loading}
        aria-label="送信"
        sx={{
          backgroundColor: 'primary.main',
          color: 'white',
          width: 40,
          height: 40,
          '&:hover': { backgroundColor: 'primary.dark' },
          '&.Mui-disabled': { backgroundColor: 'grey.300', color: 'grey.500' },
        }}
      >
        {loading ? <CircularProgress size={20} color="inherit" /> : <SendIcon fontSize="small" />}
      </IconButton>
    </Box>
  );
};

export default ChatInput;
