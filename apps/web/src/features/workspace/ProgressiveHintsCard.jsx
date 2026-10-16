import React from 'react';
import {
  Lightbulb,
  ChevronDown,
  ChevronRight,
  Eye,
  CheckCircle2,
  Sparkles,
  HelpCircle,
} from 'lucide-react';

export default function ProgressiveHintsCard({
  hints,
  revealedLevel = 0,
  onRevealNext,
  onShowSolution,
  loading = false,
}) {
  if (!hints && !loading) return null;

  const tier1 = hints?.tier_1_general;
  const tier2 = hints?.tier_2_concept;
  const tier3 = hints?.tier_3_targeted;

  return (
    <div
      style={{
        background: 'rgba(30, 41, 59, 0.7)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        borderRadius: '8px',
        padding: '0.85rem 1rem',
        marginTop: '0.65rem',
        marginBottom: '0.65rem',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '0.6rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
          <Lightbulb size={16} color="var(--accent-amber)" />
          <span style={{ fontSize: '0.825rem', fontWeight: 700, color: '#ffffff' }}>
            Progressive Learning Hints
          </span>
          <span
            style={{
              fontSize: '0.68rem',
              color: 'var(--text-muted)',
              background: 'rgba(0,0,0,0.3)',
              padding: '0.1rem 0.45rem',
              borderRadius: '9999px',
              border: '1px solid var(--border-subtle)',
            }}
          >
            {revealedLevel}/3 Unlocked
          </span>
        </div>

        {revealedLevel < 3 && (
          <button
            type="button"
            onClick={onRevealNext}
            disabled={loading}
            style={{
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.3), rgba(6, 182, 212, 0.2))',
              border: '1px solid var(--border-glow)',
              color: '#ffffff',
              padding: '0.25rem 0.65rem',
              borderRadius: '4px',
              fontSize: '0.72rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.3rem',
            }}
          >
            <Eye size={12} />
            <span>
              {revealedLevel === 0 ? 'Unlock Hint 1' : `Unlock Hint ${revealedLevel + 1}`}
            </span>
          </button>
        )}
      </div>

      <div style={{ fontSize: '0.72rem', color: 'var(--text-subtle)', marginBottom: '0.65rem' }}>
        Work through hints step-by-step to correct your logic before looking at the full solution.
      </div>

      {/* Hints List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {/* Tier 1 */}
        {revealedLevel >= 1 && (
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(99, 102, 241, 0.25)',
              borderRadius: '6px',
              padding: '0.6rem 0.85rem',
              animation: 'fadeIn 0.2s ease',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.25rem' }}>
              <span
                style={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  color: 'var(--accent-primary)',
                  letterSpacing: '0.04em',
                }}
              >
                Hint 1 · General Direction
              </span>
            </div>
            <div style={{ fontSize: '0.78rem', color: '#cbd5e1', lineHeight: 1.45 }}>
              {tier1 || 'Consider boundary cases and check that your function processes all inputs.'}
            </div>
          </div>
        )}

        {/* Tier 2 */}
        {revealedLevel >= 2 && (
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(6, 182, 212, 0.25)',
              borderRadius: '6px',
              padding: '0.6rem 0.85rem',
              animation: 'fadeIn 0.2s ease',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.25rem' }}>
              <span
                style={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  color: 'var(--accent-cyan)',
                  letterSpacing: '0.04em',
                }}
              >
                Hint 2 · Algorithm & Data Structure
              </span>
            </div>
            <div style={{ fontSize: '0.78rem', color: '#cbd5e1', lineHeight: 1.45 }}>
              {tier2 || 'Identify which algorithmic paradigm or data structure matches the required time complexity.'}
            </div>
          </div>
        )}

        {/* Tier 3 */}
        {revealedLevel >= 3 && (
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
              borderRadius: '6px',
              padding: '0.6rem 0.85rem',
              animation: 'fadeIn 0.2s ease',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.25rem' }}>
              <span
                style={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  color: 'var(--accent-emerald)',
                  letterSpacing: '0.04em',
                }}
              >
                Hint 3 · Targeted Guidance
              </span>
            </div>
            <div style={{ fontSize: '0.78rem', color: '#cbd5e1', lineHeight: 1.45 }}>
              {tier3 || 'Inspect how variables transition during each iteration or recursion step.'}
            </div>
          </div>
        )}
      </div>

      {/* Solution Option Prompt */}
      <div
        style={{
          marginTop: '0.65rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingTop: '0.45rem',
          borderTop: '1px solid var(--border-subtle)',
        }}
      >
        <span style={{ fontSize: '0.7rem', color: 'var(--text-subtle)' }}>
          {revealedLevel === 3
            ? 'All hints revealed. Still stuck?'
            : 'Want to study the complete verified solution?'}
        </span>
        {onShowSolution && (
          <button
            type="button"
            onClick={onShowSolution}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--accent-cyan)',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
              padding: '0.15rem 0.35rem',
            }}
          >
            <Sparkles size={12} />
            <span>Show Correct Solution</span>
          </button>
        )}
      </div>
    </div>
  );
}
