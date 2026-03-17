import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Toaster } from 'react-hot-toast';
import App from './App.jsx';
import './styles/index.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: '#111827',
          color: '#f1f5f9',
          border: '1px solid rgba(99, 102, 241, 0.12)',
        },
      }}
    />
  </StrictMode>,
);
