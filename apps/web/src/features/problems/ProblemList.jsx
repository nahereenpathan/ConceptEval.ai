import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Search,
  Sparkles,
  RefreshCw,
  WifiOff,
  Lock,
  ServerCrash,
  RotateCcw,
  Bookmark,
  Clock,
  UploadCloud,
  Filter,
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
  X,
} from 'lucide-react';
import { api } from '../../api/client';

const COMPREHENSIVE_TOPICS = [
  { slug: 'arrays', name: 'Arrays' },
  { slug: 'strings', name: 'Strings' },
  { slug: 'hashing', name: 'Hashing & Maps' },
  { slug: 'sorting', name: 'Sorting' },
  { slug: 'searching', name: 'Searching' },
  { slug: 'recursion', name: 'Recursion' },
  { slug: 'loops', name: 'Loops & Iteration' },
  { slug: 'functions', name: 'Functions' },
  { slug: 'linked-lists', name: 'Linked Lists' },
  { slug: 'stacks', name: 'Stacks' },
  { slug: 'queues', name: 'Queues' },
  { slug: 'trees', name: 'Trees' },
  { slug: 'graphs', name: 'Graphs' },
  { slug: 'heaps', name: 'Heaps' },
  { slug: 'binary-search', name: 'Binary Search' },
  { slug: 'greedy', name: 'Greedy Algorithms' },
  { slug: 'backtracking', name: 'Backtracking' },
  { slug: 'dynamic-programming', name: 'Dynamic Programming' },
  { slug: 'math', name: 'Mathematics' },
  { slug: 'bit-manipulation', name: 'Bit Manipulation' },
  { slug: 'oop', name: 'OOP & Classes' },
  { slug: 'comprehensions', name: 'Comprehensions' },
  { slug: 'sql', name: 'SQL' },
];

