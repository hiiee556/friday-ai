import React, { useEffect, useRef } from 'react';
import Message from './Message';
import LoadingIndicator from './LoadingIndicator';

const ChatContainer = ({ messages, isLoading }) => {
  const scrollRef = useRef(null);

  useEffect(() => {
    // Auto-scroll to bottom whenever messages or loading state changes
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  return (
    <div className="chat-window" ref={scrollRef}>
      {messages.length === 0 && (
        <div style={{ textAlign: 'center', marginTop: '4rem', color: 'var(--text-secondary)', animation: 'fadeIn 0.8s ease-out' }}>
          <img src="/vibe-logo.png" alt="Vibe AI" style={{ width: '80px', height: '80px', marginBottom: '1.5rem', borderRadius: '20px', boxShadow: '0 8px 30px rgba(88, 166, 255, 0.2)' }} />
          <h2 style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)', marginBottom: '1rem', fontSize: '2rem' }}>
            Hello! I'm Vibe AI
          </h2>
          <p>Your intelligent assistant is ready for your first prompt.</p>
        </div>
      )}
      {messages.map((msg, index) => (
        <Message key={index} message={msg} />
      ))}
      {isLoading && <LoadingIndicator />}
    </div>
  );
};

export default ChatContainer;
