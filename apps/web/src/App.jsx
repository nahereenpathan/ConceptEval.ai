import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import AuthModal from './components/AuthModal';
import ProblemList from './features/problems/ProblemList';
import ProblemWorkspace from './features/workspace/ProblemWorkspace';
import AuthoringPlayground from './features/authoring/AuthoringPlayground';
import { api } from './api/client';

import ErrorBoundary from './components/ErrorBoundary';

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);

  useEffect(() => {
    // Attempt auto-login if token is preserved or load demo student
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      if (api.token) {
        const user = await api.getMe();
        setCurrentUser(user);
      } else {
        // Auto-login as student for zero-friction demo experience
        await api.login('student@codeedu.org', 'StudentPassword123!');
        const user = await api.getMe();
        setCurrentUser(user);
      }
    } catch (err) {
      console.warn('Auto auth skipped:', err);
    }
  };

  return (
    <BrowserRouter>
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Navbar
          currentUser={currentUser}
          onOpenAuth={() => setAuthModalOpen(true)}
        />

        <main style={{ flex: 1 }}>
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<ProblemList />} />
              <Route
                path="/problems/:id"
                element={
                  <ProblemWorkspace
                    currentUser={currentUser}
                    onOpenAuth={() => setAuthModalOpen(true)}
                  />
                }
              />
              <Route
                path="/authoring"
                element={
                  <AuthoringPlayground
                    currentUser={currentUser}
                    onOpenAuth={() => setAuthModalOpen(true)}
                  />
                }
              />
            </Routes>
          </ErrorBoundary>
        </main>

        <AuthModal
          isOpen={authModalOpen}
          onClose={() => setAuthModalOpen(false)}
          onAuthSuccess={(user) => setCurrentUser(user)}
        />
      </div>
    </BrowserRouter>
  );
}
