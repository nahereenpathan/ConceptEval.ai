import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Code, Terminal, CheckCircle2, AlertTriangle, Layers, Search, Sparkles } from 'lucide-react';
import { api } from '../../api/client';

export default function ProblemList() {
  const [problems, setProblems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDifficulty, setSelectedDifficulty] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadProblems();
  }, [selectedDifficulty]);

  const loadProblems = async () => {
    setLoading(true);
    try {
      const diff = selectedDifficulty === 'all' ? null : selectedDifficulty;
      const data = await api.listProblems(diff);
      setProblems(data);
    } catch (err) {
      setError(err.message || 'Failed to load problems from API.');
    } finally {
      setLoading(false);
    }
  };

  const filteredProblems = problems.filter(p =>
    p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.slug.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="container" style={{ paddingBottom: '4rem' }}>
      {/* Hero Section */}
      <div style={{
        textAlign: 'center',
        padding: '3rem 1rem 2.5rem',
        maxWidth: '840px',
        margin: '0 auto',
      }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          background: 'rgba(99, 102, 241, 0.1)',
          border: '1px solid rgba(99, 102, 241, 0.3)',
          padding: '0.35rem 0.9rem',
          borderRadius: 'var(--radius-full)',
          fontSize: '0.8rem',
          color: '#a5b4fc',
          marginBottom: '1rem',
          fontWeight: 600,
        }}>
          <Sparkles size={14} color="var(--accent-cyan)" />
          <span>BEYOND OUTPUT-ONLY ASSESSMENT</span>
        </div>

        <h1 style={{
          fontFamily: 'var(--font-heading)',
          fontSize: '2.75rem',
          fontWeight: 800,
          letterSpacing: '-0.02em',
          lineHeight: 1.15,
          marginBottom: '1rem',
          background: 'linear-gradient(135deg, #ffffff 40%, #a5b4fc 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          Concept-Aware Code Evaluation
        </h1>

        <p style={{ fontSize: '1.05rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
          Traditional judges only check if program outputs match test cases. This platform combines{' '}
          <strong style={{ color: 'var(--accent-cyan)' }}>isolated test-case execution</strong> with{' '}
          <strong style={{ color: '#a5b4fc' }}>Abstract Syntax Tree (AST) & NLP analysis</strong> to verify whether students used the required programming constructs.
        </p>

        {/* Dual-Track Visual Demonstration Banner */}
        <div className="glass-panel" style={{
          marginTop: '2rem',
          padding: '1.25rem',
          textAlign: 'left',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '1rem',
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid var(--border-medium)',
        }}>
          <div style={{
            background: 'rgba(16, 185, 129, 0.08)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            borderRadius: 'var(--radius-sm)',
            padding: '1rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <CheckCircle2 size={16} color="var(--accent-emerald)" />
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#34d399' }}>Compliant Solution (100 pts)</span>
            </div>
            <pre style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.75rem',
              color: '#d1fae5',
              background: 'rgba(0,0,0,0.3)',
              padding: '0.6rem',
              borderRadius: '4px'
            }}>
{`for i in range(4):
    print("Hello World")`}
            </pre>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
              ✅ Correct output + loop construct verified by AST visitor. Full points awarded.
            </div>
          </div>

          <div style={{
            background: 'rgba(244, 63, 94, 0.08)',
            border: '1px solid rgba(244, 63, 94, 0.25)',
            borderRadius: 'var(--radius-sm)',
            padding: '1rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <AlertTriangle size={16} color="var(--accent-rose)" />
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#fb7185' }}>Concept Violation (50 pts)</span>
            </div>
            <pre style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.75rem',
              color: '#ffe4e6',
              background: 'rgba(0,0,0,0.3)',
              padding: '0.6rem',
              borderRadius: '4px'
            }}>
{`print("Hello World")
print("Hello World")
print("Hello World")
print("Hello World")`}
            </pre>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
              ⚠️ Same output, but required loop was omitted. Functional awarded; concept withheld!
            </div>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem',
        marginBottom: '1.5rem',
      }}>
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          {['all', 'easy', 'medium', 'hard'].map(diff => (
            <button
              key={diff}
              className="btn"
              onClick={() => setSelectedDifficulty(diff)}
              style={{
                textTransform: 'capitalize',
                padding: '0.45rem 1rem',
                fontSize: '0.8rem',
                background: selectedDifficulty === diff ? 'var(--accent-primary)' : 'var(--bg-card)',
                color: selectedDifficulty === diff ? '#ffffff' : 'var(--text-muted)',
                borderColor: selectedDifficulty === diff ? 'var(--accent-primary)' : 'var(--border-subtle)',
              }}
            >
              {diff}
            </button>
          ))}
        </div>

        <div style={{ position: 'relative', width: '280px' }}>
          <Search size={16} color="var(--text-subtle)" style={{ position: 'absolute', left: '10px', top: '10px' }} />
          <input
            type="text"
            placeholder="Search problems..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '0.5rem 0.75rem 0.5rem 2.2rem',
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              color: 'white',
              fontSize: '0.85rem',
            }}
          />
        </div>
      </div>

      {/* Problem Cards List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '4rem 1rem', color: 'var(--text-muted)' }}>
          Loading assessment challenges...
        </div>
      ) : error ? (
        <div style={{
          textAlign: 'center',
          padding: '3rem',
          background: 'rgba(244, 63, 94, 0.1)',
          border: '1px solid rgba(244, 63, 94, 0.2)',
          borderRadius: 'var(--radius-md)',
          color: 'var(--accent-rose)'
        }}>
          {error}
        </div>
      ) : filteredProblems.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-muted)' }}>
          No problems found matching criteria.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          {filteredProblems.map((prob) => (
            <Link
              key={prob.id}
              to={`/problems/${prob.id}`}
              style={{ textDecoration: 'none', color: 'inherit' }}
            >
              <div
                className="glass-panel"
                style={{
                  padding: '1.25rem 1.5rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  transition: 'all 0.2s ease',
                  cursor: 'pointer',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--accent-primary)';
                  e.currentTarget.style.transform = 'translateY(-2px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-subtle)';
                  e.currentTarget.style.transform = 'none';
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '8px',
                    background: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-medium)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    <Code size={20} color="var(--accent-cyan)" />
                  </div>

                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.25rem' }}>
                      <span style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text-main)' }}>
                        {prob.title}
                      </span>
                      <span className={`badge badge-${prob.difficulty}`}>
                        {prob.difficulty}
                      </span>
                      <span className="badge badge-concept">
                        Python 3.12
                      </span>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      Evaluates both functional test cases and AST compliance rules.
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-primary)', fontSize: '0.875rem', fontWeight: 600 }}>
                  <span>Solve Challenge</span>
                  <ArrowRight size={16} />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
