import React, { useRef, useEffect } from 'react';
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
} from '@mui/material';
import { ExpandMore as ExpandMoreIcon } from '@mui/icons-material';
import type { ChatMessage } from '../../types/api';

interface ChatMessageListProps {
  messages: ChatMessage[];
  loading?: boolean;
}

const TypingIndicator: React.FC = () => (
  <Box
    sx={{
      display: 'flex',
      gap: 0.5,
      p: 1.5,
      '@keyframes blink': {
        '0%, 80%, 100%': { opacity: 0.3 },
        '40%': { opacity: 1 },
      },
    }}
  >
    {[0, 1, 2].map((i) => (
      <Box
        key={i}
        sx={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          backgroundColor: 'grey.400',
          animation: 'blink 1.4s infinite',
          animationDelay: `${i * 0.2}s`,
        }}
      />
    ))}
  </Box>
);

const MessageBubble: React.FC<{ message: ChatMessage }> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        mb: 1.5,
      }}
    >
      <Box
        sx={{
          maxWidth: '85%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: isUser ? 'flex-end' : 'flex-start',
        }}
      >
        <Box
          sx={{
            px: 2,
            py: 1.5,
            borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
            backgroundColor: isUser ? 'primary.main' : 'grey.100',
            color: isUser ? 'white' : 'text.primary',
          }}
        >
          <Typography
            variant="body2"
            sx={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              lineHeight: 1.6,
            }}
          >
            {message.content}
          </Typography>
        </Box>

        {/* Context references */}
        {!isUser && message.context_chunks && message.context_chunks.length > 0 && (
          <Accordion
            disableGutters
            elevation={0}
            sx={{
              mt: 0.5,
              maxWidth: '100%',
              backgroundColor: 'transparent',
              '&::before': { display: 'none' },
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon sx={{ fontSize: '1rem' }} />}
              sx={{
                minHeight: 28,
                px: 1,
                '& .MuiAccordionSummary-content': { my: 0 },
              }}
            >
              <Chip
                label={`参照: ${message.context_chunks.length}件`}
                size="small"
                variant="outlined"
                sx={{ height: 22, fontSize: '0.7rem' }}
              />
            </AccordionSummary>
            <AccordionDetails sx={{ px: 1, pt: 0 }}>
              {message.context_chunks.map((chunk, idx) => (
                <Box
                  key={idx}
                  sx={{
                    mb: 1,
                    p: 1,
                    borderRadius: 1,
                    backgroundColor: 'grey.50',
                    border: '1px solid',
                    borderColor: 'divider',
                  }}
                >
                  <Typography
                    variant="caption"
                    sx={{ fontWeight: 600, color: 'primary.main', display: 'block', mb: 0.5 }}
                  >
                    {chunk.title}
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{ color: 'text.secondary', lineHeight: 1.5 }}
                  >
                    {chunk.content.length > 150
                      ? `${chunk.content.slice(0, 150)}...`
                      : chunk.content}
                  </Typography>
                </Box>
              ))}
            </AccordionDetails>
          </Accordion>
        )}

        {/* Timestamp */}
        {message.created_at && (
          <Typography
            variant="caption"
            sx={{ color: 'text.disabled', mt: 0.25, px: 0.5, fontSize: '0.65rem' }}
          >
            {new Date(message.created_at).toLocaleTimeString('ja-JP', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </Typography>
        )}
      </Box>
    </Box>
  );
};

const ChatMessageList: React.FC<ChatMessageListProps> = ({ messages, loading = false }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  return (
    <Box
      sx={{
        flex: 1,
        overflowY: 'auto',
        px: 2,
        py: 1,
      }}
    >
      {messages.length === 0 && !loading && (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: 'text.disabled',
          }}
        >
          <Typography variant="h3" sx={{ mb: 1, opacity: 0.4, fontSize: '2rem' }}>
            AI
          </Typography>
          <Typography variant="body2">
            BSF飼育・配合に関する質問をどうぞ
          </Typography>
        </Box>
      )}

      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 1.5 }}>
          <Box
            sx={{
              borderRadius: '16px 16px 16px 4px',
              backgroundColor: 'grey.100',
            }}
          >
            <TypingIndicator />
          </Box>
        </Box>
      )}

      <div ref={bottomRef} />
    </Box>
  );
};

export default ChatMessageList;
