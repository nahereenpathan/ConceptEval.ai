import React from 'react';
import {
  AlertTriangle,
  Lightbulb,
  CheckCircle2,
  XCircle,
  FileCode,
  Terminal,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';

export default function IntelligentFeedbackCard({
  feedback,
  onShowHints,
  onShowSolution,
}) {
  if (!feedback) return null;

  const {
    category,
    summary,
    diagnostic_details,
    compiler_sanitized,
    runtime_sanitized,
    concept_guidance,
    actionable_recommendation,
  } = feedback;

  const getCategoryConfig = (cat) => {
    switch (cat) {
      case 'compilation_error':
        return {
          label: 'Compilation Diagnostic',
          color: '#fb7185',
          bg: 'rgba(244, 63, 94, 0.12)',
          border: 'rgba(244, 63, 94, 0.35)',
          icon: <Terminal size={15} color="#fb7185" />,
        };
      case 'runtime_error':
        return {
          label: 'Runtime Exception',
          color: '#f87171',
          bg: 'rgba(239, 68, 68, 0.12)',
          border: 'rgba(239, 68, 68, 0.35)',
          icon: <AlertTriangle size={15} color="#f87171" />,
        };
      case 'concept_requirement_not_satisfied':
        return {
          label: 'Concept Requirement Missing',
          color: '#fbbf24',
          bg: 'rgba(245, 158, 11, 0.12)',
          border: 'rgba(245, 158, 11, 0.35)',
          icon: <ShieldAlert size={15} color="#fbbf24" />,
        };
      case 'time_limit_exceeded':
        return {
          label: 'Time Limit Exceeded',
          color: '#f59e0b',
          bg: 'rgba(245, 158, 11, 0.12)',
          border: 'rgba(245, 158, 11, 0.35)',
          icon: <AlertTriangle size={15} color="#f59e0b" />,
        };
      case 'wrong_answer':
      default:
        return {
          label: 'Logical / Output Mismatch',
          color: '#38bdf8',
          bg: 'rgba(56, 189, 248, 0.12)',
          border: 'rgba(56, 189, 248, 0.35)',
          icon: <Lightbulb size={15} color="#38bdf8" />,
        };
    }
  };

  const config = getCategoryConfig(category);

  return (
    <div
      style={{
        background: config.bg,
        border: `1px solid ${config.border}`,
        borderRadius: '8px',
        padding: '0.85rem 1rem',
        marginBottom: '0.75rem',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '0.5rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
          {config.icon}
          <span
            style={{
              fontSize: '0.75rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: config.color,
            }}
          >
            {config.label}
          </span>
        </div>
        <span
          style={{
            fontSize: '0.68rem',
            color: 'var(--text-subtle)',
            background: 'rgba(0,0,0,0.25)',
            padding: '0.15rem 0.45rem',
            borderRadius: '4px',
          }}
        >
          Automated Feedback
        </span>
      </div>

      {/* Summary Message */}
      {summary && (
        <div
          style={{
            fontSize: '0.825rem',
            fontWeight: 600,
            color: '#ffffff',
            lineHeight: 1.4,
            marginBottom: '0.4rem',
          }}
        >
          {summary}
        </div>
      )}

      {/* Diagnostic Details */}
      {diagnostic_details && (
        <div
          style={{
            fontSize: '0.78rem',
            color: '#cbd5e1',
            lineHeight: 1.45,
            marginBottom: '0.5rem',
          }}
        >
          {diagnostic_details}
        </div>
      )}

      {/* Sanitized Compiler / Runtime Output */}
      {(compiler_sanitized || runtime_sanitized) && (
        <div style={{ marginBottom: '0.5rem' }}>
          <div
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-subtle)',
              marginBottom: '0.2rem',
              fontWeight: 600,
            }}
          >
            Sanitized Diagnostics:
          </div>
          <pre
            style={{
              margin: 0,
              padding: '0.45rem 0.65rem',
              background: 'rgba(0, 0, 0, 0.45)',
              borderRadius: '4px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.72rem',
              color: '#fca5a5',
              whiteSpace: 'pre-wrap',
              maxHeight: '110px',
              overflowY: 'auto',
            }}
          >
            {compiler_sanitized || runtime_sanitized}
          </pre>
        </div>
      )}

      {/* Concept Guidance */}
      {concept_guidance && (
        <div
          style={{
            background: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid rgba(245, 158, 11, 0.25)',
            borderRadius: '6px',
            padding: '0.45rem 0.65rem',
            marginBottom: '0.5rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.4rem',
          }}
        >
          <ShieldAlert size={14} color="#fbbf24" style={{ marginTop: '0.15rem', flexShrink: 0 }} />
          <div style={{ fontSize: '0.75rem', color: '#fef3c7', lineHeight: 1.4 }}>
            <strong>Required Concept:</strong> {concept_guidance}
          </div>
        </div>
      )}

      {/* Actionable Recommendation */}
      {actionable_recommendation && (
        <div
          style={{
            background: 'rgba(16, 185, 129, 0.08)',
            border: '1px solid rgba(16, 185, 129, 0.2)',
            borderRadius: '6px',
            padding: '0.45rem 0.65rem',
            marginBottom: '0.65rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.4rem',
          }}
        >
          <Lightbulb size={14} color="#34d399" style={{ marginTop: '0.15rem', flexShrink: 0 }} />
          <div style={{ fontSize: '0.75rem', color: '#d1fae5', lineHeight: 1.4 }}>
            <strong>Next Step:</strong> {actionable_recommendation}
          </div>
        </div>
      )}

      {/* Quick Action Buttons */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', paddingTop: '0.25rem' }}>
        {onShowHints && (
          <button
            type="button"
            onClick={onShowHints}
            style={{
              background: 'rgba(99, 102, 241, 0.2)',
              border: '1px solid rgba(99, 102, 241, 0.4)',
              borderRadius: '4px',
              padding: '0.25rem 0.6rem',
              color: '#c7d2fe',
              fontSize: '0.72rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '0.3rem',
              cursor: 'pointer',
            }}
          >
            <Lightbulb size={12} />
            <span>Need a Hint?</span>
          </button>
        )}

        {onShowSolution && (
          <button
            type="button"
            onClick={onShowSolution}
            style={{
              background: 'rgba(6, 182, 212, 0.15)',
              border: '1px solid rgba(6, 182, 212, 0.35)',
              borderRadius: '4px',
              padding: '0.25rem 0.6rem',
              color: '#a5f3fc',
              fontSize: '0.72rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '0.3rem',
              cursor: 'pointer',
            }}
          >
            <CheckCircle2 size={12} />
            <span>Show Correct Solution</span>
          </button>
        )}
      </div>
    </div>
  );
}
