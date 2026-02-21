import React, { useState } from 'react';
import { Fab, Tooltip } from '@mui/material';
import { SmartToy as SmartToyIcon } from '@mui/icons-material';
import ChatDrawer from './ChatDrawer';
import { useReducedMotion } from '../../hooks/useReducedMotion';

const ChatFab: React.FC = () => {
  const [open, setOpen] = useState(false);
  const prefersReduced = useReducedMotion();

  return (
    <>
      <Tooltip title="AIアシスタント" placement="left">
        <Fab
          color="primary"
          onClick={() => setOpen(true)}
          aria-label="AIチャットを開く"
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            width: 56,
            height: 56,
            boxShadow: '0 4px 12px rgba(30, 64, 175, 0.3)',
            transition: prefersReduced ? 'none' : 'transform 200ms ease, box-shadow 200ms ease',
            '&:hover': {
              transform: prefersReduced ? 'none' : 'scale(1.05)',
              boxShadow: '0 6px 16px rgba(30, 64, 175, 0.4)',
            },
            zIndex: 1100,
          }}
        >
          <SmartToyIcon />
        </Fab>
      </Tooltip>
      <ChatDrawer open={open} onClose={() => setOpen(false)} />
    </>
  );
};

export default ChatFab;
