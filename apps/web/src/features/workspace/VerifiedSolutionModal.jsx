import React, { useState } from 'react';
import {
  X,
  CheckCircle2,
  AlertTriangle,
  Copy,
  Check,
  Code,
  BookOpen,
  ArrowRight,
  Clock,
  HardDrive,
  Cpu,
  Layers,
  Sparkles,
  RefreshCw,
  Share2,
} from 'lucide-react';

export default function VerifiedSolutionModal({
  isOpen,
  onClose,
  solutionData,
  loading = false,
  error = null,
  selectedLanguage = 'python',
  onLoadIntoEditor,
  problemTitle = 'Problem',
}) {
  const [activeTab, setActiveTab] = useState('explanation'); // 'explanation' | 'code' | 'trace'
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopy = () => {
    if (solutionData?.source_code) {
      navigator.clipboard.writeText(solutionData.source_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const explanation = solutionData?.explanation || {};
  const isVerified = Boolean(solutionData?.is_verified);
  const vResults = solutionData?.verification_results || {};

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9000,
        background: 'rgba(5, 8, 15, 0.85)',
        backdropFilter: 'blur(10px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.25rem',
      }}
      onClick={onClose}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '880px',
          maxHeight: '90vh',
          background: 'rgba(11, 17, 32, 0.98)',
          border: '1px solid var(--border-medium)',
          borderRadius: '14px',
          boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.8)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '1rem 1.5rem',
            borderBottom: '1px solid var(--border-subtle)',
            background: 'rgba(15, 23, 42, 0.85)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.2rem' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-subtle)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Solution Learning System
              </span>
              <span
                style={{
                  fontSize: '0.7rem',
                  padding: '0.1rem 0.5rem',
                  borderRadius: '9999px',
                  background: 'rgba(99, 102, 241, 0.15)',
                  color: 'var(--accent-primary)',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                }}
              >
                {selectedLanguage}
              </span>
            </div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#ffffff', margin: 0 }}>
              {problemTitle} — Verified Solution & Guide
            </h2>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '0.35rem',
              borderRadius: '4px',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Verification Status Banner */}
        <div
          style={{
            padding: '0.65rem 1.5rem',
            background: isVerified ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
            borderBottom: `1px solid ${isVerified ? 'rgba(16, 185, 129, 0.25)' : 'rgba(245, 158, 11, 0.25)'}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '0.5rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {isVerified ? (
              <CheckCircle2 size={16} color="var(--accent-emerald)" />
            ) : (
              <AlertTriangle size={16} color="var(--accent-amber)" />
            )}
            <span
              style={{
                fontSize: '0.78rem',
                fontWeight: 700,
                color: isVerified ? '#34d399' : '#fbbf24',
              }}
            >
              {isVerified
                ? 'Teacher-Verified Reference Solution (Validated in Sandbox)'
                : 'AI-Generated Candidate (Not Yet Fully Verified)'}
            </span>
          </div>

          {isVerified && vResults.total_cases > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.72rem', color: '#cbd5e1' }}>
              <span>
                <strong>{vResults.passed_cases}/{vResults.total_cases}</strong> Sandbox Tests Passed
              </span>
              {vResults.concept_verified && (
                <span style={{ color: '#34d399', display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                  ✓ AST Concept Compliance
                </span>
              )}
            </div>
          )}
        </div>

        {/* Content Tabs */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid var(--border-subtle)',
            background: 'rgba(15, 23, 42, 0.5)',
            padding: '0 1.5rem',
          }}
        >
          <button
            onClick={() => setActiveTab('explanation')}
            style={{
              padding: '0.65rem 1rem',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === 'explanation' ? '2px solid var(--accent-cyan)' : '2px solid transparent',
              color: activeTab === 'explanation' ? '#ffffff' : 'var(--text-muted)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
            }}
          >
            <BookOpen size={14} />
            <span>Pedagogical Approach</span>
          </button>
          <button
            onClick={() => setActiveTab('code')}
            style={{
              padding: '0.65rem 1rem',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === 'code' ? '2px solid var(--accent-cyan)' : '2px solid transparent',
              color: activeTab === 'code' ? '#ffffff' : 'var(--text-muted)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
            }}
          >
            <Code size={14} />
            <span>Verified Code & Walkthrough</span>
          </button>
          <button
            onClick={() => setActiveTab('trace')}
            style={{
              padding: '0.65rem 1rem',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === 'trace' ? '2px solid var(--accent-cyan)' : '2px solid transparent',
              color: activeTab === 'trace' ? '#ffffff' : 'var(--text-muted)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
            }}
          >
            <Layers size={14} />
            <span>Example Trace</span>
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem 1.5rem' }}>
          {loading && (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
              <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.75rem', color: 'var(--accent-cyan)' }} />
              <div>Validating reference solution in isolated sandbox...</div>
            </div>
          )}

          {error && !loading && (
            <div
              style={{
                background: 'rgba(244, 63, 94, 0.12)',
                border: '1px solid rgba(244, 63, 94, 0.35)',
                borderRadius: '8px',
                padding: '1rem',
                color: '#fb7185',
                fontSize: '0.85rem',
              }}
            >
              <div style={{ fontWeight: 700, marginBottom: '0.3rem' }}>Could Not Load Verified Solution</div>
              <div>{error}</div>
            </div>
          )}

          {solutionData && !loading && !error && (
            <>
              {/* TAB 1: EXPLANATION */}
              {activeTab === 'explanation' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {/* Approach & Logic */}
                  <div>
                    <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.35rem' }}>
                      Optimal Approach & Algorithm
                    </h4>
                    <p style={{ fontSize: '0.825rem', color: '#cbd5e1', lineHeight: 1.55 }}>
                      {explanation.approach || 'Optimal algorithmic strategy satisfying required complexity constraints.'}
                    </p>
                  </div>

                  {/* Why it works */}
                  {explanation.why_it_works && (
                    <div
                      style={{
                        background: 'rgba(15, 23, 42, 0.7)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        padding: '0.85rem 1rem',
                      }}
                    >
                      <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: '0.35rem' }}>
                        Why this approach works
                      </h4>
                      <p style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.55, margin: 0 }}>
                        {explanation.why_it_works}
                      </p>
                    </div>
                  )}

                  {/* Complexity Badges */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                    <div
                      style={{
                        background: 'rgba(30, 41, 59, 0.6)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        padding: '0.75rem',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--text-muted)', fontSize: '0.72rem', marginBottom: '0.2rem' }}>
                        <Clock size={13} color="var(--accent-primary)" />
                        <span>Time Complexity</span>
                      </div>
                      <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#ffffff', fontFamily: 'var(--font-mono)' }}>
                        {explanation.time_complexity || 'O(N)'}
                      </div>
                    </div>

                    <div
                      style={{
                        background: 'rgba(30, 41, 59, 0.6)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        padding: '0.75rem',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--text-muted)', fontSize: '0.72rem', marginBottom: '0.2rem' }}>
                        <HardDrive size={13} color="var(--accent-cyan)" />
                        <span>Space Complexity</span>
                      </div>
                      <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#ffffff', fontFamily: 'var(--font-mono)' }}>
                        {explanation.space_complexity || 'O(1)'}
                      </div>
                    </div>
                  </div>

                  {/* Required Concepts Satisfied */}
                  {Array.isArray(explanation.required_concepts_satisfied) && explanation.required_concepts_satisfied.length > 0 && (
                    <div>
                      <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.4rem' }}>
                        Required Concepts Verified via AST
                      </h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                        {explanation.required_concepts_satisfied.map((rc, idx) => (
                          <div
                            key={idx}
                            style={{
                              background: 'rgba(16, 185, 129, 0.08)',
                              border: '1px solid rgba(16, 185, 129, 0.25)',
                              borderRadius: '6px',
                              padding: '0.45rem 0.75rem',
                              fontSize: '0.78rem',
                              color: '#d1fae5',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.4rem',
                            }}
                          >
                            <CheckCircle2 size={14} color="var(--accent-emerald)" />
                            <span>{rc}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Alternative Approaches */}
                  {explanation.alternative_approaches && (
                    <div>
                      <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                        Alternative Approaches & Trade-offs
                      </h4>
                      <p style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.5, margin: 0 }}>
                        {explanation.alternative_approaches}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: CODE & WALKTHROUGH */}
              {activeTab === 'code' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {/* Code box */}
                  <div
                    style={{
                      background: 'rgba(15, 23, 42, 0.95)',
                      border: '1px solid var(--border-medium)',
                      borderRadius: '8px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        padding: '0.45rem 0.85rem',
                        background: 'rgba(30, 41, 59, 0.7)',
                        borderBottom: '1px solid var(--border-subtle)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        Solution.{selectedLanguage === 'cpp' ? 'cpp' : selectedLanguage === 'java' ? 'java' : 'py'}
                      </span>
                      <button
                        onClick={handleCopy}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: copied ? 'var(--accent-emerald)' : 'var(--text-muted)',
                          fontSize: '0.72rem',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.3rem',
                        }}
                      >
                        {copied ? <Check size={12} /> : <Copy size={12} />}
                        <span>{copied ? 'Copied' : 'Copy Code'}</span>
                      </button>
                    </div>

                    <pre
                      style={{
                        margin: 0,
                        padding: '1rem',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '0.8rem',
                        color: '#f8fafc',
                        lineHeight: 1.5,
                        overflowX: 'auto',
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {solutionData.source_code}
                    </pre>
                  </div>

                  {/* Step by Step Breakdown */}
                  {Array.isArray(explanation.step_by_step) && explanation.step_by_step.length > 0 && (
                    <div>
                      <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
                        Step-by-Step Code Walkthrough
                      </h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                        {explanation.step_by_step.map((step, idx) => (
                          <div
                            key={idx}
                            style={{
                              background: 'rgba(30, 41, 59, 0.5)',
                              border: '1px solid var(--border-subtle)',
                              borderRadius: '6px',
                              padding: '0.55rem 0.85rem',
                              display: 'flex',
                              alignItems: 'flex-start',
                              gap: '0.5rem',
                            }}
                          >
                            <span
                              style={{
                                width: '18px',
                                height: '18px',
                                borderRadius: '50%',
                                background: 'rgba(99, 102, 241, 0.25)',
                                color: 'var(--accent-primary)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '0.68rem',
                                fontWeight: 700,
                                flexShrink: 0,
                                marginTop: '0.1rem',
                              }}
                            >
                              {idx + 1}
                            </span>
                            <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.45 }}>
                              {step}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: TRACE */}
              {activeTab === 'trace' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <div
                    style={{
                      background: 'rgba(15, 23, 42, 0.8)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '8px',
                      padding: '1rem',
                    }}
                  >
                    <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
                      Execution Trace with Sample Input
                    </h4>
                    <p style={{ fontSize: '0.825rem', color: '#cbd5e1', lineHeight: 1.6 }}>
                      {explanation.example_walkthrough ||
                        'Trace the solution step-by-step with sample input to observe how variables update during execution.'}
                    </p>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: '0.85rem 1.5rem',
            borderTop: '1px solid var(--border-subtle)',
            background: 'rgba(15, 23, 42, 0.85)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ fontSize: '0.72rem', color: 'var(--text-subtle)' }}>
            Examining verified solutions reinforces algorithmic patterns and concept mastery.
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              style={{ padding: '0.45rem 1rem', fontSize: '0.8rem' }}
            >
              Close
            </button>

            {solutionData?.source_code && onLoadIntoEditor && (
              <button
                type="button"
                className="btn btn-primary"
                onClick={onLoadIntoEditor}
                style={{
                  padding: '0.45rem 1.15rem',
                  fontSize: '0.8rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                }}
              >
                <Code size={14} />
                <span>Load Solution into Editor</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
