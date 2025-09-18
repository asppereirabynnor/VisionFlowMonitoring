import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Contextos
import { AuthProvider } from './contexts/AuthContext';

// Páginas
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import CameraList from './pages/CameraList';
import CameraDetail from './pages/CameraDetail';
import EventList from './pages/EventList';
import Settings from './pages/Settings';
import VideoProcessor from './pages/VideoProcessor';

// Componentes
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

// Cliente para React Query
const queryClient = new QueryClient();

// Tema da aplicação
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#2196f3',
    },
    secondary: {
      main: '#f50057',
    },
    background: {
      default: '#121212',
      paper: '#1e1e1e',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/" element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }>
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="cameras" element={<CameraList />} />
                <Route path="cameras/:id" element={<CameraDetail />} />
                <Route path="events" element={<EventList />} />
                <Route path="video-processor" element={<VideoProcessor />} />
                <Route path="settings" element={<Settings />} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </AuthProvider>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
