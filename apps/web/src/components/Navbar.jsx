import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Code2, BookOpen, Sparkles, UserCheck, LogIn, CheckCircle2 } from 'lucide-react';

export default function Navbar({ currentUser, onOpenAuth }) {
  const location = useLocation();

  return (
    <nav className="navbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
        <Link to="/" className="brand-logo">
          <div style={{
            background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
            padding: '8px',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 15px rgba(99, 102, 241, 0.4)'
          }}>
            <Code2 size={22} color="#ffffff" />
          </div>
          <span>ConceptEval<span style={{ color: 'var(--accent-cyan)' }}>.ai</span></span>
          <span className="brand-badge">AST + NLP</span>
        </Link>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Link
            to="/"
            className="btn btn-secondary"
            style={{
              padding: '0.4rem 0.85rem',
              fontSize: '0.825rem',
              background: location.pathname === '/' ? 'var(--bg-glass-hover)' : 'transparent',
              borderColor: location.pathname === '/' ? 'var(--border-medium)' : 'transparent',
            }}
          >
            <BookOpen size={15} />
            <span>Problem Library</span>
          </Link>

          <Link
            to="/authoring"
            className="btn btn-secondary"
            style={{
              padding: '0.4rem 0.85rem',
              fontSize: '0.825rem',
              background: location.pathname === '/authoring' ? 'var(--bg-glass-hover)' : 'transparent',
              borderColor: location.pathname === '/authoring' ? 'var(--border-medium)' : 'transparent',
            }}
          >
            <Sparkles size={15} color="var(--accent-cyan)" />
            <span>NLP Rubric Extractor</span>
          </Link>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {/* Backend health status badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.25)',
          padding: '0.25rem 0.65rem',
          borderRadius: 'var(--radius-full)'
        }}>
          <CheckCircle2 size={13} color="var(--accent-emerald)" />
          <span>FastAPI Engine Ready</span>
        </div>

        {currentUser ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.6rem',
            background: 'var(--bg-tertiary)',
            padding: '0.35rem 0.75rem',
            borderRadius: 'var(--radius-full)',
            border: '1px solid var(--border-medium)'
          }}>
            <UserCheck size={16} color="var(--accent-primary)" />
            <span style={{ fontSize: '0.825rem', fontWeight: 600 }}>{currentUser.display_name}</span>
          </div>
        ) : (
          <button className="btn btn-primary" onClick={onOpenAuth} style={{ padding: '0.45rem 1rem' }}>
            <LogIn size={15} />
            <span>Sign In / Demo Login</span>
          </button>
        )}
      </div>
    </nav>
  );
}
