import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthProvider';
import App from './App.jsx';
import ScrollTop from './components/ScrollTop.jsx';
import './styles/common.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ScrollTop/>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);