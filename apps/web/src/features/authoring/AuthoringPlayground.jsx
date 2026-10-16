import React, { useState } from 'react';
import { Sparkles, CheckCircle2, AlertCircle, ShieldAlert, Cpu, ArrowRight } from 'lucide-react';

export default function AuthoringPlayground() {
  const [problemPrompt, setProblemPrompt] = useState(
    'Write a Python program to reverse a list recursively without using loops or built-in reverse.'
  );
  const [extractionResult, setExtractionResult] = useState(null);
  const [extracting, setExtracting] = useState(false);

  // Client-side NLP extractor demo mirroring the backend NLP service
  const handleExtract = () => {
    setExtracting(true);
    const cleaned = problemPrompt.toLowerCase();
    const concepts = [];
    const prohibitions = [];
    const notes = [];
    let confidence = 0.95;

    // Concepts
    if (/using (a |the )?(loop|for loop|while loop)|iterate|iteration|looping/.test(cleaned)) {
      concepts.push({
        concept: 'loop',
        accepted: ['for', 'while'],
        desc: 'Requires iterative execution using a loop (for or while).',
      });
    }

    if (/recursive|recursion|recursively|call(s)? itself/.test(cleaned)) {
      concepts.push({
        concept: 'recursion',
        accepted: ['recursion'],
        desc: 'Requires recursive function call with a base case.',
      });
    }

    if (/list comprehension|dict comprehension/.test(cleaned)) {
      concepts.push({
        concept: 'comprehension',
        accepted: ['list_comprehension', 'dict_comprehension'],
        desc: 'Requires Python comprehension construct.',
      });
    }

    // Prohibitions
    if (/without (using )?loops?|no loops? allowed|do not use (a )?loop/.test(cleaned)) {
      prohibitions.push({
        construct: 'loop',
        targets: ['for', 'while'],
        desc: 'Loops are strictly prohibited.',
      });
    }

    if (/without (using )?built-?in|do not use built-?in/.test(cleaned)) {
      prohibitions.push({
        construct: 'specific_builtin',
        targets: ['reverse', 'reversed'],
        desc: 'Built-in reversal functions prohibited.',
      });
    }

    if (concepts.length === 0 && prohibitions.length === 0) {
      confidence = 0.50;
      notes.push('No explicit concept keywords detected. Problem will be graded on functional correctness only.');
    }

    const requiresReview = confidence < 0.80 || notes.length > 0;

    const rubricDraft = {
      schema_version: '1.0.0',
      max_score: 100.0,
      functional_weight: 40.0,
      concept_weight: concepts.length > 0 ? 35.0 : 0.0,
      algorithmic_weight: concepts.length > 0 ? 15.0 : 40.0,
      constraint_weight: prohibitions.length > 0 ? 10.0 : 20.0,
      required_concepts: concepts,
      prohibited_constructs: prohibitions,
    };

    setTimeout(() => {
      setExtractionResult({
        concepts,
        prohibitions,
        confidence,
        requiresReview,
        notes,
        rubricDraft,
      });
      setExtracting(false);
    }, 300);
  };

  return (
    <div className="container" style={{ maxWidth: '1000px', paddingBottom: '4rem' }}>
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.4rem',
          background: 'rgba(6, 182, 212, 0.1)',
          border: '1px solid rgba(6, 182, 212, 0.3)',
          padding: '0.3rem 0.8rem',
          borderRadius: 'var(--radius-full)',
          fontSize: '0.75rem',
          color: 'var(--accent-cyan)',
          fontWeight: 600,
          marginBottom: '0.75rem',
        }}>
          <Sparkles size={14} />
          <span>PHASE 6 & 7: NLP INTENT SERVICE</span>
        </div>
        <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: '2.2rem', fontWeight: 800 }}>
          NLP Intent Extraction & Rubric Authoring
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
          Extract required programming concepts, prohibited constructs, and generate versioned rubrics from plain English prompts.
        </p>
      </div>

      {/* Authoring Card */}
      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>
          Problem Description or Constraint Prompt
        </label>
        <textarea
          rows={4}
          value={problemPrompt}
          onChange={(e) => setProblemPrompt(e.target.value)}
          placeholder="e.g. Write a program to print Hello World exactly 4 times using a loop..."
          style={{
            width: '100%',
            padding: '0.75rem',
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-sm)',
            color: 'white',
            fontFamily: 'var(--font-sans)',
            fontSize: '0.9rem',
            lineHeight: 1.5,
            resize: 'vertical',
            marginBottom: '1rem',
          }}
        />

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={handleExtract}
            disabled={extracting}
            className="btn btn-primary"
            style={{ padding: '0.55rem 1.25rem' }}
          >
            <Cpu size={16} />
            <span>{extracting ? 'Extracting Intent...' : 'Extract Concepts & Draft Rubric'}</span>
          </button>
        </div>
      </div>

      {/* Extraction Results */}
      {extractionResult && (
        <div className="glass-panel-glow" style={{ padding: '1.5rem', background: '#090d16' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingBottom: '1rem',
            borderBottom: '1px solid var(--border-subtle)',
            marginBottom: '1.25rem',
          }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>NLP Intent Pipeline</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-main)' }}>
                Extraction Analysis
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{
                background: extractionResult.confidence >= 0.8 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                border: `1px solid ${extractionResult.confidence >= 0.8 ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
                padding: '0.25rem 0.65rem',
                borderRadius: 'var(--radius-full)',
                fontSize: '0.75rem',
                fontWeight: 600,
                color: extractionResult.confidence >= 0.8 ? '#34d399' : '#fbbf24',
              }}>
                Confidence: {(extractionResult.confidence * 100).toFixed(0)}%
              </div>

              <div style={{
                background: extractionResult.requiresReview ? 'rgba(245, 158, 11, 0.15)' : 'rgba(99, 102, 241, 0.15)',
                border: `1px solid ${extractionResult.requiresReview ? 'rgba(245, 158, 11, 0.3)' : 'rgba(99, 102, 241, 0.3)'}`,
                padding: '0.25rem 0.65rem',
                borderRadius: 'var(--radius-full)',
                fontSize: '0.75rem',
                fontWeight: 600,
                color: extractionResult.requiresReview ? '#fbbf24' : '#a5b4fc',
              }}>
                {extractionResult.requiresReview ? 'Review Required' : 'Ready for Approval'}
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
            {/* Detected Concepts */}
            <div style={{ background: 'var(--bg-card)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#a5b4fc', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.6rem' }}>
                <CheckCircle2 size={16} color="var(--accent-primary)" />
                <span>Required Concepts Detected</span>
              </div>
              {extractionResult.concepts.length === 0 ? (
                <div style={{ fontSize: '0.8rem', color: 'var(--text-subtle)' }}>None explicitly identified.</div>
              ) : (
                extractionResult.concepts.map((c, i) => (
                  <div key={i} style={{ fontSize: '0.8rem', marginBottom: '0.4rem' }}>
                    <strong style={{ color: 'var(--text-main)', textTransform: 'capitalize' }}>{c.concept}</strong>: {c.desc}
                  </div>
                ))
              )}
            </div>

            {/* Detected Prohibitions */}
            <div style={{ background: 'var(--bg-card)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#fb7185', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.6rem' }}>
                <ShieldAlert size={16} color="var(--accent-rose)" />
                <span>Prohibited Constructs Detected</span>
              </div>
              {extractionResult.prohibitions.length === 0 ? (
                <div style={{ fontSize: '0.8rem', color: 'var(--text-subtle)' }}>No forbidden constructs specified.</div>
              ) : (
                extractionResult.prohibitions.map((p, i) => (
                  <div key={i} style={{ fontSize: '0.8rem', marginBottom: '0.4rem' }}>
                    <strong style={{ color: 'var(--accent-rose)', textTransform: 'capitalize' }}>{p.construct}</strong>: {p.desc}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Generated Rubric JSON Schema */}
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--accent-cyan)' }}>
              Generated Draft Rubric (100% Weighted Balance)
            </div>
            <pre style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.78rem',
              background: 'rgba(0,0,0,0.5)',
              padding: '1rem',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
              color: '#a5b4fc',
              overflowX: 'auto',
            }}>
              {JSON.stringify(extractionResult.rubricDraft, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
