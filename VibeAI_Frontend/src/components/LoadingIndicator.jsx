import React from 'react';

const LoadingIndicator = () => {
  return (
    <div className="message-row ai">
      <div className="message-bubble">
        <div className="typing-indicator">
          <div className="dot"></div>
          <div className="dot"></div>
          <div className="dot"></div>
        </div>
      </div>
    </div>
  );
};

export default LoadingIndicator;
