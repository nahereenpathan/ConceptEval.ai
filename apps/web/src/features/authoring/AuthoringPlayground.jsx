import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ShieldAlert,
  Cpu,
  ArrowRight,
  Plus,
  Trash2,
  Play,
  Send,
  Eye,
  FileCode2,
  RefreshCw,
  BookOpen,
  Check,
} from 'lucide-react';
import { api } from '../../api/client';

export default function AuthoringPlayground({ currentUser, onOpenAuth }) {
  // Navigation tabs
  const [activeTab, setActiveTab] = useState('studio'); // 'studio' | 'my_problems'

  // NLP Assist prompt
  const [nlpPrompt, setNlpPrompt] = useState(
    'Write a Python program to find the sum of all even numbers in a list using a loop. Prohibit using built-in sum().'
  );
  const [extracting, setExtracting] = useState(false);
  const [extractionResult, setExtractionResult] = useState(null);

  // Authoring Form State
  const [title, setTitle] = useState('Sum of Even Numbers in a List');
  const [slug, setSlug] = useState('');
  const [difficulty, setDifficulty] = useState('easy');
  const [language, setLanguage] = useState('python');
  const [topics, setTopics] = useState('Loops & Iteration, Arrays');
  const [statement, setStatement] = useState(
    'Given a list of integers on standard input, compute and print the sum of all even numbers in the list.\n\nYou must explicitly use a `for` or `while` loop construct. Do NOT use the built-in `sum()` function.'
  );
  const [inputFormat, setInputFormat] = useState('Space-separated integers on standard input.');
  const [outputFormat, setOutputFormat] = useState('A single integer: the sum of the even numbers.');
  const [constraints, setConstraints] = useState('1 <= len(nums) <= 1000\n-1000 <= nums[i] <= 1000');
  const [starterCode, setStarterCode] = useState(
    'import sys\n\ndef sum_even(nums):\n    # TODO: Implement using a loop\n    pass\n\nif __name__ == "__main__":\n    line = sys.stdin.read().strip()\n    if line:\n        nums = [int(x) for x in line.split()]\n        print(sum_even(nums))\n'
  );
  const [referenceSolution, setReferenceSolution] = useState(
    'import sys\n\ndef sum_even(nums):\n    total = 0\n    for n in nums:\n        if n % 2 == 0:\n            total += n\n    return total\n\nif __name__ == "__main__":\n    line = sys.stdin.read().strip()\n    if line:\n        nums = [int(x) for x in line.split()]\n        print(sum_even(nums))\n'
  );

  // Test Cases
  const [testCases, setTestCases] = useState([
    {
      input_data: '1 2 3 4 5 6\n',
      expected_output: '12',
      visibility: 'sample',
      timeout_ms: 3000,
      memory_limit_mb: 128,
    },
    {
      input_data: '1 3 5 7\n',
      expected_output: '0',
      visibility: 'sample',
      timeout_ms: 3000,
      memory_limit_mb: 128,
    },
    {
      input_data: '-2 4 -6 8 10\n',
      expected_output: '14',
      visibility: 'hidden',
      timeout_ms: 3000,
      memory_limit_mb: 128,
    },
  ]);

  // Concept Rules & Prohibitions
  const [conceptRules, setConceptRules] = useState([
    {
      concept: 'loop',
      required: true,
      min_occurrences: 1,
      description: 'Must use a for or while loop',
    },
  ]);
  const [prohibitions, setProhibitions] = useState(['sum']);
  const [functionalWeight, setFunctionalWeight] = useState(60.0);
  const [conceptWeight, setConceptWeight] = useState(40.0);

  // Validation & Publishing State
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [publishing, setPublishing] = useState(false);
  const [publishSuccess, setPublishSuccess] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // My Authored Problems
  const [authoredProblems, setAuthoredProblems] = useState([]);
  const [loadingAuthored, setLoadingAuthored] = useState(false);

  useEffect(() => {
    if (activeTab === 'my_problems') {
      loadAuthoredProblems();
    }
  }, [activeTab]);

  const loadAuthoredProblems = async () => {
    setLoadingAuthored(true);
    try {
      const data = await api.getAuthoredProblems();
      setAuthoredProblems(Array.isArray(data) ? data : []);
    } catch {
      // Ignored if unauthenticated or student
    } finally {
      setLoadingAuthored(false);
    }
  };

  // Step 1: NLP Intent Extraction & Rubric Draft
  const handleExtractIntent = async () => {
    setExtracting(true);
    setErrorMsg(null);
    try {
      const data = await api.extractIntent(nlpPrompt);
      setExtractionResult({
        concepts: data.extracted_concepts,
        prohibitions: data.extracted_prohibitions,
        confidence: data.confidence,
        requiresReview: data.requires_human_review,
        notes: data.review_notes,
        rubricDraft: data.rubric_draft,
      });

      // Populate concept rules
      if (data.extracted_concepts && data.extracted_concepts.length > 0) {
        setConceptRules(
          data.extracted_concepts.map((c) => ({
            concept: c.concept,
            required: true,
            min_occurrences: 1,
            description: c.desc || `Requires ${c.concept}`,
          }))
        );
      }

      // Populate prohibitions
      if (data.extracted_prohibitions && data.extracted_prohibitions.length > 0) {
        setProhibitions(data.extracted_prohibitions.map((p) => p.construct));
      }

      // Suggest title from prompt
      const words = nlpPrompt.split(' ').slice(0, 7).join(' ');
      setTitle(words.replace(/^(write a program to|write a python program to)\s*/i, '').trim() || title);
    } catch (err) {
      setErrorMsg(err.message || 'Intent extraction failed.');
    } finally {
      setExtracting(false);
    }
  };

  // Add / Remove Test Case
  const handleAddTestCase = (visibility = 'sample') => {
    setTestCases([
      ...testCases,
      {
        input_data: '',
        expected_output: '',
        visibility,
        timeout_ms: 3000,
        memory_limit_mb: 128,
      },
    ]);
  };

  const handleRemoveTestCase = (index) => {
    setTestCases(testCases.filter((_, idx) => idx !== index));
  };

  const handleUpdateTestCase = (index, field, value) => {
    const updated = [...testCases];
    updated[index][field] = value;
    setTestCases(updated);
  };

  // Add / Remove Concept Rule
  const handleAddConceptRule = () => {
    setConceptRules([
      ...conceptRules,
      {
        concept: 'loop',
        required: true,
        min_occurrences: 1,
        description: '',
      },
    ]);
  };

  const handleRemoveConceptRule = (index) => {
    setConceptRules(conceptRules.filter((_, idx) => idx !== index));
  };

  const handleUpdateConceptRule = (index, field, value) => {
    const updated = [...conceptRules];
    updated[index][field] = value;
    setConceptRules(updated);
  };

  // Step 2: Validate Reference Solution in Sandbox
  const handleValidate = async () => {
    setValidating(true);
    setErrorMsg(null);
    setValidationResult(null);

    try {
      const res = await api.validateAuthoredProblem({
        source_code: referenceSolution,
        language: language,
        test_cases: testCases,
        concept_rules: conceptRules,
        prohibited_constructs: prohibitions,
      });
      setValidationResult(res);
    } catch (err) {
      setErrorMsg(err.message || 'Sandbox validation failed.');
    } finally {
      setValidating(false);
    }
  };

  // Step 3: Save Draft or Publish Problem
  const handleSaveProblem = async (publishStatus = 'draft') => {
    setPublishing(true);
    setErrorMsg(null);
    setPublishSuccess(null);

    const payload = {
      title,
      slug: slug.trim() || undefined,
      statement_markdown: statement,
      difficulty,
      language: language,
      topics: topics.split(',').map((t) => t.trim()).filter(Boolean),
      constraints: constraints.split('\n').filter(Boolean),
      input_format: inputFormat,
      output_format: outputFormat,
      starter_code: starterCode,
      reference_solution: referenceSolution,
      test_cases: testCases,
      concept_rules: conceptRules,
      prohibited_constructs: prohibitions,
      functional_weight: parseFloat(functionalWeight) || 60.0,
      concept_weight: parseFloat(conceptWeight) || 40.0,
      status: publishStatus,
    };

    try {
      const created = await api.createAuthoredProblem(payload);
      setPublishSuccess({
        id: created.id,
        slug: created.slug,
        title: created.title,
        status: created.status,
      });
      loadAuthoredProblems();
    } catch (err) {
      if (err.status === 403) {
        setErrorMsg('Authorization Error: Only logged in teachers or administrators are permitted to publish problems.');
      } else {
        setErrorMsg(err.message || 'Failed to save problem.');
      }
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="container" style={{ maxWidth: '1100px', paddingBottom: '4rem' }}>
      {/* Page Title & Navigation Tabs */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.4rem',
            background: 'rgba(6, 182, 212, 0.1)',
            border: '1px solid rgba(6, 182, 212, 0.3)',
            padding: '0.25rem 0.65rem',
            borderRadius: 'var(--radius-full)',
            fontSize: '0.75rem',
            color: 'var(--accent-cyan)',
            fontWeight: 600,
            marginBottom: '0.5rem',
          }}>
            <Sparkles size={14} />
            <span>TEACHER AUTHORING STUDIO</span>
          </div>
          <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: '2rem', fontWeight: 800, margin: 0 }}>
            Question Authoring & Concept Studio
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.25rem' }}>
            Author original coding problems, extract candidate rubrics with NLP, and enforce AST concept rules.
          </p>
        </div>

        {/* Tab switch */}
        <div style={{ display: 'flex', background: 'rgba(30, 41, 59, 0.6)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', padding: '0.2rem' }}>
          <button
            onClick={() => setActiveTab('studio')}
            style={{
              background: activeTab === 'studio' ? 'rgba(99, 102, 241, 0.3)' : 'transparent',
              border: 'none',
              color: activeTab === 'studio' ? '#ffffff' : 'var(--text-muted)',
              padding: '0.4rem 0.9rem',
              borderRadius: '4px',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Create Problem
          </button>
          <button
            onClick={() => setActiveTab('my_problems')}
            style={{
              background: activeTab === 'my_problems' ? 'rgba(99, 102, 241, 0.3)' : 'transparent',
              border: 'none',
              color: activeTab === 'my_problems' ? '#ffffff' : 'var(--text-muted)',
              padding: '0.4rem 0.9rem',
              borderRadius: '4px',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            My Authored Problems ({authoredProblems.length})
          </button>
        </div>
      </div>

      {/* SUCCESS NOTIFICATION */}
      {publishSuccess && (
        <div style={{
          background: 'rgba(16, 185, 129, 0.12)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          borderRadius: 'var(--radius-sm)',
          padding: '1rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <CheckCircle2 size={20} color="var(--accent-emerald)" />
            <div>
              <div style={{ fontWeight: 700, color: '#34d399', fontSize: '0.9rem' }}>
                Problem {publishSuccess.status === 'published' ? 'Published Successfully' : 'Saved as Draft'}!
              </div>
              <div style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                "{publishSuccess.title}" is now recorded in the catalog.
              </div>
            </div>
          </div>

          <Link
            to={`/problems/${publishSuccess.slug || publishSuccess.id}`}
            className="btn btn-primary"
            style={{ padding: '0.4rem 0.9rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}
          >
            <Eye size={14} />
            <span>Open in Workspace</span>
          </Link>
        </div>
      )}

      {/* ERROR ALERT */}
      {errorMsg && (
        <div style={{
          background: 'rgba(244, 63, 94, 0.1)',
          border: '1px solid rgba(244, 63, 94, 0.3)',
          borderRadius: 'var(--radius-sm)',
          padding: '0.85rem 1rem',
          color: '#fb7185',
          fontSize: '0.85rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          marginBottom: '1.5rem',
        }}>
          <AlertCircle size={18} color="var(--accent-rose)" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* TAB 1: AUTHORING STUDIO */}
      {activeTab === 'studio' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Section 1: NLP Prompt Assist */}
          <div className="glass-panel" style={{ padding: '1.25rem', background: 'rgba(15, 23, 42, 0.8)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--accent-cyan)', fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.4rem' }}>
              <Cpu size={16} />
              <span>STEP 1: NLP INTENT & RUBRIC ASSIST (OPTIONAL)</span>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
              Describe what the problem requires in plain English. The backend NLP engine extracts intent, required programming concepts, and prohibited constructs for human review.
            </p>

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <input
                type="text"
                value={nlpPrompt}
                onChange={(e) => setNlpPrompt(e.target.value)}
                placeholder="e.g. Write a program to calculate factorial using recursion without loops..."
                style={{
                  flex: 1,
                  padding: '0.6rem 0.85rem',
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-medium)',
                  borderRadius: 'var(--radius-sm)',
                  color: '#ffffff',
                  fontSize: '0.85rem',
                }}
              />
              <button
                onClick={handleExtractIntent}
                disabled={extracting}
                className="btn btn-primary"
                style={{ padding: '0.6rem 1.25rem', fontSize: '0.825rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
              >
                {extracting ? <RefreshCw size={14} className="spin" /> : <Sparkles size={14} />}
                <span>{extracting ? 'Analyzing...' : 'Extract Intent'}</span>
              </button>
            </div>

            {/* Extraction Insights */}
            {extractionResult && (
              <div style={{ marginTop: '0.85rem', padding: '0.75rem', background: 'rgba(99, 102, 241, 0.08)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(99, 102, 241, 0.25)', fontSize: '0.8rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                  <span style={{ fontWeight: 600, color: '#a5b4fc' }}>Intent Extraction Results:</span>
                  <span style={{ color: '#34d399', fontWeight: 600 }}>Confidence: {(extractionResult.confidence * 100).toFixed(0)}%</span>
                </div>
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                  <div>
                    <span style={{ color: 'var(--text-subtle)' }}>Detected Concepts: </span>
                    <strong style={{ color: 'var(--accent-cyan)' }}>
                      {extractionResult.concepts.map((c) => c.concept).join(', ') || 'None'}
                    </strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-subtle)' }}>Prohibitions: </span>
                    <strong style={{ color: 'var(--accent-rose)' }}>
                      {extractionResult.prohibitions.map((p) => p.construct).join(', ') || 'None'}
                    </strong>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Section 2: Problem Metadata */}
          <div className="glass-panel" style={{ padding: '1.25rem', background: 'rgba(15, 23, 42, 0.8)' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '1rem', color: '#ffffff' }}>
              STEP 2: PROBLEM SPECIFICATIONS & STATEMENT
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Problem Title *
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  style={{ width: '100%', padding: '0.55rem', background: 'var(--bg-tertiary)', border: '1px solid var(--border-medium)', borderRadius: 'var(--radius-sm)', color: '#fff', fontSize: '0.85rem' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Language
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  style={{ width: '100%', padding: '0.55rem', background: 'var(--bg-tertiary)', border: '1px solid var(--border-medium)', borderRadius: 'var(--radius-sm)', color: '#fff', fontSize: '0.85rem' }}
                >
                  <option value="python">Python 3.12</option>
                  <option value="java">Java (JDK)</option>
                  <option value="cpp">C++ (g++)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Difficulty
                </label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  style={{ width: '100%', padding: '0.55rem', background: 'var(--bg-tertiary)', border: '1px solid var(--border-medium)', borderRadius: 'var(--radius-sm)', color: '#fff', fontSize: '0.85rem' }}
                >
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Topic Tags (comma-separated)
                </label>
                <input
                  type="text"
                  value={topics}
                  onChange={(e) => setTopics(e.target.value)}
                  placeholder="e.g. Loops, Arrays"
                  style={{ width: '100%', padding: '0.55rem', background: 'var(--bg-tertiary)', border: '1px solid var(--border-medium)', borderRadius: 'var(--radius-sm)', color: '#fff', fontSize: '0.85rem' }}
                />
              </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                Problem Statement (Markdown) *
              </label>
              <textarea
                rows={5}
                value={statement}
                onChange={(e) => setStatement(e.target.value)}
                style={{ width: '100%', padding: '0.65rem', background: 'var(--bg-tertiary)', border: '1px solid var(--border-medium)', borderRadius: 'var(--radius-sm)', color: '#fff', fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Input Format
                </label>
                <textarea
                  rows={2}
                  value={inputFormat}
                  onChange={(e) => setInputFormat(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', background: 'var(--bg-tertiary)', border: '1px solid var(--border-medium)', borderRadius: 'var(--radius-sm)', color: '#fff', fontSize: '0.8rem' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Output Format
                </label>
                <textarea
                  rows={2}
                  value={outputFormat}
                  onChange={(e) => setOutputFormat(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', background: 'var(--bg-tertiary)', border: '1px solid var(--border-medium)', borderRadius: 'var(--radius-sm)', color: '#fff', fontSize: '0.8rem' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Constraints (one per line)
                </label>
                <textarea
                  rows={2}
                  value={constraints}
                  onChange={(e) => setConstraints(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', background: 'var(--bg-tertiary)', border: '1px solid var(--border-medium)', borderRadius: 'var(--radius-sm)', color: '#fff', fontSize: '0.8rem' }}
                />
              </div>
            </div>
          </div>

          {/* Section 3: Test Cases & AST Rules */}
          <div className="glass-panel" style={{ padding: '1.25rem', background: 'rgba(15, 23, 42, 0.8)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0, color: '#ffffff' }}>
                STEP 3: TEST CASES & CONCEPT RULES
              </h3>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => handleAddTestCase('sample')}
                  className="btn btn-secondary"
                  style={{ padding: '0.3rem 0.75rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}
                >
                  <Plus size={13} />
                  <span>Add Sample Case</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleAddTestCase('hidden')}
                  className="btn btn-secondary"
                  style={{ padding: '0.3rem 0.75rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.3rem', borderColor: 'rgba(99, 102, 241, 0.4)' }}
                >
                  <Plus size={13} />
                  <span>Add Hidden Case</span>
                </button>
              </div>
            </div>

            {/* Test Case Cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
              {testCases.map((tc, idx) => (
                <div key={idx} style={{
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid var(--border-medium)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '0.75rem',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontSize: '0.8rem', fontWeight: 700, color: tc.visibility === 'sample' ? 'var(--accent-cyan)' : '#a5b4fc' }}>
                        Test Case #{idx + 1} ({tc.visibility.toUpperCase()})
                      </span>
                      <select
                        value={tc.visibility}
                        onChange={(e) => handleUpdateTestCase(idx, 'visibility', e.target.value)}
                        style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', color: '#fff', fontSize: '0.72rem', borderRadius: '3px', padding: '0.15rem 0.35rem' }}
                      >
                        <option value="sample">Sample (Visible)</option>
                        <option value="hidden">Hidden (Graded)</option>
                      </select>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleRemoveTestCase(idx)}
                      style={{ background: 'transparent', border: 'none', color: '#fb7185', cursor: 'pointer', padding: '0.2rem' }}
                      title="Remove test case"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-subtle)', marginBottom: '0.2rem' }}>Input Data (STDIN):</div>
                      <textarea
                        rows={2}
                        value={tc.input_data}
                        onChange={(e) => handleUpdateTestCase(idx, 'input_data', e.target.value)}
                        placeholder="e.g. 5\n"
                        style={{ width: '100%', padding: '0.4rem', background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: '4px', color: '#fff', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}
                      />
                    </div>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-subtle)', marginBottom: '0.2rem' }}>Expected Output (STDOUT):</div>
                      <textarea
                        rows={2}
                        value={tc.expected_output}
                        onChange={(e) => handleUpdateTestCase(idx, 'expected_output', e.target.value)}
                        placeholder="e.g. 15"
                        style={{ width: '100%', padding: '0.4rem', background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: '4px', color: '#fff', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Concept Rules & Weights */}
            <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                  Enforced Static AST Concepts:
                </span>
                <button
                  type="button"
                  onClick={handleAddConceptRule}
                  className="btn btn-secondary"
                  style={{ padding: '0.25rem 0.6rem', fontSize: '0.72rem' }}
                >
                  <Plus size={12} /> Add Concept Rule
                </button>
              </div>

              {conceptRules.map((cr, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <select
                    value={cr.concept}
                    onChange={(e) => handleUpdateConceptRule(idx, 'concept', e.target.value)}
                    style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-medium)', borderRadius: '4px', color: '#fff', padding: '0.35rem 0.5rem', fontSize: '0.8rem' }}
                  >
                    <option value="loop">Loop (for/while)</option>
                    <option value="recursion">Recursion</option>
                    <option value="comprehensions">List/Dict Comprehension</option>
                    <option value="conditionals">Conditionals (if/else)</option>
                    <option value="exception_handling">Exception Handling (try/except)</option>
                  </select>

                  <input
                    type="text"
                    value={cr.description}
                    onChange={(e) => handleUpdateConceptRule(idx, 'description', e.target.value)}
                    placeholder="Pedagogical description"
                    style={{ flex: 1, background: 'var(--bg-tertiary)', border: '1px solid var(--border-medium)', borderRadius: '4px', color: '#fff', padding: '0.35rem 0.5rem', fontSize: '0.8rem' }}
                  />

                  <button
                    type="button"
                    onClick={() => handleRemoveConceptRule(idx)}
                    style={{ background: 'transparent', border: 'none', color: '#fb7185', cursor: 'pointer' }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}

              {/* Weights balance */}
              <div style={{ display: 'flex', gap: '1.5rem', marginTop: '1rem', background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: '4px' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-subtle)' }}>Functional Score Weight (%):</label>
                  <input
                    type="number"
                    value={functionalWeight}
                    onChange={(e) => setFunctionalWeight(e.target.value)}
                    style={{ width: '80px', marginLeft: '0.5rem', padding: '0.2rem 0.4rem', background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', color: '#fff', fontSize: '0.8rem' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-subtle)' }}>AST Concept Weight (%):</label>
                  <input
                    type="number"
                    value={conceptWeight}
                    onChange={(e) => setConceptWeight(e.target.value)}
                    style={{ width: '80px', marginLeft: '0.5rem', padding: '0.2rem 0.4rem', background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', color: '#fff', fontSize: '0.8rem' }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Section 4: Reference Solution & Sandbox Validation */}
          <div className="glass-panel" style={{ padding: '1.25rem', background: 'rgba(15, 23, 42, 0.8)' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.5rem', color: '#ffffff' }}>
              STEP 4: REFERENCE SOLUTION & PREVIEW VALIDATION
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
              Validate your teacher reference solution in the sandbox before publishing to verify that all test cases pass and conceptual AST rules are satisfied.
            </p>

            <textarea
              rows={6}
              value={referenceSolution}
              onChange={(e) => setReferenceSolution(e.target.value)}
              style={{ width: '100%', padding: '0.65rem', background: 'var(--bg-tertiary)', border: '1px solid var(--border-medium)', borderRadius: 'var(--radius-sm)', color: '#fff', fontSize: '0.85rem', fontFamily: 'var(--font-mono)', marginBottom: '1rem' }}
            />

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <button
                type="button"
                onClick={handleValidate}
                disabled={validating}
                className="btn btn-secondary"
                style={{ padding: '0.55rem 1.25rem', fontSize: '0.825rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
              >
                {validating ? <RefreshCw size={14} className="spin" /> : <Play size={14} fill="currentColor" />}
                <span>{validating ? 'Validating in Sandbox...' : 'Run Sandbox Validation'}</span>
              </button>

              <div style={{ display: 'flex', gap: '0.6rem' }}>
                <button
                  type="button"
                  onClick={() => handleSaveProblem('draft')}
                  disabled={publishing}
                  className="btn btn-secondary"
                  style={{ padding: '0.55rem 1rem', fontSize: '0.825rem' }}
                >
                  Save as Draft
                </button>
                <button
                  type="button"
                  onClick={() => handleSaveProblem('published')}
                  disabled={publishing}
                  className="btn btn-primary"
                  style={{ padding: '0.55rem 1.25rem', fontSize: '0.825rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                >
                  <Send size={14} />
                  <span>{publishing ? 'Publishing...' : 'Publish to Problemset'}</span>
                </button>
              </div>
            </div>

            {/* Validation Feedback */}
            {validationResult && (
              <div style={{
                marginTop: '1rem',
                padding: '0.85rem',
                borderRadius: 'var(--radius-sm)',
                background: validationResult.all_passed ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
                border: `1px solid ${validationResult.all_passed ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 700, fontSize: '0.85rem', color: validationResult.all_passed ? '#34d399' : '#fb7185', marginBottom: '0.4rem' }}>
                  {validationResult.all_passed ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                  <span>{validationResult.all_passed ? 'Validation Succeeded: All tests and AST concepts passed!' : 'Validation Failed: Issues detected.'}</span>
                </div>

                <div style={{ fontSize: '0.78rem', color: '#cbd5e1' }}>
                  Tests Passed: {validationResult.passed_tests} / {validationResult.total_tests}
                </div>

                {validationResult.concept_results && validationResult.concept_results.map((cr, idx) => (
                  <div key={idx} style={{ fontSize: '0.75rem', color: cr.passed ? '#34d399' : '#fb7185', marginTop: '0.2rem' }}>
                    {cr.passed ? '✓' : '✗'} {cr.message}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: MY AUTHORED PROBLEMS */}
      {activeTab === 'my_problems' && (
        <div className="glass-panel" style={{ padding: '1.5rem', background: 'rgba(15, 23, 42, 0.9)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>
              Your Authored Problem Catalog
            </h3>
            <button
              onClick={loadAuthoredProblems}
              className="btn btn-secondary"
              style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}
            >
              <RefreshCw size={13} className={loadingAuthored ? 'spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>

          {loadingAuthored ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
              <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.5rem', color: 'var(--accent-cyan)' }} />
              <div>Loading your authored questions...</div>
            </div>
          ) : authoredProblems.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
              <BookOpen size={32} style={{ margin: '0 auto 0.75rem', opacity: 0.4 }} />
              <p style={{ fontSize: '0.9rem' }}>You have not authored any problems yet.</p>
              <button onClick={() => setActiveTab('studio')} className="btn btn-primary" style={{ marginTop: '0.5rem', padding: '0.4rem 1rem', fontSize: '0.8rem' }}>
                Create Your First Problem
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {authoredProblems.map((prob) => (
                <div
                  key={prob.id}
                  style={{
                    background: 'rgba(30, 41, 59, 0.5)',
                    border: '1px solid var(--border-medium)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '1rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
                      <span className={`badge badge-${prob.difficulty}`}>{prob.difficulty}</span>
                      <span style={{
                        padding: '0.15rem 0.5rem',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        background: prob.status === 'published' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                        color: prob.status === 'published' ? '#34d399' : '#fbbf24',
                        border: `1px solid ${prob.status === 'published' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
                      }}>
                        {prob.status.toUpperCase()}
                      </span>
                      <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff' }}>
                        {prob.title}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', gap: '1rem' }}>
                      <span>Slug: <strong style={{ color: '#cbd5e1' }}>{prob.slug}</strong></span>
                      <span>Test Cases: <strong style={{ color: '#cbd5e1' }}>{prob.test_cases?.length || 0}</strong></span>
                      <span>Concepts: <strong style={{ color: 'var(--accent-cyan)' }}>{prob.concept_rules?.map((c) => c.concept).join(', ') || 'None'}</strong></span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Link
                      to={`/problems/${prob.slug || prob.id}`}
                      className="btn btn-secondary"
                      style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}
                    >
                      <Eye size={13} />
                      <span>Solve</span>
                    </Link>

                    {prob.status === 'draft' && (
                      <button
                        onClick={async () => {
                          try {
                            await api.publishAuthoredProblem(prob.id);
                            loadAuthoredProblems();
                          } catch (err) {
                            alert(err.message || 'Publishing failed.');
                          }
                        }}
                        className="btn btn-primary"
                        style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}
                      >
                        Publish
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