export default function ProblemList() {
  // Core state
  const [problems, setProblems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters and pagination state
  const [activeTab, setActiveTab] = useState('all'); // 'all', 'saved', 'recent'
  const [selectedDifficulty, setSelectedDifficulty] = useState('all');
  const [selectedTopic, setSelectedTopic] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);
  const [difficultyCounts, setDifficultyCounts] = useState({ easy: 0, medium: 0, hard: 0, total: 0 });
  const [statusCounts, setStatusCounts] = useState({ not_started: 0, attempted: 0, solved: 0 });
  const [availableTopics, setAvailableTopics] = useState([]);

  // Import modal state
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importFormat, setImportFormat] = useState('json'); // 'json' | 'csv'
  const [importJsonText, setImportJsonText] = useState('');
  const [importCsvText, setImportCsvText] = useState('');
  const [importSourceName, setImportSourceName] = useState('Authorized Courseware Dataset');
  const [importLicenseType, setImportLicenseType] = useState('CC-BY-4.0');
  const [importProvenanceUrl, setImportProvenanceUrl] = useState('');
  const [importLoading, setImportLoading] = useState(false);
  const [importReport, setImportReport] = useState(null);
  const [importError, setImportError] = useState(null);

  const topicsList = useMemo(() => {
    if (availableTopics && availableTopics.length > 0) {
      return availableTopics;
    }
    return COMPREHENSIVE_TOPICS;
  }, [availableTopics]);


  // Bookmark notification toast
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Load available topics on mount
  useEffect(() => {
    loadTopics();
  }, []);

  // Reload problems when filters/tabs/pagination change
  useEffect(() => {
    loadProblems();
  }, [activeTab, selectedDifficulty, selectedTopic, selectedStatus, sortBy, sortOrder, currentPage, pageSize]);

  const loadTopics = async () => {
    try {
      const topicsData = await api.getTopics();
      if (Array.isArray(topicsData)) {
        setAvailableTopics(topicsData);
      }
    } catch {
      // Non-fatal if topics endpoint is warming up
    }
  };

  const loadProblems = async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === 'saved') {
        const data = await api.getMyBookmarks();
        const items = Array.isArray(data) ? data : (data.items || []);
        setProblems(items);
        setTotalRecords(items.length);
        setTotalPages(1);
      } else if (activeTab === 'recent') {
        const data = await api.getMyRecentProblems();
        const items = Array.isArray(data) ? data : (data.items || []);
        setProblems(items);
        setTotalRecords(items.length);
        setTotalPages(1);
      } else {
        const queryParams = {
          difficulty: selectedDifficulty === 'all' ? null : selectedDifficulty,
          topic: selectedTopic === 'all' ? null : selectedTopic,
          search: searchQuery.trim() || null,
          status: selectedStatus === 'all' ? null : selectedStatus,
          sort_by: sortBy,
          sort_order: sortOrder,
          page: currentPage,
          page_size: pageSize,
          paginate: true,
        };

        const res = await api.listProblems(queryParams);

        if (res && res.items && Array.isArray(res.items)) {
          setProblems(res.items);
          setTotalRecords(res.total || res.items.length);
          setTotalPages(res.total_pages || 1);
          if (res.difficulty_counts) setDifficultyCounts(res.difficulty_counts);
          if (res.status_counts) setStatusCounts(res.status_counts);
          if (res.available_topics && res.available_topics.length > 0) {
            // Merge with loaded topics
          }
        } else if (Array.isArray(res)) {
          setProblems(res);
          setTotalRecords(res.length);
          setTotalPages(1);
        } else {
          setProblems([]);
          setTotalRecords(0);
          setTotalPages(1);
        }
      }
    } catch (err) {
      if (err && err.code === 'REQUEST_ABORTED') {
        return;
      }
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setCurrentPage(1);
    loadProblems();
  };

  const handleBookmarkToggle = async (e, problemId) => {
    e.preventDefault();
    e.stopPropagation();

    // Optimistic UI update
    setProblems((prev) =>
      prev.map((p) => (p.id === problemId ? { ...p, is_saved: !p.is_saved } : p))
    );

    try {
      const res = await api.toggleBookmark(problemId);
      showToast(res.message || (res.is_saved ? 'Problem bookmarked!' : 'Bookmark removed.'));
    } catch (err) {
      // Revert optimistic update
      setProblems((prev) =>
        prev.map((p) => (p.id === problemId ? { ...p, is_saved: !p.is_saved } : p))
      );
      if (err.status === 401) {
        showToast('Please log in to save bookmarks.');
      } else {
        showToast('Could not update bookmark.');
      }
    }
  };

  const handleImportSubmit = async (e) => {
    e.preventDefault();
    setImportLoading(true);
    setImportError(null);
    setImportReport(null);

    try {
      let report;
      if (importFormat === 'csv') {
        if (!importCsvText.trim()) {
          throw new Error('Please enter or upload CSV dataset content.');
        }
        report = await api.importCsvDataset({
          source_name: importSourceName || 'Authorized Courseware Dataset',
          license_type: importLicenseType || 'CC-BY-4.0',
          provenance_url: importProvenanceUrl || null,
          csv_content: importCsvText,
        });
      } else {
        const parsedData = JSON.parse(importJsonText);
        const payload = {
          source_name: importSourceName || 'Authorized Courseware Dataset',
          license_type: importLicenseType || 'CC-BY-4.0',
          provenance_url: importProvenanceUrl || null,
          problems: Array.isArray(parsedData.problems) ? parsedData.problems : (Array.isArray(parsedData) ? parsedData : []),
        };

        if (!payload.problems || payload.problems.length === 0) {
          throw new Error('JSON dataset must contain a "problems" array with at least one item.');
        }

        report = await api.importProblemDataset(payload);
      }

      setImportReport(report);
      showToast(`Successfully imported ${report.imported_count} problems!`);
      // Reload problem list and topics
      loadProblems();
      loadTopics();
    } catch (err) {
      setImportError(err.message || 'Failed to process import.');
    } finally {
      setImportLoading(false);
    }
  };

  const handleFileUpload = (e, format) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result || '';
      if (format === 'json') {
        setImportJsonText(content);
      } else {
        setImportCsvText(content);
      }
    };
    reader.readAsText(file);
  };

  const loadSampleCsvTemplate = () => {
    const csvTemplate = `title,statement_markdown,difficulty,language,topics,expected_concepts,test_cases_json,rubric_rules_json
"Filter Odd Numbers with Loop","### Description\\nRead space-separated numbers and print only odd numbers in a list.\\n\\n### Concept Requirement\\nYou **must** use a loop.",easy,python,"loops,arrays","loop","[{\\"input_data\\":\\"1 2 3 4 5\\\\n\\",\\"expected_output\\":\\"[1, 3, 5]\\\\n\\",\\"visibility\\":\\"sample\\",\\"weight\\":1.0}]","[{\\"concept\\":\\"loop\\",\\"rule_id\\":\\"rule_loop\\",\\"accepted_constructs\\":[\\"For\\",\\"While\\"],\\"required\\":true,\\"min_occurrences\\":1}]"`;
    setImportCsvText(csvTemplate);
  };

  const loadSampleImportTemplate = () => {
    const template = {
      source_name: "Original Algorithm Workshop",
      license_type: "CC-BY-4.0",
      provenance_url: "https://example.edu/cs101-problems",
      problems: [
        {
          title: "Unique Elements Filter using Set",
          statement_markdown: "### Problem Description\nRead space-separated integers and print only the unique numbers in sorted order.\n\n### Concept Requirement\nYou **must** use a Python `set`.",
          difficulty: "easy",
          language: "python",
          topics: ["hashing", "arrays"],
          expected_concepts: ["set"],
          test_cases: [
            {
              input_data: "4 2 4 1 2\n",
              expected_output: "[1, 2, 4]\n",
              visibility: "sample",
              weight: 1.0
            }
          ],
          concept_rules: [
            {
              concept: "set",
              rule_id: "rule_require_set",
              accepted_constructs: ["Set", "Call"],
              required: true,
              min_occurrences: 1,
              description: "Must construct or use a set collection."
            }
          ]
        }
      ]
    };
    setImportJsonText(JSON.stringify(template, null, 2));
  };


  // Helper colors
  const getDifficultyColor = (diff) => {
    switch (diff?.toLowerCase()) {
      case 'easy':
        return { bg: 'rgba(16, 185, 129, 0.12)', text: '#34d399', border: 'rgba(16, 185, 129, 0.3)' };
      case 'medium':
        return { bg: 'rgba(245, 158, 11, 0.12)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.3)' };
      case 'hard':
        return { bg: 'rgba(244, 63, 94, 0.12)', text: '#fb7185', border: 'rgba(244, 63, 94, 0.3)' };
      default:
        return { bg: 'rgba(148, 163, 184, 0.12)', text: '#94a3b8', border: 'rgba(148, 163, 184, 0.2)' };
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'solved':
        return (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.35)',
            color: '#34d399',
            padding: '0.2rem 0.55rem',
            borderRadius: 'var(--radius-full)',
            fontSize: '0.72rem',
            fontWeight: 700,
          }}>
            <CheckCircle2 size={12} /> Solved
          </span>
        );
      case 'attempted':
        return (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            background: 'rgba(245, 158, 11, 0.15)',
            border: '1px solid rgba(245, 158, 11, 0.35)',
            color: '#fbbf24',
            padding: '0.2rem 0.55rem',
            borderRadius: 'var(--radius-full)',
            fontSize: '0.72rem',
            fontWeight: 700,
          }}>
            <Clock size={12} /> Attempted
          </span>
        );
      default:
        return (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            background: 'rgba(148, 163, 184, 0.08)',
            border: '1px solid rgba(148, 163, 184, 0.2)',
            color: '#94a3b8',
            padding: '0.2rem 0.55rem',
            borderRadius: 'var(--radius-full)',
            fontSize: '0.72rem',
            fontWeight: 500,
          }}>
            Not Started
          </span>
        );
    }
  };

  return (
    <div className="container" style={{ paddingBottom: '4rem' }}>
      {/* Toast Notification */}
      {toastMessage && (
        <div style={{
          position: 'fixed',
          bottom: '2rem',
          right: '2rem',
          background: 'rgba(30, 41, 59, 0.95)',
          border: '1px solid var(--accent-cyan)',
          borderRadius: 'var(--radius-md)',
          padding: '0.85rem 1.4rem',
          color: '#ffffff',
          boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
          zIndex: 9999,
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          fontSize: '0.9rem',
          fontWeight: 600,
          animation: 'fadeIn 0.2s ease-in-out',
        }}>
          <Sparkles size={16} color="var(--accent-cyan)" />
          {toastMessage}
        </div>
      )}

      {/* Hero Section */}
      <div style={{
        textAlign: 'center',
        padding: '3rem 1rem 2.5rem',
        maxWidth: '860px',
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
          <span>PHASE 1: PRODUCTION PROBLEM LIBRARY</span>
        </div>

        <h1 style={{
          fontFamily: 'var(--font-heading)',
          fontSize: '2.8rem',
          fontWeight: 800,
          letterSpacing: '-0.02em',
          lineHeight: 1.15,
          marginBottom: '1rem',
          background: 'linear-gradient(135deg, #ffffff 40%, #a5b4fc 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          Concept-Aware Coding Practice
        </h1>

        <p style={{ fontSize: '1.05rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
          Solve authentic challenges where output correctness is validated against isolated test cases{' '}
          <strong>and</strong> specific programming constructs are verified via{' '}
          <strong style={{ color: 'var(--accent-cyan)' }}>Abstract Syntax Tree (AST) analysis</strong>.
        </p>

        {/* Action Header: Import Button & View Navigation */}
        <div style={{
          marginTop: '1.75rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '1rem',
          flexWrap: 'wrap',
        }}>
          <div style={{
            display: 'inline-flex',
            background: 'rgba(30, 41, 59, 0.7)',
            borderRadius: 'var(--radius-full)',
            padding: '0.25rem',
            border: '1px solid var(--border-medium)',
          }}>
            <button
              onClick={() => { setActiveTab('all'); setCurrentPage(1); }}
              style={{
                background: activeTab === 'all' ? 'var(--accent-primary)' : 'transparent',
                color: activeTab === 'all' ? '#ffffff' : 'var(--text-muted)',
                border: 'none',
                borderRadius: 'var(--radius-full)',
                padding: '0.45rem 1.1rem',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
            >
              All Problems ({difficultyCounts.total || totalRecords})
            </button>
            <button
              onClick={() => { setActiveTab('saved'); setCurrentPage(1); }}
              style={{
                background: activeTab === 'saved' ? 'var(--accent-primary)' : 'transparent',
                color: activeTab === 'saved' ? '#ffffff' : 'var(--text-muted)',
                border: 'none',
                borderRadius: 'var(--radius-full)',
                padding: '0.45rem 1.1rem',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                transition: 'all 0.2s',
              }}
            >
              <Bookmark size={13} /> Saved / Bookmarks
            </button>
            <button
              onClick={() => { setActiveTab('recent'); setCurrentPage(1); }}
              style={{
                background: activeTab === 'recent' ? 'var(--accent-primary)' : 'transparent',
                color: activeTab === 'recent' ? '#ffffff' : 'var(--text-muted)',
                border: 'none',
                borderRadius: 'var(--radius-full)',
                padding: '0.45rem 1.1rem',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                transition: 'all 0.2s',
              }}
            >
              <Clock size={13} /> Recently Attempted
            </button>
          </div>

          <button
            onClick={() => setIsImportModalOpen(true)}
            className="btn btn-outline"
            style={{
              padding: '0.45rem 1rem',
              fontSize: '0.85rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              borderColor: 'rgba(99, 102, 241, 0.4)',
              color: '#c7d2fe',
            }}
          >
            <UploadCloud size={15} />
            <span>Import Dataset</span>
          </button>
        </div>
      </div>

      {/* Main Filter Toolbar */}
      <div className="glass-panel" style={{
        padding: '1.25rem',
        marginBottom: '1.5rem',
        borderRadius: 'var(--radius-md)',
      }}>
        {/* Search Bar & Sorting */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1rem',
        }}>
          <form onSubmit={handleSearchSubmit} style={{ flex: '1', minWidth: '280px', position: 'relative' }}>
            <Search
              size={17}
              style={{
                position: 'absolute',
                left: '0.85rem',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-muted)',
              }}
            />
            <input
              type="text"
              placeholder="Search by title, keywords, required concept, or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input"
              style={{
                paddingLeft: '2.5rem',
                paddingRight: searchQuery ? '2.5rem' : '1rem',
                width: '100%',
                background: 'rgba(15, 23, 42, 0.6)',
              }}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => { setSearchQuery(''); loadProblems(); }}
                style={{
                  position: 'absolute',
                  right: '0.75rem',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                }}
              >
                <X size={15} />
              </button>
            )}
          </form>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              <SlidersHorizontal size={14} />
              <span>Sort:</span>
              <select
                value={`${sortBy}-${sortOrder}`}
                onChange={(e) => {
                  const [b, o] = e.target.value.split('-');
                  setSortBy(b);
                  setSortOrder(o);
                }}
                className="input"
                style={{
                  padding: '0.35rem 0.75rem',
                  fontSize: '0.85rem',
                  background: 'rgba(15, 23, 42, 0.8)',
                  cursor: 'pointer',
                }}
              >
                <option value="created_at-desc">Newest First</option>
                <option value="created_at-asc">Oldest First</option>
                <option value="difficulty-asc">Difficulty (Easy → Hard)</option>
                <option value="difficulty-desc">Difficulty (Hard → Easy)</option>
                <option value="title-asc">Title (A → Z)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Difficulty and Progress Filters */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          paddingTop: '0.75rem',
          borderTop: '1px solid var(--border-light)',
        }}>
          {/* Difficulty Chips with Live Counts */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, marginRight: '0.25rem' }}>
              Difficulty:
            </span>
            {[
              { id: 'all', label: 'All', count: difficultyCounts.total },
              { id: 'easy', label: 'Easy', count: difficultyCounts.easy, color: '#34d399' },
              { id: 'medium', label: 'Medium', count: difficultyCounts.medium, color: '#fbbf24' },
              { id: 'hard', label: 'Hard', count: difficultyCounts.hard, color: '#fb7185' },
            ].map((diff) => (
              <button
                key={diff.id}
                onClick={() => { setSelectedDifficulty(diff.id); setCurrentPage(1); }}
                style={{
                  background: selectedDifficulty === diff.id ? 'var(--accent-primary)' : 'rgba(30, 41, 59, 0.6)',
                  color: selectedDifficulty === diff.id ? '#ffffff' : (diff.color || 'var(--text-muted)'),
                  border: selectedDifficulty === diff.id ? '1px solid var(--accent-primary)' : '1px solid var(--border-light)',
                  borderRadius: 'var(--radius-full)',
                  padding: '0.25rem 0.75rem',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  transition: 'all 0.15s ease',
                }}
              >
                <span>{diff.label}</span>
                {diff.count !== undefined && diff.count !== null && (
                  <span style={{
                    opacity: 0.8,
                    fontSize: '0.7rem',
                    background: selectedDifficulty === diff.id ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.25)',
                    padding: '0.1rem 0.35rem',
                    borderRadius: 'var(--radius-full)',
                  }}>
                    {diff.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Student Status Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, marginRight: '0.25rem' }}>
              Status:
            </span>
            {[
              { id: 'all', label: 'All Status' },
              { id: 'not_started', label: 'Not Started' },
              { id: 'attempted', label: 'Attempted' },
              { id: 'solved', label: 'Solved' },
            ].map((st) => (
              <button
                key={st.id}
                onClick={() => { setSelectedStatus(st.id); setCurrentPage(1); }}
                style={{
                  background: selectedStatus === st.id ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                  color: selectedStatus === st.id ? '#a5b4fc' : 'var(--text-muted)',
                  border: selectedStatus === st.id ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
                  borderRadius: 'var(--radius-sm)',
                  padding: '0.2rem 0.55rem',
                  fontSize: '0.78rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                {st.label}
              </button>
            ))}
          </div>
        </div>

        {/* Topic Filters Row */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          overflowX: 'auto',
          paddingTop: '0.75rem',
          marginTop: '0.5rem',
          borderTop: '1px solid var(--border-light)',
          whiteSpace: 'nowrap',
          scrollbarWidth: 'thin',
        }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600, flexShrink: 0 }}>
            Topic:
          </span>
          <button
            onClick={() => { setSelectedTopic('all'); setCurrentPage(1); }}
            style={{
              background: selectedTopic === 'all' ? 'rgba(6, 182, 212, 0.15)' : 'rgba(30, 41, 59, 0.4)',
              color: selectedTopic === 'all' ? 'var(--accent-cyan)' : 'var(--text-muted)',
              border: selectedTopic === 'all' ? '1px solid rgba(6, 182, 212, 0.4)' : '1px solid var(--border-light)',
              borderRadius: 'var(--radius-full)',
              padding: '0.2rem 0.65rem',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer',
              flexShrink: 0,
            }}
          >
            All Topics
          </button>
          {topicsList.map((t) => (
            <button
              key={t.slug}
              onClick={() => { setSelectedTopic(t.slug); setCurrentPage(1); }}
              style={{
                background: selectedTopic === t.slug ? 'rgba(6, 182, 212, 0.15)' : 'rgba(30, 41, 59, 0.4)',
                color: selectedTopic === t.slug ? 'var(--accent-cyan)' : 'var(--text-muted)',
                border: selectedTopic === t.slug ? '1px solid rgba(6, 182, 212, 0.4)' : '1px solid var(--border-light)',
                borderRadius: 'var(--radius-full)',
                padding: '0.2rem 0.65rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                flexShrink: 0,
              }}
            >
              {t.name}
            </button>
          ))}
        </div>
      </div>

      {/* Results Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '1rem',
        fontSize: '0.85rem',
        color: 'var(--text-muted)',
      }}>
        <span>
          Showing <strong>{problems.length}</strong> of <strong>{totalRecords}</strong> {totalRecords === 1 ? 'problem' : 'problems'}
          {selectedDifficulty !== 'all' && ` • Difficulty: ${selectedDifficulty}`}
          {selectedTopic !== 'all' && ` • Topic: ${selectedTopic}`}
          {searchQuery && ` • Matching: "${searchQuery}"`}
        </span>

        {/* Page size picker */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span>Per page:</span>
          {[10, 20, 50].map((sz) => (
            <button
              key={sz}
              onClick={() => { setPageSize(sz); setCurrentPage(1); }}
              style={{
                background: pageSize === sz ? 'var(--accent-primary)' : 'rgba(30, 41, 59, 0.5)',
                color: pageSize === sz ? '#ffffff' : 'var(--text-muted)',
                border: 'none',
                borderRadius: '4px',
                padding: '0.15rem 0.45rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {sz}
            </button>
          ))}
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="glass-panel" style={{
          textAlign: 'center',
          padding: '4rem 2rem',
          borderRadius: 'var(--radius-md)',
        }}>
          <RefreshCw size={28} className="spin" color="var(--accent-cyan)" style={{ marginBottom: '1rem' }} />
          <h3 style={{ fontSize: '1.1rem', marginBottom: '0.4rem' }}>Loading Problem Library...</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Fetching verified challenges and concept rubrics from FastAPI backend.
          </p>
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div className="glass-panel" style={{
          padding: '2.5rem',
          textAlign: 'center',
          border: '1px solid rgba(244, 63, 94, 0.35)',
          borderRadius: 'var(--radius-md)',
          background: 'rgba(244, 63, 94, 0.04)',
        }}>
          {error.code === 'NETWORK_ERROR' ? (
            <WifiOff size={36} color="var(--accent-rose)" style={{ marginBottom: '1rem' }} />
          ) : error.code === 'VALIDATION_ERROR' ? (
            <AlertTriangle size={36} color="#fbbf24" style={{ marginBottom: '1rem' }} />
          ) : error.code === 'AUTHENTICATION_REQUIRED' || error.code === 'ACCESS_DENIED' ? (
            <Lock size={36} color="#fbbf24" style={{ marginBottom: '1rem' }} />
          ) : (
            <ServerCrash size={36} color="var(--accent-rose)" style={{ marginBottom: '1rem' }} />
          )}

          <h3 style={{ fontSize: '1.2rem', marginBottom: '0.5rem', color: error.code === 'VALIDATION_ERROR' ? '#fbbf24' : '#fca5a5' }}>
            {error.code === 'NETWORK_ERROR'
              ? 'Backend Connection Error'
              : error.code === 'VALIDATION_ERROR'
              ? 'Validation Error (422)'
              : error.status >= 500
              ? `FastAPI Server Error (${error.status})`
              : 'Unable to Load Problems'}
          </h3>
          <p style={{ color: 'var(--text-muted)', maxWidth: '560px', margin: '0 auto 1.5rem', fontSize: '0.9rem', lineHeight: '1.5' }}>
            {error.message || 'An error occurred while communicating with the problem library service.'}
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem' }}>
            <button
              onClick={() => {
                setError(null);
                loadProblems();
              }}
              className="btn btn-primary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <RotateCcw size={15} /> Retry Request
            </button>
            {error.code === 'NETWORK_ERROR' && (
              <button
                onClick={() => window.open('http://127.0.0.1:8000/docs', '_blank')}
                className="btn btn-outline"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}
              >
                Open Swagger Docs
              </button>
            )}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && problems.length === 0 && (
        <div className="glass-panel" style={{
          textAlign: 'center',
          padding: '4rem 2rem',
          borderRadius: 'var(--radius-md)',
        }}>
          <Filter size={32} color="var(--text-muted)" style={{ marginBottom: '1rem', opacity: 0.6 }} />
          <h3 style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>No Problems Match Your Criteria</h3>
          <p style={{ color: 'var(--text-muted)', maxWidth: '480px', margin: '0 auto 1.5rem', fontSize: '0.9rem' }}>
            {searchQuery
              ? `No problems found matching "${searchQuery}". Try adjusting your keywords or clearing difficulty filters.`
              : 'No problems currently match the selected difficulty and topic filters.'}
          </p>
          <button
            onClick={() => {
              setSelectedDifficulty('all');
              setSelectedTopic('all');
              setSelectedStatus('all');
              setSearchQuery('');
              setActiveTab('all');
              setCurrentPage(1);
            }}
            className="btn btn-outline"
          >
            Clear All Filters
          </button>
        </div>
      )}

      {/* Problem Cards List */}
      {!loading && !error && problems.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {problems.map((problem) => {
            const diffStyle = getDifficultyColor(problem.difficulty);

            return (
              <div
                key={problem.id}
                className="glass-panel card-hover"
                style={{
                  padding: '1.4rem 1.6rem',
                  borderRadius: 'var(--radius-md)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '1.5rem',
                  position: 'relative',
                  border: '1px solid var(--border-medium)',
                  background: 'rgba(15, 23, 42, 0.75)',
                }}
              >
                {/* Left side: Problem info */}
                <div style={{ flex: '1', minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
                    {/* Difficulty Badge */}
                    <span style={{
                      background: diffStyle.bg,
                      color: diffStyle.text,
                      border: `1px solid ${diffStyle.border}`,
                      padding: '0.2rem 0.6rem',
                      borderRadius: 'var(--radius-full)',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                    }}>
                      {problem.difficulty}
                    </span>

                    {/* Student Progress Badge */}
                    {getStatusBadge(problem.student_status)}

                    {/* Topic Tags */}
                    {problem.topics && problem.topics.map((t, idx) => (
                      <span
                        key={`${problem.id}-topic-${t}-${idx}`}
                        style={{
                          background: 'rgba(51, 65, 85, 0.4)',
                          color: '#cbd5e1',
                          padding: '0.15rem 0.5rem',
                          borderRadius: '4px',
                          fontSize: '0.72rem',
                          border: '1px solid rgba(148, 163, 184, 0.15)',
                        }}
                      >
                        {t}
                      </span>
                    ))}
                  </div>

                  {/* Title & Bookmark Button */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <h3 style={{
                      fontFamily: 'var(--font-heading)',
                      fontSize: '1.18rem',
                      fontWeight: 700,
                      color: '#ffffff',
                      margin: 0,
                    }}>
                      <Link
                        to={`/problems/${problem.slug || problem.id}`}
                        style={{ color: 'inherit', textDecoration: 'none' }}
                        className="hover-cyan"
                      >
                        {problem.title}
                      </Link>
                    </h3>

                    {/* Interactive Bookmark Button */}
                    <button
                      onClick={(e) => handleBookmarkToggle(e, problem.id)}
                      title={problem.is_saved ? 'Remove Bookmark' : 'Save Problem'}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        padding: '0.25rem',
                        color: problem.is_saved ? '#fbbf24' : 'var(--text-muted)',
                        display: 'flex',
                        alignItems: 'center',
                        transition: 'transform 0.15s ease',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.2)')}
                      onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1.0)')}
                    >
                      <Bookmark size={17} fill={problem.is_saved ? '#fbbf24' : 'none'} />
                    </button>
                  </div>

                  {/* Statement preview snippet */}
                  {problem.statement_preview && (
                    <p style={{
                      color: 'var(--text-muted)',
                      fontSize: '0.85rem',
                      lineHeight: 1.5,
                      margin: '0.5rem 0 0.6rem',
                    }}>
                      {problem.statement_preview}
                    </p>
                  )}

                  {/* Concept-Aware Pill Breakdown */}
                  {problem.expected_concepts && problem.expected_concepts.length > 0 && (
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.4rem',
                      marginTop: '0.5rem',
                      flexWrap: 'wrap',
                    }}>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                        Required Concepts:
                      </span>
                      {problem.expected_concepts.map((concept, cIdx) => (
                        <span
                          key={`${problem.id}-concept-${concept}-${cIdx}`}
                          style={{
                            background: 'rgba(6, 182, 212, 0.1)',
                            border: '1px solid rgba(6, 182, 212, 0.3)',
                            color: 'var(--accent-cyan)',
                            padding: '0.15rem 0.5rem',
                            borderRadius: '4px',
                            fontSize: '0.72rem',
                            fontWeight: 600,
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          ⚡ {concept}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Right side: Action Button */}
                <div style={{ flexShrink: 0 }}>
                  <Link
                    to={`/problems/${problem.slug || problem.id}`}
                    className="btn btn-primary"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.45rem',
                      padding: '0.6rem 1.25rem',
                      fontSize: '0.9rem',
                      fontWeight: 600,
                      textDecoration: 'none',
                    }}
                  >
                    <span>Practice</span>
                    <ArrowRight size={15} />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {!loading && !error && totalPages > 1 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.5rem',
          marginTop: '2.5rem',
        }}>
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="btn btn-outline"
            style={{
              padding: '0.45rem 0.85rem',
              opacity: currentPage === 1 ? 0.4 : 1,
              cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
            }}
          >
            <ChevronLeft size={16} /> Prev
          </button>

          {Array.from({ length: totalPages }, (_, i) => i + 1).map((pageNum) => (
            <button
              key={pageNum}
              onClick={() => setCurrentPage(pageNum)}
              style={{
                background: currentPage === pageNum ? 'var(--accent-primary)' : 'rgba(30, 41, 59, 0.6)',
                color: currentPage === pageNum ? '#ffffff' : 'var(--text-muted)',
                border: currentPage === pageNum ? '1px solid var(--accent-primary)' : '1px solid var(--border-light)',
                borderRadius: '6px',
                width: '36px',
                height: '36px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {pageNum}
            </button>
          ))}

          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="btn btn-outline"
            style={{
              padding: '0.45rem 0.85rem',
              opacity: currentPage === totalPages ? 0.4 : 1,
              cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
            }}
          >
            Next <ChevronRight size={16} />
          </button>
        </div>
      )}

      {/* Authorized Dataset Import Modal */}
      {isImportModalOpen && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 99999,
          padding: '1rem',
        }}>
          <div className="glass-panel" style={{
            maxWidth: '680px',
            width: '100%',
            maxHeight: '90vh',
            overflowY: 'auto',
            borderRadius: 'var(--radius-lg)',
            padding: '2rem',
            position: 'relative',
            background: 'rgba(15, 23, 42, 0.95)',
            border: '1px solid var(--border-medium)',
          }}>
            <button
              onClick={() => setIsImportModalOpen(false)}
              style={{
                position: 'absolute',
                top: '1.25rem',
                right: '1.25rem',
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
              }}
            >
              <X size={20} />
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
              <div style={{
                background: 'rgba(99, 102, 241, 0.15)',
                padding: '0.6rem',
                borderRadius: '8px',
                border: '1px solid rgba(99, 102, 241, 0.3)',
              }}>
                <UploadCloud size={24} color="#a5b4fc" />
              </div>
              <div>
                <h2 style={{ fontSize: '1.4rem', margin: 0, fontFamily: 'var(--font-heading)' }}>
                  Import Authorized Problem Dataset
                </h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', margin: 0 }}>
                  Upload original, institution-owned, or open-licensed problem sets with schema validation.
                </p>
              </div>
            </div>

            {/* License Policy Notice */}
            <div style={{
              background: 'rgba(51, 65, 85, 0.3)',
              border: '1px solid var(--border-light)',
              borderRadius: 'var(--radius-sm)',
              padding: '0.75rem 1rem',
              fontSize: '0.78rem',
              color: '#cbd5e1',
              marginBottom: '1.25rem',
              lineHeight: 1.5,
            }}>
              ⚖️ <strong>Compliance Policy:</strong> All imported problems must be original courseware or authorized under open licenses (e.g. CC-BY-4.0). Do not import copyrighted statements or proprietary platform tests.
            </div>

            <form onSubmit={handleImportSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                    Dataset / Source Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={importSourceName}
                    onChange={(e) => setImportSourceName(e.target.value)}
                    className="input"
                    placeholder="e.g. Department CS101 Lab Catalog"
                    style={{ width: '100%' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                    License Type *
                  </label>
                  <select
                    value={importLicenseType}
                    onChange={(e) => setImportLicenseType(e.target.value)}
                    className="input"
                    style={{ width: '100%' }}
                  >
                    <option value="CC-BY-4.0">Creative Commons CC-BY-4.0</option>
                    <option value="MIT">MIT License</option>
                    <option value="Institution-Courseware">Institution Internal Courseware</option>
                    <option value="Educational-Fair-Use">Educational Fair Use</option>
                  </select>
                </div>
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                  Provenance URL (Optional)
                </label>
                <input
                  type="url"
                  value={importProvenanceUrl}
                  onChange={(e) => setImportProvenanceUrl(e.target.value)}
                  className="input"
                  placeholder="https://github.com/my-org/course-problems"
                  style={{ width: '100%' }}
                />
              </div>

              {/* Format Switcher: JSON vs CSV */}
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => setImportFormat('json')}
                  style={{
                    background: importFormat === 'json' ? 'var(--accent-primary)' : 'rgba(30, 41, 59, 0.6)',
                    color: importFormat === 'json' ? '#ffffff' : 'var(--text-muted)',
                    border: 'none',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.35rem 0.85rem',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  JSON Format
                </button>
                <button
                  type="button"
                  onClick={() => setImportFormat('csv')}
                  style={{
                    background: importFormat === 'csv' ? 'var(--accent-primary)' : 'rgba(30, 41, 59, 0.6)',
                    color: importFormat === 'csv' ? '#ffffff' : 'var(--text-muted)',
                    border: 'none',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.35rem 0.85rem',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  CSV Format
                </button>
              </div>

              {importFormat === 'json' ? (
                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                    <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>
                      JSON Problem Dataset *
                    </label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <label style={{ cursor: 'pointer', color: 'var(--accent-cyan)', fontSize: '0.75rem', fontWeight: 600 }}>
                        Upload .json file
                        <input
                          type="file"
                          accept=".json,application/json"
                          style={{ display: 'none' }}
                          onChange={(e) => handleFileUpload(e, 'json')}
                        />
                      </label>
                      <button
                        type="button"
                        onClick={loadSampleImportTemplate}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: 'var(--accent-cyan)',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        Load Sample Template
                      </button>
                    </div>
                  </div>
                  <textarea
                    required
                    rows={8}
                    value={importJsonText}
                    onChange={(e) => setImportJsonText(e.target.value)}
                    className="input"
                    placeholder='Paste JSON schema containing { "problems": [ ... ] }'
                    style={{
                      width: '100%',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.8rem',
                      lineHeight: 1.4,
                    }}
                  />
                </div>
              ) : (
                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                    <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>
                      CSV Problem Dataset *
                    </label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <label style={{ cursor: 'pointer', color: 'var(--accent-cyan)', fontSize: '0.75rem', fontWeight: 600 }}>
                        Upload .csv file
                        <input
                          type="file"
                          accept=".csv,text/csv"
                          style={{ display: 'none' }}
                          onChange={(e) => handleFileUpload(e, 'csv')}
                        />
                      </label>
                      <button
                        type="button"
                        onClick={loadSampleCsvTemplate}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: 'var(--accent-cyan)',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        Load Sample CSV
                      </button>
                    </div>
                  </div>
                  <textarea
                    required
                    rows={8}
                    value={importCsvText}
                    onChange={(e) => setImportCsvText(e.target.value)}
                    className="input"
                    placeholder="title,statement_markdown,difficulty,language,topics,expected_concepts,test_cases_json,rubric_rules_json..."
                    style={{
                      width: '100%',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.8rem',
                      lineHeight: 1.4,
                    }}
                  />
                </div>
              )}

              {/* Import Error Banner */}
              {importError && (
                <div style={{
                  background: 'rgba(244, 63, 94, 0.1)',
                  border: '1px solid rgba(244, 63, 94, 0.3)',
                  color: '#fb7185',
                  padding: '0.75rem',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.82rem',
                  marginBottom: '1rem',
                }}>
                  {importError}
                </div>
              )}

              {/* Import Report Banner */}
              {importReport && (
                <div style={{
                  background: 'rgba(16, 185, 129, 0.1)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  color: '#34d399',
                  padding: '1rem',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.85rem',
                  marginBottom: '1rem',
                }}>
                  <div style={{ fontWeight: 700, marginBottom: '0.25rem' }}>
                    ✅ Import Complete!
                  </div>
                  <div>• Total Processed: <strong>{importReport.total_processed}</strong></div>
                  <div>• Successfully Imported: <strong>{importReport.imported_count}</strong></div>
                  <div>• Skipped Duplicates: <strong>{importReport.skipped_duplicates}</strong></div>
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.75rem' }}>
                <button
                  type="button"
                  onClick={() => setIsImportModalOpen(false)}
                  className="btn btn-outline"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={importLoading || (importFormat === 'json' ? !importJsonText.trim() : !importCsvText.trim())}
                  className="btn btn-primary"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    opacity: importLoading ? 0.7 : 1,
                  }}
                >
                  {importLoading ? <RefreshCw size={15} className="spin" /> : <UploadCloud size={15} />}
                  <span>{importLoading ? 'Validating & Importing...' : 'Execute Import'}</span>
                </button>
              </div>

            </form>
          </div>
        </div>
      )}
    </div>
  );
}
