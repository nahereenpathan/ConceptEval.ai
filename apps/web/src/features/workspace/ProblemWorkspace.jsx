import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import confetti from 'canvas-confetti';
import {
  ArrowLeft,
  Play,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Sparkles,
  Info,
  Terminal,
  FileCode2,
  RefreshCw,
  Lightbulb,
} from 'lucide-react';
import { api } from '../../api/client';

export default function ProblemWorkspace({ currentUser, onOpenAuth }) {
  const { id } = useParams();
  const [problem, setProblem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [code, setCode] = useState('');
  const [evaluating, setEvaluating] = useState(false);
  const [evalResult, setEvalResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    loadProblem();
  }, [id]);

  const loadProblem = async () => {
    setLoading(true);
    try {
      const data = await api.getProblem(id);
      setProblem(data);

      // Default starter code depending on problem slug
      if (data.slug.includes('factorial')) {
        setCode('# Write your recursive factorial function here\n\ndef factorial(n):\n    # TODO: Implement base case and recursive step\n    pass\n\nif __name__ == "__main__":\n    n = int(input().strip())\n    print(factorial(n))\n');
      } else {
        setCode('# Write a Python program to print "Hello World" exactly 4 times using a loop\n\n');
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load problem.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickTemplate = (templateType) => {
    if (problem?.slug.includes('factorial')) {
      if (templateType === 'compliant') {
        setCode('def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n\nif __name__ == "__main__":\n    n = int(input().strip())\n    print(factorial(n))\n');
      } else if (templateType === 'violation') {
        // Uses loop instead of recursion
        setCode('def factorial(n):\n    ans = 1\n    for i in range(1, n + 1):\n        ans *= i\n    return ans\n\nif __name__ == "__main__":\n    n = int(input().strip())\n    print(factorial(n))\n');
      }
    } else {
      if (templateType === 'compliant') {
        setCode('for i in range(4):\n    print("Hello World")\n');
      } else if (templateType === 'violation') {
        setCode('print("Hello World")\nprint("Hello World")\nprint("Hello World")\nprint("Hello World")\n');
      } else if (templateType === 'syntax_err') {
        setCode('for i in range(4)\n    print("Hello World")\n');
      }
    }
  };

  const handleSubmit = async () => {
    if (!currentUser) {
      onOpenAuth();
      return;
    }

    setEvaluating(true);
    setErrorMsg(null);
    setEvalResult(null);

    try {
      const result = await api.createSubmission(problem.id, code, problem.version_number);
      setEvalResult(result);

      if (result.total_score === 100) {
        confetti({
          particleCount: 80,
          spread: 70,
          origin: { y: 0.6 },
        });
      }
    } catch (err) {
      setErrorMsg(err.message || 'Submission evaluation failed.');
    } finally {
      setEvaluating(false);
    }
  };

  if (loading) {
    return (
      <div className="container" style={{ textAlign: 'center', padding: '6rem' }}>
        Loading coding workspace...
      </div>
    );
  }

  if (!problem) {
    return (
      <div className="container" style={{ textAlign: 'center', padding: '6rem' }}>
        <h2>Problem not found</h2>
        <Link to="/" className="btn btn-primary" style={{ marginTop: '1rem' }}>Back to Problems</Link>
      </div>
    );
  }

  return (
    <div style={{ padding: '1rem 1.5rem', height: 'calc(100vh - 64px)', overflow: 'hidden' }}>
      <div className="split-layout">
        {/* Left Pane: Problem Description & Constraints */}
        <div className="glass-panel" style={{
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden',
          background: 'rgba(15, 23, 42, 0.95)',
        }}>
          {/* Top Bar */}
          <div style={{
            padding: '1rem 1.25rem',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)', textDecoration: 'none', fontSize: '0.825rem' }}>
              <ArrowLeft size={16} />
              <span>Back to Library</span>
            </Link>
            <span className={`badge badge-${problem.difficulty}`}>{problem.difficulty}</span>
          </div>

          {/* Problem Statement Content */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem' }}>
            <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.75rem' }}>
              {problem.title}
            </h1>

            {/* Concept Aware Banner */}
            <div style={{
              background: 'rgba(99, 102, 241, 0.12)',
              border: '1px solid rgba(99, 102, 241, 0.35)',
              borderRadius: 'var(--radius-sm)',
              padding: '0.85rem',
              marginBottom: '1.25rem',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#a5b4fc', fontSize: '0.825rem', fontWeight: 700, marginBottom: '0.25rem' }}>
                <Sparkles size={16} color="var(--accent-cyan)" />
                <span>CONCEPT COMPLIANCE ACTIVE</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-main)', lineHeight: 1.45 }}>
                Your solution is evaluated for both <strong>functional output</strong> and <strong>conceptual compliance</strong> using static AST analysis. Solutions matching outputs via shortcuts without the required constructs will have conceptual marks withheld.
              </p>
            </div>

            {/* Statement Markdown Render */}
            <div style={{
              fontSize: '0.9rem',
              color: 'var(--text-main)',
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
            }}>
              {problem.statement_markdown}
            </div>

            {/* Public Sample Test Cases */}
            <div style={{ marginTop: '1.75rem' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem', color: 'var(--text-main)' }}>
                Sample Test Cases
              </h3>
              {problem.sample_test_cases.map((sample, idx) => (
                <div key={sample.id} style={{
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '0.75rem',
                  marginBottom: '0.75rem',
                }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '0.35rem' }}>
                    Sample Case #{idx + 1}
                  </div>
                  {sample.input_data && (
                    <div style={{ marginBottom: '0.5rem' }}>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-subtle)' }}>Input:</div>
                      <pre style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', background: 'rgba(0,0,0,0.3)', padding: '0.4rem', borderRadius: '4px' }}>
                        {sample.input_data}
                      </pre>
                    </div>
                  )}
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-subtle)' }}>Expected Output:</div>
                    <pre style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', background: 'rgba(0,0,0,0.3)', padding: '0.4rem', borderRadius: '4px' }}>
                      {sample.expected_output}
                    </pre>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Pane: Code Editor & Live Evaluation Results */}
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '0.75rem' }}>
          {/* Editor Header & Quick Templates */}
          <div className="glass-panel" style={{
            padding: '0.75rem 1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(15, 23, 42, 0.95)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <FileCode2 size={16} color="var(--accent-cyan)" />
              <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Python 3.12 Editor</span>
            </div>

            {/* Preset template loaders to immediately demonstrate the difference */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-subtle)', marginRight: '0.2rem' }}>Load Preset:</span>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => handleQuickTemplate('compliant')}
                style={{ padding: '0.25rem 0.6rem', fontSize: '0.72rem', borderColor: 'rgba(16, 185, 129, 0.4)', color: '#34d399' }}
                title="Loads code that fulfills both functional output and required concepts"
              >
                Compliant
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => handleQuickTemplate('violation')}
                style={{ padding: '0.25rem 0.6rem', fontSize: '0.72rem', borderColor: 'rgba(244, 63, 94, 0.4)', color: '#fb7185' }}
                title="Matches output but violates required concepts"
              >
                Concept Violation
              </button>
            </div>
          </div>

          {/* Monaco Editor */}
          <div className="glass-panel" style={{
            flex: evalResult ? '0 0 45%' : '1',
            borderRadius: 'var(--radius-sm)',
            overflow: 'hidden',
            border: '1px solid var(--border-medium)',
            transition: 'flex 0.3s ease',
          }}>
            <Editor
              height="100%"
              defaultLanguage="python"
              theme="vs-dark"
              value={code}
              onChange={(newVal) => setCode(newVal || '')}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                fontFamily: 'var(--font-mono)',
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true,
                padding: { top: 12, bottom: 12 },
              }}
            />
          </div>

          {/* Run Action Bar */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-subtle)' }}>
              Execution sandbox: Non-root process, isolated memory, 3.0s wall-clock limit.
            </div>

            <button
              onClick={handleSubmit}
              disabled={evaluating}
              className="btn btn-primary"
              style={{ padding: '0.6rem 1.4rem', fontWeight: 600 }}
            >
              {evaluating ? (
                <>
                  <RefreshCw size={16} className="spin" />
                  <span>Evaluating AST & Tests...</span>
                </>
              ) : (
                <>
                  <Play size={16} fill="white" />
                  <span>Submit for Evaluation</span>
                </>
              )}
            </button>
          </div>

          {/* Evaluation Results Drawer */}
          {evalResult && (
            <div className="glass-panel-glow" style={{
              flex: '1',
              padding: '1.25rem',
              overflowY: 'auto',
              background: '#090d16',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}>
              {/* Score Summary Header */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '0.85rem',
                borderBottom: '1px solid var(--border-subtle)',
              }}>
                <div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Evaluation Result</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: evalResult.total_score === 100 ? '#34d399' : '#fbbf24' }}>
                    {evalResult.summary_feedback}
                  </div>
                </div>

                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  fontSize: '1.75rem',
                  fontWeight: 800,
                  fontFamily: 'var(--font-heading)',
                  color: evalResult.total_score === 100 ? '#34d399' : evalResult.total_score > 0 ? '#fbbf24' : '#f43f5e',
                }}>
                  <span>{evalResult.total_score}</span>
                  <span style={{ fontSize: '1rem', color: 'var(--text-subtle)' }}>/100</span>
                </div>
              </div>

              {/* 4-Criterion Weighted Score Breakdown */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.6rem' }}>
                {evalResult.criteria_scores.map((crit) => (
                  <div key={crit.criterion} style={{
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.6rem',
                  }}>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                      {crit.criterion.replace('_', ' ')}
                    </div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, margin: '0.2rem 0' }}>
                      {crit.awarded_points} <span style={{ fontSize: '0.7rem', color: 'var(--text-subtle)' }}>/ {crit.max_points}</span>
                    </div>
                    <div style={{
                      fontSize: '0.68rem',
                      fontWeight: 600,
                      color: crit.passed ? 'var(--accent-emerald)' : 'var(--accent-rose)'
                    }}>
                      {crit.passed ? 'PASSED' : 'WITHHELD'}
                    </div>
                  </div>
                ))}
              </div>

              {/* Static AST Concept Evidence */}
              <div>
                <div style={{ fontSize: '0.825rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--accent-cyan)' }}>
                  AST Concept Evidence Verified
                </div>
                {evalResult.concept_evidence.length === 0 ? (
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>No explicit concepts evaluated.</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                    {evalResult.concept_evidence.map((ev) => (
                      <div key={ev.rule_id} style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.6rem',
                        padding: '0.55rem 0.75rem',
                        background: ev.passed ? 'rgba(16, 185, 129, 0.08)' : 'rgba(244, 63, 94, 0.08)',
                        border: `1px solid ${ev.passed ? 'rgba(16, 185, 129, 0.25)' : 'rgba(244, 63, 94, 0.25)'}`,
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.8rem',
                      }}>
                        {ev.passed ? (
                          <CheckCircle2 size={16} color="var(--accent-emerald)" />
                        ) : (
                          <XCircle size={16} color="var(--accent-rose)" />
                        )}
                        <span style={{ color: ev.passed ? '#d1fae5' : '#ffe4e6' }}>
                          {ev.message}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Actionable Pedagogical Feedback */}
              {evalResult.actionable_suggestions.length > 0 && (
                <div style={{
                  background: 'rgba(245, 158, 11, 0.1)',
                  border: '1px solid rgba(245, 158, 11, 0.3)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '0.75rem',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#fbbf24', fontSize: '0.8rem', fontWeight: 700, marginBottom: '0.35rem' }}>
                    <Lightbulb size={15} />
                    <span>Actionable Recommendations</span>
                  </div>
                  <ul style={{ paddingLeft: '1.25rem', fontSize: '0.78rem', color: 'var(--text-main)' }}>
                    {evalResult.actionable_suggestions.map((sug, i) => (
                      <li key={i} style={{ marginBottom: '0.2rem' }}>{sug}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
