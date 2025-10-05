'use client';

import { useEffect, useState, useRef } from 'react';
import WebSocketClient from '@/lib/websocket';
import { useAuthStore } from '@/lib/store';
import type { ChatMessage, ChatEvent } from '@/types/api';
import MessageList from './MessageList';

interface ChatWindowProps {
  sessionId: number;
  crewId?: number;
}

export default function ChatWindow({ sessionId, crewId }: ChatWindowProps) {
  const { token } = useAuthStore();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [typing, setTyping] = useState(false);
  const wsClient = useRef<WebSocketClient | null>(null);

  useEffect(() => {
    if (!token) return;

    // Initialize WebSocket connection
    const client = new WebSocketClient();
    wsClient.current = client;

    client.connect(token, {
      onConnect: () => {
        console.log('Connected to chat');
        client.joinSession(sessionId);
      },
      onDisconnect: () => {
        console.log('Disconnected from chat');
      },
      onError: (error) => {
        console.error('Chat error:', error);
      },
    });

    // Listen for messages
    client.onMessage((event: ChatEvent) => {
      if (event.type === 'message' && 'content' in event.data) {
        setMessages((prev) => [...prev, event.data as ChatMessage]);
      }
    });

    // Listen for typing indicators
    client.onTyping((data) => {
      if (data.session_id === sessionId) {
        setTyping(data.typing);
      }
    });

    return () => {
      client.leaveSession(sessionId);
      client.disconnect();
    };
  }, [sessionId, token]);

  const handleSend = async () => {
    if (!input.trim() || !wsClient.current) return;

    setSending(true);
    try {
      wsClient.current.sendMessage(sessionId, input);
      setInput('');
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInputChange = (value: string) => {
    setInput(value);

    // Send typing indicator
    if (wsClient.current) {
      wsClient.current.sendTyping(sessionId, value.length > 0);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-4">
        <h2 className="text-lg font-semibold text-gray-900">
          Chat Session #{sessionId}
        </h2>
        {crewId && (
          <p className="text-sm text-gray-500">
            Crew ID: {crewId}
          </p>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <MessageList messages={messages} />
        {typing && (
          <div className="px-6 py-2">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <div className="flex gap-1">
                <span className="animate-bounce">●</span>
                <span className="animate-bounce" style={{ animationDelay: '0.1s' }}>●</span>
                <span className="animate-bounce" style={{ animationDelay: '0.2s' }}>●</span>
              </div>
              <span>Agent is typing...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 px-6 py-4">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            rows={2}
            disabled={sending}
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 resize-none focus:border-blue-500 focus:outline-none focus:ring-blue-500"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sending}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed self-end"
          >
            {sending ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
