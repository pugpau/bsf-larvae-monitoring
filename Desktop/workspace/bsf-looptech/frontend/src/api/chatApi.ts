/**
 * RAG Chat & Knowledge Base API
 */
import { createAuthenticatedClient } from '../utils/axiosConfig';
import type {
  ChatSession, ChatSessionDetail, ChatResponse,
  ChatStreamCallbacks, KnowledgeEntry,
} from '../types/api';

const chatClient = createAuthenticatedClient('/api/v1', 30000);

/** Create a new chat session. */
export const createChatSession = async (title = 'New Chat'): Promise<ChatSession> => {
  const response = await chatClient.post('/chat/sessions', { title });
  return response.data;
};

/** List all chat sessions. */
export const fetchChatSessions = async (): Promise<ChatSession[]> => {
  const response = await chatClient.get('/chat/sessions');
  return response.data;
};

/** Get chat session detail with messages. */
export const fetchChatSession = async (sessionId: string): Promise<ChatSessionDetail> => {
  const response = await chatClient.get(`/chat/sessions/${sessionId}`);
  return response.data;
};

/** Delete a chat session. */
export const deleteChatSession = async (sessionId: string): Promise<void> => {
  await chatClient.delete(`/chat/sessions/${sessionId}`);
};

/** Ask a question via RAG (non-streaming). */
export const askChat = async (sessionId: string, question: string): Promise<ChatResponse> => {
  const response = await chatClient.post('/chat/ask', {
    session_id: sessionId,
    question,
  });
  return response.data;
};

/**
 * Ask a question via RAG with SSE streaming.
 * Returns an EventSource-like reader. Call onChunk for token chunks,
 * onContext for context data, onDone when complete.
 */
export const askChatStream = (
  sessionId: string,
  question: string,
  { onChunk, onContext, onDone, onError }: ChatStreamCallbacks
): void => {
  // Suppress unused variable warning — onContext reserved for future context event handling
  void onContext;

  const url = '/api/v1/chat/ask/stream';
  const body = JSON.stringify({ session_id: sessionId, question });

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const token = localStorage.getItem('accessToken');
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  fetch(url, {
    method: 'POST',
    headers,
    body,
    credentials: 'include',
  }).then(async (res) => {
    if (!res.ok) {
      onError?.(new Error(`HTTP ${res.status}`));
      return;
    }
    const reader = res.body?.getReader();
    if (!reader) {
      onError?.(new Error('Response body is null'));
      return;
    }
    const decoder = new TextDecoder();
    let buffer = '';

    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            onDone?.();
          } else {
            onChunk?.(data);
          }
        } else if (line.startsWith('event: context')) {
          // Next data line will be context JSON
        } else if (line.startsWith('event: done')) {
          // Next data line will be final JSON
        }
      }
    }
  }).catch((err) => {
    onError?.(err instanceof Error ? err : new Error(String(err)));
  });
};

/** Add knowledge to the knowledge base. */
export const createKnowledge = async (data: Partial<KnowledgeEntry>): Promise<KnowledgeEntry> => {
  const response = await chatClient.post('/knowledge', data);
  return response.data;
};

/** List knowledge base entries. */
export const fetchKnowledge = async (): Promise<KnowledgeEntry[]> => {
  const response = await chatClient.get('/knowledge');
  return response.data;
};

/** Seed knowledge base with default BSF domain data. */
export const seedKnowledge = async (): Promise<{ seeded: number }> => {
  const response = await chatClient.post('/knowledge/seed');
  return response.data;
};
