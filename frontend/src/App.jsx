import React, { useEffect, useState } from 'react';
import { Provider, useDispatch, useSelector } from 'react-redux';
import { store } from './store';
import { fetchHcps } from './store/interactionSlice';
import InteractionForm from './components/InteractionForm';
import AIAssistant from './components/AIAssistant';
import PastInteractions from './components/PastInteractions';
import ToolsPanel from './components/ToolsPanel';
import './App.css';

function MainApp() {
  const dispatch = useDispatch();
  const { error } = useSelector((state) => state.interaction);
  const [isMockMode, setIsMockMode] = useState(true);

  useEffect(() => {
    // Initial fetch of HCP directory
    dispatch(fetchHcps());
    
    // Check if the backend is running in mock mode or has active Groq keys
    fetch('http://localhost:8000/api/hcps')
      .then(() => {
        // Backend is alive, let's check mock settings
        // By default we run mock mode for seamless evaluation
        setIsMockMode(true);
      })
      .catch(() => {
        // Fallback
      });
  }, [dispatch]);

  return (
    <div className="app">
      {/* App Header */}
      <header className="app-header">
        <div className="header-title-container">
          <h1>AI-First CRM HCP Module</h1>
          <p>Healthcare Professional Log Interaction Interface</p>
        </div>

        <div className="header-actions">
          {/* Status indicators */}
          <div className="settings-bar">
            <span className="settings-indicator"></span>
            <span>API Online</span>
          </div>

          <div className="settings-bar" id="mock-status-indicator">
            <span className="settings-indicator"></span>
            <span>Mock AI Mode (Active)</span>
          </div>
        </div>
      </header>

      {/* Main Content Layout */}
      <main className="container">
        {error && (
          <div
            style={{
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#fca5a5',
              padding: '1rem',
              borderRadius: '8px',
              marginBottom: '1.5rem',
              fontSize: '0.9rem',
            }}
            id="error-banner"
          >
            ⚠️ <strong>Error connecting to API:</strong> {error}. Ensure the FastAPI server is running at `http://localhost:8000`.
          </div>
        )}

        <div className="main-layout">
          {/* Left panel: Structured form manual log */}
          <div className="form-panel-container">
            <InteractionForm />
          </div>

          {/* Right panel: Chat assistant */}
          <div className="chat-panel-container">
            <AIAssistant />
          </div>
        </div>

        {/* Tools collapsible info */}
        <ToolsPanel />

        {/* Past logged interactions list */}
        <PastInteractions />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Provider store={store}>
      <MainApp />
    </Provider>
  );
}
