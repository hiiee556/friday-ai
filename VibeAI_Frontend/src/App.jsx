import React, { useState } from 'react';
import axios from 'axios';
import ChatContainer from './components/ChatContainer';
import InputBox from './components/InputBox';

function App() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (text) => {
    // 1. Add user message locally
    const userMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // 2. Call Python backend using axios
      const response = await axios.post('http://localhost:8000/api/chat', {
        message: text,
      });

      // 3. Add AI response locally
      const aiMessage = { 
        role: 'assistant', 
        content: response.data.response || response.data.message || 'No response from AI' 
      };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      console.error('Error fetching AI response:', error);
      const errorMessage = { 
        role: 'assistant', 
        content: "I'm sorry, I'm having trouble connecting to the backend. Please ensure the server is running at http://localhost:8000." 
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      <ChatContainer messages={messages} isLoading={isLoading} />
      <InputBox onSend={handleSendMessage} disabled={isLoading} />
    </div>
  );
}

export default App;
