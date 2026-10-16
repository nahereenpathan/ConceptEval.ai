import React from 'react';
import { AlertCircle, X, Check, ArrowRight } from 'lucide-react';

export default function LoadSolutionConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  language = 'python',
}) {
  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        background: 'rgba(5, 8, 15, 0.8)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
      }}
      onClick={onClose}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '480px',
          background: 'rgba(15, 23, 42, 0.98)',
          border: '1px solid rgba(245, 158, 11, 0.4)',
          borderRadius: '12px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '1rem 1.25rem',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(245, 158, 11, 0.08)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertCircle size={20} color="var(--accent-amber)" />
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff', margin: 0 }}>
              Load Solution into Editor?
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '0.2rem',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '1.25rem' }}>
          <p style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: 1.5, marginBottom: '0.85rem' }}>
            This will load the verified reference implementation in{' '}
            <strong style={{ color: '#ffffff', textTransform: 'uppercase' }}>{language}</strong> directly into your code editor.
          </p>

          <div
            style={{
              background: 'rgba(0, 0, 0, 0.35)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              padding: '0.75rem',
              marginBottom: '1rem',
              fontSize: '0.78rem',
              color: 'var(--text-muted)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.4rem', marginBottom: '0.35rem' }}>
              <span style={{ color: 'var(--accent-amber)' }}>⚠️</span>
              <span>Your current code in the editor will be replaced.</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.4rem' }}>
              <span style={{ color: 'var(--accent-emerald)' }}>✓</span>
              <span>Your previous submissions are safely stored in your Submission History.</span>
            </div>
          </div>

          <p style={{ fontSize: '0.8rem', color: 'var(--text-subtle)', margin: 0 }}>
            We recommend examining the explanation first and attempting to correct your solution independently.
          </p>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '0.85rem 1.25rem',
            background: 'rgba(15, 23, 42, 0.6)',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '0.65rem',
          }}
        >
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
            style={{ padding: '0.45rem 1rem', fontSize: '0.825rem' }}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={onConfirm}
            style={{
              padding: '0.45rem 1.15rem',
              fontSize: '0.825rem',
              background: 'linear-gradient(135deg, #f59e0b, #d97706)',
              borderColor: '#f59e0b',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
            }}
          >
            <Check size={14} />
            <span>Confirm & Load into Editor</span>
          </button>
        </div>
      </div>
    </div>
  );
}
