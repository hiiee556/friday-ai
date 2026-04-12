# Vibe AI Frontend

A modern, production-ready React interface for your Python-based AI system.

## Features
- **Modern UI**: Dark-themed ChatGPT-style interface with glassmorphism and smooth animations.
- **Responsive**: Works perfectly on Desktop, Tablet, and Mobile.
- **Optimized**: Fast rendering using React 18 and Vite.
- **Auto-Resize Input**: Textarea grows with your content.
- **Loading States**: Animated typing indicators for better UX.

## Getting Started

### Prerequisites
- Node.js (v16.0.0 or higher)
- npm or yarn

### Installation
1. Navigate to the project directory:
   ```bash
   cd VibeAI_Frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```

### Running the App
1. Start the development server:
   ```bash
   npm run dev
   ```
2. Open your browser and navigate to `http://localhost:3000` (or the port shown in your terminal).

### Backend Integration
The app is configured to talk to `http://localhost:8000/api/chat`. 
The expected request format is:
```json
{
  "message": "User query here"
}
```
The expected response format is:
```json
{
  "response": "AI reply here"
}
```

## Project Structure
- `src/App.jsx`: Main logic and API integration.
- `src/components/`: Reusable UI components (ChatContainer, Message, InputBox).
- `src/index.css`: Global styling and design system.
- `vite.config.js`: Configuration with a proxy for development.
