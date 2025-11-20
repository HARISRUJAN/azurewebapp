import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { Landing } from './pages/Landing';
import { AskAI } from './pages/AskAI';
import { AdminLogin } from './pages/Admin/Login';
import { AdminDashboard } from './pages/Admin/Dashboard';
import { Health } from './pages/Admin/Health';
import { Monitor } from './pages/Admin/Monitor';
import { Sidebar } from './components/Navigation';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/admin/login" replace />;
  }
  
  return <>{children}</>;
};

const AdminLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAdmin } = useAuth();
  
  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }
  
  const navItems = [
    { label: 'Monitor', path: '/admin/monitor' },
    { label: 'Dashboard', path: '/admin/dashboard' },
    { label: 'Health', path: '/admin/health' },
  ];
  
  return (
    <div className="flex min-h-screen">
      <Sidebar items={navItems} />
      <main className="flex-1">{children}</main>
    </div>
  );
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/ask" element={<AskAI />} />
            <Route path="/admin/login" element={<AdminLogin />} />
            {/* Redirect /monitor/login to /admin/login for convenience */}
            <Route path="/monitor/login" element={<Navigate to="/admin/login" replace />} />
            <Route
              path="/admin/dashboard"
              element={
                <ProtectedRoute>
                  <AdminLayout>
                    <AdminDashboard />
                  </AdminLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/health"
              element={
                <ProtectedRoute>
                  <AdminLayout>
                    <Health />
                  </AdminLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/monitor"
              element={
                <ProtectedRoute>
                  <AdminLayout>
                    <Monitor />
                  </AdminLayout>
                </ProtectedRoute>
              }
            />
            {/* Catch-all route for unknown paths */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;

