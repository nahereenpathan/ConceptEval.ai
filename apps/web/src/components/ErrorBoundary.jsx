import React from 'react';
import { AlertCircle, RefreshCw, Home } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an unhandled error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '60vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '2rem 1rem',
        }}>
          <div style={{
            background: 'rgba(30, 41, 59, 0.85)',
            border: '1px solid rgba(244, 63, 94, 0.4)',
            borderRadius: 'var(--radius-md)',
            padding: '2.5rem',
            maxWidth: '650px',
            width: '100%',
            textAlign: 'center',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
          }}>
            <AlertCircle size={44} color="var(--accent-rose)" style={{ margin: '0 auto 1rem' }} />
            <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.75rem' }}>
              Something Went Wrong
            </h2>
            <p style={{ fontSize: '0.9rem', color: '#cbd5e1', lineHeight: 1.5, marginBottom: '1.5rem' }}>
              An unexpected error occurred while rendering this page:
            </p>

            <pre style={{
              background: 'rgba(0, 0, 0, 0.5)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '1rem',
              color: '#fb7185',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.8rem',
              textAlign: 'left',
              overflowX: 'auto',
              maxHeight: '160px',
              marginBottom: '1.75rem',
            }}>
              {this.state.error?.message || String(this.state.error)}
            </pre>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
              <button
                onClick={this.handleReset}
                className="btn btn-secondary"
                style={{ padding: '0.55rem 1.25rem', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
              >
                <RefreshCw size={14} />
                <span>Reload Page</span>
              </button>
              <a
                href="/"
                className="btn btn-primary"
                style={{ padding: '0.55rem 1.25rem', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.4rem', textDecoration: 'none' }}
              >
                <Home size={14} />
                <span>Problem Library</span>
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
