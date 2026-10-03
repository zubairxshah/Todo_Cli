'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  MainContainer,
  ChatContainer,
  MessageList,
  Message,
  MessageInput,
  TypingIndicator
} from '@chatscope/chat-ui-kit-react';
import '@chatscope/chat-ui-kit-styles/dist/default/styles.min.css';
import { chatApi } from '../../lib/chatApi';

interface MessageItem {
  id: string;
  text: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

export default function ChatUI() {
  const [inputMessage, setInputMessage] = useState<string>('');
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const messageListRef = useRef<any>(null);
  const isMountedRef = useRef(true); // Track if component is mounted

  // Load initial welcome message
  useEffect(() => {
    const welcomeMessage: MessageItem = {
      id: 'welcome-' + Date.now().toString(),
      text: 'Hello! I\'m your AI assistant. How can I help you with your tasks today?',
      sender: 'assistant',
      timestamp: new Date(),
    };
    setMessages([welcomeMessage]);

    // Cleanup function
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages]);

  // Cleanup function to cancel ongoing requests when component unmounts
  useEffect(() => {
    return () => {
      // Cancel any ongoing request when component unmounts
      chatApi.cancelCurrentRequest();
      isMountedRef.current = false;
    };
  }, []);

  const handleSend = async (text: string) => {
    if (!text.trim() || isLoading) return; // Prevent multiple simultaneous requests

    // Add user message to the chat
    const userMessage: MessageItem = {
      id: Date.now().toString(),
      text: text,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      // Call the chat API
      const response = await chatApi.sendMessage(text);

      // Only update state if component is still mounted
      if (isMountedRef.current) {
        // Create assistant message based on response status
        const assistantMessage: MessageItem = {
          id: (Date.now() + 1).toString(),
          text: response.message || 'I processed your request and here\'s the response from the AI assistant.',
          sender: 'assistant',
          timestamp: new Date(),
        };

        // Add the assistant message to the chat
        setMessages(prev => [...prev, assistantMessage]);
      }
    } catch (error) {
      // Only update state if component is still mounted
      if (isMountedRef.current) {
        console.error('Chat API error:', error);

        // Handle error with a more specific message
        let errorMessageText = 'Sorry, I encountered an issue. Please try again.';

        if (error instanceof Error) {
          if (error.message.includes('timeout')) {
            errorMessageText = 'The request took too long. The backend server might not be running or the API key is not configured.';
          } else if (error.message.includes('connect')) {
            errorMessageText = 'Cannot connect to the chat service. Please ensure the backend server is running.';
          }
        }

        const errorMessage: MessageItem = {
          id: (Date.now() + 1).toString(),
          text: errorMessageText,
          sender: 'assistant',
          timestamp: new Date(),
        };

        setMessages(prev => [...prev, errorMessage]);
      }
    } finally {
      // Only update loading state if component is still mounted
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  };

  return (
    <div style={{ position: "relative", height: "500px", width: "100%" }}>
      <MainContainer responsive>
        <ChatContainer>
          <MessageList
            ref={messageListRef}
            scrollBehavior="smooth"
            typingIndicator={isLoading ? <TypingIndicator content="AI is thinking..." /> : undefined}
          >
            {messages.map((msg) => (
              <Message
                key={msg.id}
                model={{
                  message: msg.text,
                  sentTime: msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                  sender: msg.sender,
                  direction: msg.sender === 'user' ? 'outgoing' : 'incoming',
                  position: msg.sender === 'user' ? 'normal' : 'normal'  // Added position property
                }}
                avatarPosition={msg.sender === 'user' ? 'tr' : 'tl'}
              />
            ))}
          </MessageList>

          <MessageInput
            placeholder="Type your message here..."
            onSend={handleSend}
            attachButton={false}
            disabled={isLoading}
            value={inputMessage}
            onChange={(val) => setInputMessage(val)}
          />
        </ChatContainer>
      </MainContainer>
    </div>
  );
}