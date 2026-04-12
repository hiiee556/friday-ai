import React from 'react';

const Message = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`message-row ${isUser ? 'user' : 'ai'}`}>
      <div className="message-bubble">
        {message.content}
      </div>
    </div>
  );
};

export default Message;
