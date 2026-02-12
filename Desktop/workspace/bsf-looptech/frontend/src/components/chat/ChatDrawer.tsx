import React, { useState, useEffect, useCallback } from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Divider,
  Button,
  Menu,
  MenuItem,
  Snackbar,
  Alert,
} from '@mui/material';
import {
  Close as CloseIcon,
  Add as AddIcon,
  ArrowBack as ArrowBackIcon,
  MoreVert as MoreVertIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import type { ChatSession, ChatMessage, ChatResponse } from '../../types/api';
import {
  createChatSession,
  fetchChatSessions,
  fetchChatSession,
  deleteChatSession,
  askChat,
} from '../../utils/apiClient';
import ChatMessageList from './ChatMessageList';
import ChatInput from './ChatInput';

interface ChatDrawerProps {
  open: boolean;
  onClose: () => void;
}

type View = 'sessions' | 'chat';

const DRAWER_WIDTH = 420;

const ChatDrawer: React.FC<ChatDrawerProps> = ({ open, onClose }) => {
  const [view, setView] = useState<View>('sessions');
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error',
  });

  // Load sessions when drawer opens
  const loadSessions = useCallback(async () => {
    try {
      const data = await fetchChatSessions();
      setSessions(data);
    } catch {
      setSnackbar({ open: true, message: 'セッション一覧の取得に失敗しました', severity: 'error' });
    }
  }, []);

  useEffect(() => {
    if (open) {
      loadSessions();
    }
  }, [open, loadSessions]);

  // Load session messages
  const openSession = useCallback(async (sessionId: string) => {
    setActiveSessionId(sessionId);
    setView('chat');
    setMessagesLoading(true);
    try {
      const detail = await fetchChatSession(sessionId);
      setMessages(detail.messages || []);
    } catch {
      setSnackbar({ open: true, message: 'メッセージの取得に失敗しました', severity: 'error' });
    } finally {
      setMessagesLoading(false);
    }
  }, []);

  // Create new session and open it
  const handleNewSession = useCallback(async () => {
    try {
      const session = await createChatSession();
      setSessions((prev) => [session, ...prev]);
      await openSession(session.id);
    } catch {
      setSnackbar({ open: true, message: 'セッション作成に失敗しました', severity: 'error' });
    }
  }, [openSession]);

  // Delete session
  const handleDeleteSession = useCallback(async () => {
    if (!activeSessionId) return;
    setMenuAnchor(null);
    try {
      await deleteChatSession(activeSessionId);
      setSessions((prev) => prev.filter((s) => s.id !== activeSessionId));
      setActiveSessionId(null);
      setMessages([]);
      setView('sessions');
      setSnackbar({ open: true, message: 'セッションを削除しました', severity: 'success' });
    } catch {
      setSnackbar({ open: true, message: 'セッション削除に失敗しました', severity: 'error' });
    }
  }, [activeSessionId]);

  // Back to session list
  const handleBack = useCallback(() => {
    setView('sessions');
    setActiveSessionId(null);
    setMessages([]);
    loadSessions();
  }, [loadSessions]);

  // Send message
  const handleSend = useCallback(
    async (question: string) => {
      if (!activeSessionId) return;

      // Add user message optimistically
      const userMsg: ChatMessage = {
        id: `temp-${Date.now()}`,
        session_id: activeSessionId,
        role: 'user',
        content: question,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setSending(true);

      try {
        const response: ChatResponse = await askChat(activeSessionId, question);
        const aiMsg: ChatMessage = {
          id: `temp-ai-${Date.now()}`,
          session_id: activeSessionId,
          role: 'assistant',
          content: response.answer,
          context_chunks: response.context,
          token_count: response.token_count,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, aiMsg]);
      } catch {
        const errorMsg: ChatMessage = {
          id: `temp-err-${Date.now()}`,
          session_id: activeSessionId,
          role: 'assistant',
          content: 'LLMサーバーに接続できません。LM Studioが起動しているか確認してください。',
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setSending(false);
      }
    },
    [activeSessionId],
  );

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  return (
    <>
      <Drawer
        anchor="right"
        open={open}
        onClose={onClose}
        PaperProps={{
          sx: {
            width: { xs: '100vw', sm: DRAWER_WIDTH },
            display: 'flex',
            flexDirection: 'column',
          },
        }}
      >
        {/* Header */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: 2,
            py: 1.5,
            borderBottom: '1px solid',
            borderColor: 'divider',
            backgroundColor: 'primary.main',
            color: 'white',
            minHeight: 56,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {view === 'chat' && (
              <IconButton size="small" onClick={handleBack} sx={{ color: 'white' }}>
                <ArrowBackIcon fontSize="small" />
              </IconButton>
            )}
            <Typography variant="h3" sx={{ color: 'white', fontWeight: 600 }}>
              {view === 'sessions'
                ? 'AIアシスタント'
                : activeSession?.title || 'チャット'}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            {view === 'chat' && (
              <IconButton
                size="small"
                onClick={(e) => setMenuAnchor(e.currentTarget)}
                sx={{ color: 'white' }}
                aria-label="メニュー"
              >
                <MoreVertIcon fontSize="small" />
              </IconButton>
            )}
            <IconButton size="small" onClick={onClose} sx={{ color: 'white' }} aria-label="閉じる">
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
        </Box>

        {/* Session List View */}
        {view === 'sessions' && (
          <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ p: 2 }}>
              <Button
                variant="contained"
                fullWidth
                startIcon={<AddIcon />}
                onClick={handleNewSession}
                sx={{ borderRadius: '20px' }}
              >
                新しいチャット
              </Button>
            </Box>
            <Divider />
            <List sx={{ flex: 1, overflowY: 'auto', py: 0 }}>
              {sessions.length === 0 ? (
                <Box sx={{ p: 3, textAlign: 'center', color: 'text.disabled' }}>
                  <Typography variant="body2">チャット履歴がありません</Typography>
                </Box>
              ) : (
                sessions.map((session) => (
                  <ListItemButton
                    key={session.id}
                    onClick={() => openSession(session.id)}
                    sx={{
                      px: 2,
                      py: 1.5,
                      '&:hover': { backgroundColor: 'grey.50' },
                    }}
                  >
                    <ListItemText
                      primary={session.title}
                      secondary={new Date(session.created_at).toLocaleDateString('ja-JP')}
                      primaryTypographyProps={{ variant: 'body2', fontWeight: 500 }}
                      secondaryTypographyProps={{ variant: 'caption' }}
                    />
                  </ListItemButton>
                ))
              )}
            </List>
          </Box>
        )}

        {/* Chat View */}
        {view === 'chat' && (
          <>
            <ChatMessageList messages={messages} loading={messagesLoading || sending} />
            <ChatInput onSend={handleSend} loading={sending} />
          </>
        )}

        {/* Session menu */}
        <Menu
          anchorEl={menuAnchor}
          open={Boolean(menuAnchor)}
          onClose={() => setMenuAnchor(null)}
        >
          <MenuItem onClick={handleDeleteSession} sx={{ color: 'error.main' }}>
            <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
            セッション削除
          </MenuItem>
        </Menu>
      </Drawer>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
      >
        <Alert severity={snackbar.severity} variant="filled">
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  );
};

export default ChatDrawer;
