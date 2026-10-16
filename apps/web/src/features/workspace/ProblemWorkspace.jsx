import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import confetti from 'canvas-confetti';
import {
  ArrowLeft,
  Play,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Sparkles,
  FileCode2,
  RefreshCw,
  Bookmark,
  History,
  FileText,
  Terminal,
  Send,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Maximize2,
  Layers,
  Cpu,
} from 'lucide-react';
import { api } from '../../api/client';
import IntelligentFeedbackCard from './IntelligentFeedbackCard';
import ProgressiveHintsCard from './ProgressiveHintsCard';
import LoadSolutionConfirmModal from './LoadSolutionConfirmModal';
import VerifiedSolutionModal from './VerifiedSolutionModal';

export default function ProblemWorkspace({ currentUser, onOpenAuth }) {
  const { id } = useParams();
  const navigate = useNavigate();

  // Problem data
  const [problem, setProblem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [problemList, setProblemList] = useState([]);

  // Code editor & multi-language state
  const [code, setCode] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState('python');
  const [codeDrafts, setCodeDrafts] = useState({});
  const [languages, setLanguages] = useState([
    { id: 'python', name: 'Python 3.12 (Sandbox)', available: true, extension: '.py', version: '3.12' },
    { id: 'java', name: 'Java (JDK 25)', available: true, extension: '.java', version: '25' },
    { id: 'cpp', name: 'C++ (g++ 6.3.0)', available: true, extension: '.cpp', version: '6.3.0' },
  ]);

  // Execution states
  const [runningCode, setRunningCode] = useState(false);
  const [runResult, setRunResult] = useState(null);
  const [evaluating, setEvaluating] = useState(false);
  const [evalResult, setEvalResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // Verified Solution & Learning System
  const [showSolutionModal, setShowSolutionModal] = useState(false);
  const [solutionLoading, setSolutionLoading] = useState(false);
  const [solutionData, setSolutionData] = useState(null);
  const [solutionError, setSolutionError] = useState(null);
  const [showLoadConfirmModal, setShowLoadConfirmModal] = useState(false);

  // Progressive Hints State
  const [hints, setHints] = useState(null);
  const [revealedHintLevel, setRevealedHintLevel] = useState(0);
  const [loadingHints, setLoadingHints] = useState(false);

  // Bottom Console states
  const [activeConsoleTab, setActiveConsoleTab] = useState('testcase'); // 'testcase' | 'test_result' | 'submission'
  const [selectedCaseIdx, setSelectedCaseIdx] = useState(0);
  const [customInput, setCustomInput] = useState('');
  const [isConsoleOpen, setIsConsoleOpen] = useState(true);
  const [consoleHeight, setConsoleHeight] = useState(250);

  // Layout & UI states
  const [viewMode, setViewMode] = useState('split'); // 'split' | 'code_max' | 'desc_max'
  const [isSaved, setIsSaved] = useState(false);
  const [activeLeftTab, setActiveLeftTab] = useState('statement'); // 'statement' | 'history'
  const [submissionHistory, setSubmissionHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Fetch live compiler availability from backend
  useEffect(() => {
    let isMounted = true;
    api.getLanguages()
      .then((res) => {
        if (!isMounted) return;
        if (res?.languages && Array.isArray(res.languages) && res.languages.length > 0) {
          setLanguages(res.languages);
        }
      })
      .catch((err) => {
        console.warn('Languages fetch error:', err);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Safely load problem catalog for Prev/Next navigation
  useEffect(() => {
    let isMounted = true;
    api.listProblems({ paginate: false })
      .then((res) => {
        if (!isMounted) return;
        const items = res?.items || (Array.isArray(res) ? res : []);
        setProblemList(items);
      })
      .catch((err) => {
        console.warn('Navigation list fetch non-fatal error:', err);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    loadProblem();
  }, [id]);

  const getStarterCode = (lang, data) => {
    if (lang === 'java') {
      if (data?.slug?.includes('factorial')) {
        return 'import java.util.Scanner;\n\npublic class Solution {\n    // TODO: Implement recursive factorial function\n    public static long factorial(int n) {\n        // Your code here\n        return 1;\n    }\n\n    public static void main(String[] args) {\n        Scanner scanner = new Scanner(System.in);\n        if (scanner.hasNextInt()) {\n            int n = scanner.nextInt();\n            System.out.println(factorial(n));\n        }\n    }\n}\n';
      } else if (data?.slug?.includes('stairs')) {
        return 'import java.util.Scanner;\n\npublic class Solution {\n    // Required concept: loop\n    public static int climbStairs(int n) {\n        // Calculate ways to climb stairs\n        return 0;\n    }\n\n    public static void main(String[] args) {\n        Scanner scanner = new Scanner(System.in);\n        while (scanner.hasNextInt()) {\n            System.out.println(climbStairs(scanner.nextInt()));\n        }\n    }\n}\n';
      } else {
        return 'import java.util.Scanner;\n\npublic class Solution {\n    public static void main(String[] args) {\n        Scanner scanner = new Scanner(System.in);\n        // Write your solution here\n        while (scanner.hasNextLine()) {\n            String line = scanner.nextLine().trim();\n            if (line.isEmpty()) continue;\n            // Process input\n        }\n    }\n}\n';
      }
    } else if (lang === 'cpp') {
      if (data?.slug?.includes('factorial')) {
        return '#include <iostream>\n\nusing namespace std;\n\n// TODO: Implement recursive factorial function\nlong long factorial(int n) {\n    // Your code here\n    return 1;\n}\n\nint main() {\n    int n;\n    if (cin >> n) {\n        cout << factorial(n) << endl;\n    }\n    return 0;\n}\n';
      } else if (data?.slug?.includes('stairs')) {
        return '#include <iostream>\n\nusing namespace std;\n\n// Required concept: loop\nint climbStairs(int n) {\n    // Calculate ways to climb stairs\n    return 0;\n}\n\nint main() {\n    int n;\n    while (cin >> n) {\n        cout << climbStairs(n) << "\\n";\n    }\n    return 0;\n}\n';
      } else {
        return '#include <iostream>\n#include <string>\n#include <vector>\n\nusing namespace std;\n\nint main() {\n    ios_base::sync_with_stdio(false);\n    cin.tie(NULL);\n    // Write your solution here\n    string line;\n    while (getline(cin, line)) {\n        if (line.empty()) continue;\n        // Process line\n    }\n    return 0;\n}\n';
      }
    } else {
      // Python
      if (data?.starter_code) {
        return data.starter_code;
      } else if (data?.slug?.includes('factorial')) {
        return '# Write your recursive factorial function here\n\ndef factorial(n):\n    # TODO: Implement base case and recursive step\n    pass\n\nif __name__ == "__main__":\n    n = int(input().strip())\n    print(factorial(n))\n';
      } else if (data?.slug?.includes('stairs')) {
        return 'import sys\n\ndef climb_stairs(n: int) -> int:\n    # Required concept: loop\n    # Calculate number of distinct ways to climb n stairs\n    pass\n\nfor line in sys.stdin:\n    if line.strip():\n        print(climb_stairs(int(line.strip())))\n';
      } else {
        return '# Write your solution here\nimport sys\n\nfor line in sys.stdin:\n    print("Hello World")\n';
      }
    }
  };

  const loadProblem = async () => {
    if (!id) return;
    setLoading(true);
    setRunResult(null);
    setEvalResult(null);
    setErrorMsg(null);

    try {
      const data = await api.getProblem(id);
      if (!data || (!data.id && !data.title)) {
        throw new Error(`Problem with identifier "${id}" could not be found.`);
      }

      setProblem(data);
      setIsSaved(Boolean(data.is_saved));

      // If backend returns supported_languages for this problem, update available languages
      if (Array.isArray(data.supported_languages) && data.supported_languages.length > 0) {
        setLanguages(data.supported_languages);
      }

      // Initialize code for currently selected language
      setCode(getStarterCode(selectedLanguage, data));

      // Initialize custom input with first sample input
      if (Array.isArray(data.sample_test_cases) && data.sample_test_cases.length > 0) {
        setCustomInput(data.sample_test_cases[0]?.input_data || '');
      } else {
        setCustomInput('');
      }

      // Load submission history for logged in user
      if (currentUser && data.id) {
        loadSubmissionHistory(data.id);
      }
    } catch (err) {
      console.error('Failed to load problem:', err);
      setErrorMsg(err.message || `Failed to load problem "${id}".`);
    } finally {
      setLoading(false);
    }
  };

  const loadSubmissionHistory = async (problemId = null) => {
    const pId = problemId || problem?.id;
    if (!pId || !currentUser) return;
    setLoadingHistory(true);
    try {
      const history = await api.getProblemSubmissions(pId);
      setSubmissionHistory(Array.isArray(history) ? history : []);
    } catch {
      // Non-fatal
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleBookmarkToggle = async () => {
    if (!currentUser) {
      onOpenAuth();
      return;
    }
    const prev = isSaved;
    setIsSaved(!prev);
    try {
      const res = await api.toggleBookmark(problem.id);
      setIsSaved(Boolean(res.is_saved));
    } catch {
      setIsSaved(prev);
    }
  };

  const handleLanguageChange = (newLang) => {
    if (newLang === selectedLanguage) return;
    // Save draft for current language
    setCodeDrafts((prev) => ({ ...prev, [selectedLanguage]: code }));
    setSelectedLanguage(newLang);
    // Load draft or template for selected language
    if (codeDrafts[newLang]) {
      setCode(codeDrafts[newLang]);
    } else {
      setCode(getStarterCode(newLang, problem));
    }
  };

  const handleQuickTemplate = (templateType) => {
    if (selectedLanguage === 'java') {
      if (problem?.slug?.includes('factorial')) {
        if (templateType === 'compliant') {
          setCode('import java.util.Scanner;\n\npublic class Solution {\n    // Compliant: Recursive implementation\n    public static long factorial(int n) {\n        if (n <= 1) return 1;\n        return n * factorial(n - 1);\n    }\n\n    public static void main(String[] args) {\n        Scanner scanner = new Scanner(System.in);\n        if (scanner.hasNextInt()) {\n            int n = scanner.nextInt();\n            System.out.println(factorial(n));\n        }\n    }\n}\n');
        } else if (templateType === 'violation') {
          setCode('import java.util.Scanner;\n\npublic class Solution {\n    // Violation: Uses iterative loop instead of required recursion\n    public static long factorial(int n) {\n        long ans = 1;\n        for (int i = 1; i <= n; i++) {\n            ans *= i;\n        }\n        return ans;\n    }\n\n    public static void main(String[] args) {\n        Scanner scanner = new Scanner(System.in);\n        if (scanner.hasNextInt()) {\n            int n = scanner.nextInt();\n            System.out.println(factorial(n));\n        }\n    }\n}\n');
        } else if (templateType === 'syntax_err') {
          setCode('public class Solution {\n    public static void main(String[] args) {\n        System.out.println("Missing semicolon")\n    }\n}\n');
        }
      } else if (problem?.slug?.includes('stairs')) {
        if (templateType === 'compliant') {
          setCode('import java.util.Scanner;\n\npublic class Solution {\n    // Compliant: Implements required loop\n    public static int climbStairs(int n) {\n        if (n <= 2) return n;\n        int a = 1, b = 2;\n        for (int i = 3; i <= n; i++) {\n            int temp = a + b;\n            a = b;\n            b = temp;\n        }\n        return b;\n    }\n\n    public static void main(String[] args) {\n        Scanner scanner = new Scanner(System.in);\n        while (scanner.hasNextInt()) {\n            System.out.println(climbStairs(scanner.nextInt()));\n        }\n    }\n}\n');
        } else if (templateType === 'violation') {
          setCode('import java.util.Scanner;\n\npublic class Solution {\n    // Violation: Uses hardcoded lookup table without required loop\n    public static void main(String[] args) {\n        int[] table = {0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89};\n        Scanner scanner = new Scanner(System.in);\n        while (scanner.hasNextInt()) {\n            int n = scanner.nextInt();\n            System.out.println(n < table.length ? table[n] : 1);\n        }\n    }\n}\n');
        }
      } else {
        if (templateType === 'compliant') {
          setCode('import java.util.Scanner;\n\npublic class Solution {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        while (sc.hasNextLine()) {\n            String line = sc.nextLine().trim();\n            if (line.isEmpty()) continue;\n            String[] parts = line.split("\\\\s+");\n            StringBuilder sb = new StringBuilder();\n            for (int i = 0; i < parts.length; i++) {\n                int val = Integer.parseInt(parts[i]) * 2;\n                if (i > 0) sb.append(" ");\n                sb.append(val);\n            }\n            System.out.println(sb.toString());\n        }\n    }\n}\n');
        } else {
          setCode('import java.util.Scanner;\n\npublic class Solution {\n    public static void main(String[] args) {\n        System.out.println("2 4 6");\n    }\n}\n');
        }
      }
    } else if (selectedLanguage === 'cpp') {
      if (problem?.slug?.includes('factorial')) {
        if (templateType === 'compliant') {
          setCode('#include <iostream>\n\nusing namespace std;\n\n// Compliant: Recursive implementation\nlong long factorial(int n) {\n    if (n <= 1) return 1;\n    return n * factorial(n - 1);\n}\n\nint main() {\n    int n;\n    if (cin >> n) {\n        cout << factorial(n) << endl;\n    }\n    return 0;\n}\n');
        } else if (templateType === 'violation') {
          setCode('#include <iostream>\n\nusing namespace std;\n\n// Violation: Uses iterative loop instead of required recursion\nlong long factorial(int n) {\n    long long ans = 1;\n    for (int i = 1; i <= n; ++i) {\n        ans *= i;\n    }\n    return ans;\n}\n\nint main() {\n    int n;\n    if (cin >> n) {\n        cout << factorial(n) << endl;\n    }\n    return 0;\n}\n');
        } else if (templateType === 'syntax_err') {
          setCode('#include <iostream>\nint main() {\n    std::cout << "Missing semicolon"\n    return 0;\n}\n');
        }
      } else if (problem?.slug?.includes('stairs')) {
        if (templateType === 'compliant') {
          setCode('#include <iostream>\n\nusing namespace std;\n\n// Compliant: Implements required loop\nint climbStairs(int n) {\n    if (n <= 2) return n;\n    int a = 1, b = 2;\n    for (int i = 3; i <= n; ++i) {\n        int temp = a + b;\n        a = b;\n        b = temp;\n    }\n    return b;\n}\n\nint main() {\n    int n;\n    while (cin >> n) {\n        cout << climbStairs(n) << "\\n";\n    }\n    return 0;\n}\n');
        } else if (templateType === 'violation') {
          setCode('#include <iostream>\n\nusing namespace std;\n\n// Violation: Uses lookup table without required loop\nint main() {\n    int table[] = {0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89};\n    int n;\n    while (cin >> n) {\n        cout << (n < 11 ? table[n] : 1) << "\\n";\n    }\n    return 0;\n}\n');
        }
      } else {
        if (templateType === 'compliant') {
          setCode('#include <iostream>\n#include <sstream>\n#include <string>\n\nusing namespace std;\n\nint main() {\n    string line;\n    while (getline(cin, line)) {\n        if (line.empty()) continue;\n        stringstream ss(line);\n        int val;\n        bool first = true;\n        while (ss >> val) {\n            if (!first) cout << " ";\n            cout << (val * 2);\n            first = false;\n        }\n        cout << "\\n";\n    }\n    return 0;\n}\n');
        } else {
          setCode('#include <iostream>\n\nusing namespace std;\n\nint main() {\n    cout << "2 4 6\\n";\n    return 0;\n}\n');
        }
      }
    } else {
      // Python templates
      if (problem?.slug?.includes('factorial')) {
        if (templateType === 'compliant') {
          setCode('def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n\nif __name__ == "__main__":\n    n = int(input().strip())\n    print(factorial(n))\n');
        } else if (templateType === 'violation') {
          setCode('def factorial(n):\n    ans = 1\n    for i in range(1, n + 1):\n        ans *= i\n    return ans\n\nif __name__ == "__main__":\n    n = int(input().strip())\n    print(factorial(n))\n');
        }
      } else if (problem?.slug?.includes('stairs')) {
        if (templateType === 'compliant') {
          setCode('import sys\n\ndef climb_stairs(n: int) -> int:\n    if n <= 2:\n        return n\n    a, b = 1, 2\n    for _ in range(3, n + 1):\n        a, b = b, a + b\n    return b\n\nfor line in sys.stdin:\n    if line.strip():\n        print(climb_stairs(int(line.strip())))\n');
        } else if (templateType === 'violation') {
          setCode('import sys\n\n# Lookup table without required loop!\ntable = {1: 1, 2: 2, 3: 3, 4: 5, 5: 8, 6: 13, 7: 21, 8: 34, 10: 89}\nfor line in sys.stdin:\n    if line.strip():\n        print(table.get(int(line.strip()), 1))\n');
        }
      } else {
        if (templateType === 'compliant') {
          setCode('import sys\n\nfor line in sys.stdin:\n    if not line.strip():\n        continue\n    print(" ".join(str(int(x) * 2) for x in line.strip().split()))\n');
        } else if (templateType === 'violation') {
          setCode('import sys\n\nprint("2 4 6")\n');
        } else if (templateType === 'syntax_err') {
          setCode('for i in range(4)\n    print("Hello World")\n');
        }
      }
    }
  };

  // Run Code Workflow (Executes sample test cases or custom input in sandbox)
  const handleRunCode = async () => {
    setRunningCode(true);
    setErrorMsg(null);
    setIsConsoleOpen(true);
    setActiveConsoleTab('test_result');

    try {
      const isCustomActive = selectedCaseIdx === -1;
      const res = await api.runCode(problem.id, code, isCustomActive ? customInput : null, selectedLanguage);
      setRunResult(res);
      if (res?.learning_hints) {
        setHints(res.learning_hints);
      }
      if (res?.status === 'accepted') {
        setRevealedHintLevel(0);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Run code failed.');
    } finally {
      setRunningCode(false);
    }
  };

  // Submit Solution Workflow (Full evaluation against public + hidden test cases, saved to DB)
  const handleSubmit = async () => {
    if (!currentUser) {
      onOpenAuth();
      return;
    }

    setEvaluating(true);
    setErrorMsg(null);
    setEvalResult(null);
    setIsConsoleOpen(true);
    setActiveConsoleTab('submission');

    try {
      let result = await api.createSubmission(problem.id, code, problem.version_number || 1, selectedLanguage);

      if (result.status === 'queued' || result.status === 'running') {
        const submissionId = result.id;
        const maxPollAttempts = 30;
        let attempts = 0;

        while (attempts < maxPollAttempts && (result.status === 'queued' || result.status === 'running')) {
          await new Promise((resolve) => setTimeout(resolve, 1000));
          attempts++;
          result = await api.getSubmission(submissionId);
        }
      }

      setEvalResult(result);
      if (result?.learning_hints) {
        setHints(result.learning_hints);
      }

      if (result.total_score === 100) {
        confetti({
          particleCount: 80,
          spread: 70,
          origin: { y: 0.6 },
        });
      }

      // Refresh submissions history
      loadSubmissionHistory(problem.id);
    } catch (err) {
      setErrorMsg(err.message || 'Submission evaluation failed.');
    } finally {
      setEvaluating(false);
    }
  };

  // Verified Solution Handlers
  const handleOpenSolution = async () => {
    setShowSolutionModal(true);
    setSolutionLoading(true);
    setSolutionError(null);
    try {
      const res = await api.getVerifiedSolution(problem.id, selectedLanguage);
      setSolutionData(res);
    } catch (err) {
      setSolutionError(err.message || 'Failed to load verified reference solution.');
    } finally {
      setSolutionLoading(false);
    }
  };

  const handleRevealNextHint = async () => {
    if (!hints) {
      setLoadingHints(true);
      try {
        const failureCat = runResult?.status !== 'accepted'
          ? runResult?.status
          : (evalResult && evalResult.total_score < 100 ? (evalResult.verdict || evalResult.eval_verdict) : null);
        const res = await api.getProgressiveHints(problem.id, failureCat);
        setHints(res);
        setRevealedHintLevel(1);
      } catch (err) {
        console.warn('Hints load failed:', err);
      } finally {
        setLoadingHints(false);
      }
    } else {
      setRevealedHintLevel((prev) => Math.min(3, prev + 1));
    }
  };

  const handleConfirmLoadSolution = () => {
    if (solutionData?.source_code) {
      setCode(solutionData.source_code);
      setShowLoadConfirmModal(false);
      setShowSolutionModal(false);
    }
  };

  // Safe navigation helpers
  const currentIdx = Array.isArray(problemList)
    ? problemList.findIndex((p) => p.id === problem?.id || p.slug === problem?.slug)
    : -1;
  const prevProblem = currentIdx > 0 ? problemList[currentIdx - 1] : null;
  const nextProblem = currentIdx >= 0 && currentIdx < problemList.length - 1 ? problemList[currentIdx + 1] : null;

  // 1. Loading State
  if (loading) {
    return (
      <div className="container" style={{ textAlign: 'center', padding: '6rem 1rem' }}>
        <RefreshCw size={32} className="spin" style={{ margin: '0 auto 1.25rem', color: 'var(--accent-cyan)' }} />
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#ffffff', marginBottom: '0.5rem' }}>
          Loading Coding Workspace...
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          Fetching problem specifications and isolated sandbox environment.
        </p>
      </div>
    );
  }

  // 2. Error / Problem Not Found State
  if (errorMsg || !problem) {
    return (
      <div className="container" style={{ textAlign: 'center', padding: '5rem 1rem', maxWidth: '640px', margin: '0 auto' }}>
        <div style={{
          background: 'rgba(30, 41, 59, 0.85)',
          border: '1px solid rgba(244, 63, 94, 0.4)',
          borderRadius: 'var(--radius-md)',
          padding: '2.5rem 2rem',
          color: '#ffffff',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
        }}>
          <AlertCircle size={44} color="var(--accent-rose)" style={{ margin: '0 auto 1rem' }} />
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: '0.5rem' }}>
            {errorMsg ? 'Failed to Load Problem' : 'Problem Not Found'}
          </h2>
          <p style={{ fontSize: '0.9rem', color: '#cbd5e1', lineHeight: 1.5, marginBottom: '1.5rem' }}>
            {errorMsg || `Could not find a published problem matching identifier "${id}".`}
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
            <button
              onClick={loadProblem}
              className="btn btn-secondary"
              style={{ padding: '0.55rem 1.25rem', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <RefreshCw size={14} />
              <span>Retry</span>
            </button>
            <Link
              to="/"
              className="btn btn-primary"
              style={{ padding: '0.55rem 1.25rem', fontSize: '0.85rem', textDecoration: 'none' }}
            >
              Back to Problem Library
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const sampleCases = Array.isArray(problem.sample_test_cases) ? problem.sample_test_cases : [];
  const topics = Array.isArray(problem.topics) ? problem.topics : [];
  const expectedConcepts = Array.isArray(problem.expected_concepts) ? problem.expected_concepts : [];

  return (
    <div style={{ padding: '0.75rem 1.25rem', minHeight: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
      {/* Top Workspace Navigation Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingBottom: '0.65rem',
        borderBottom: '1px solid var(--border-subtle)',
        marginBottom: '0.75rem',
      }}>
        {/* Left: Back & Prev/Next Problem Navigation */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Link
            to="/"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              color: 'var(--text-muted)',
              textDecoration: 'none',
              fontSize: '0.825rem',
              fontWeight: 500,
              padding: '0.25rem 0.5rem',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(30, 41, 59, 0.4)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <ArrowLeft size={14} />
            <span>Problem List</span>
          </Link>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <button
              onClick={() => prevProblem && navigate(`/problems/${prevProblem.slug || prevProblem.id}`)}
              disabled={!prevProblem}
              title={prevProblem ? `Previous: ${prevProblem.title}` : 'No previous problem'}
              style={{
                background: 'rgba(30, 41, 59, 0.4)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.25rem 0.5rem',
                color: prevProblem ? '#cbd5e1' : '#475569',
                cursor: prevProblem ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                gap: '0.2rem',
                fontSize: '0.75rem',
              }}
            >
              <ChevronLeft size={14} />
              <span>Prev</span>
            </button>

            <button
              onClick={() => nextProblem && navigate(`/problems/${nextProblem.slug || nextProblem.id}`)}
              disabled={!nextProblem}
              title={nextProblem ? `Next: ${nextProblem.title}` : 'No next problem'}
              style={{
                background: 'rgba(30, 41, 59, 0.4)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.25rem 0.5rem',
                color: nextProblem ? '#cbd5e1' : '#475569',
                cursor: nextProblem ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                gap: '0.2rem',
                fontSize: '0.75rem',
              }}
            >
              <span>Next</span>
              <ChevronRight size={14} />
            </button>
          </div>

          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)', marginLeft: '0.5rem' }}>
            {problem.title}
          </span>
        </div>

        {/* Right: Bookmark, Difficulty & View Mode Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <button
            onClick={handleBookmarkToggle}
            title={isSaved ? "Remove from Bookmarks" : "Save to Bookmarks"}
            style={{
              background: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid var(--border-medium)',
              borderRadius: 'var(--radius-sm)',
              padding: '0.25rem 0.6rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              cursor: 'pointer',
              color: isSaved ? '#fbbf24' : 'var(--text-muted)',
              fontSize: '0.75rem',
              fontWeight: 600,
            }}
          >
            <Bookmark size={13} fill={isSaved ? '#fbbf24' : 'none'} />
            <span>{isSaved ? 'Saved' : 'Save'}</span>
          </button>

          <span className={`badge badge-${problem.difficulty || 'medium'}`}>{problem.difficulty || 'medium'}</span>

          {/* View mode toggle */}
          <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(30, 41, 59, 0.5)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', padding: '0.15rem' }}>
            <button
              onClick={() => setViewMode('split')}
              title="Split View (Description + Editor)"
              style={{
                background: viewMode === 'split' ? 'rgba(99, 102, 241, 0.3)' : 'transparent',
                border: 'none',
                color: viewMode === 'split' ? '#ffffff' : '#64748b',
                padding: '0.2rem 0.4rem',
                borderRadius: '3px',
                cursor: 'pointer',
              }}
            >
              <Layers size={13} />
            </button>
            <button
              onClick={() => setViewMode(viewMode === 'code_max' ? 'split' : 'code_max')}
              title="Maximize Code Editor"
              style={{
                background: viewMode === 'code_max' ? 'rgba(99, 102, 241, 0.3)' : 'transparent',
                border: 'none',
                color: viewMode === 'code_max' ? '#ffffff' : '#64748b',
                padding: '0.2rem 0.4rem',
                borderRadius: '3px',
                cursor: 'pointer',
              }}
            >
              <Maximize2 size={13} />
            </button>
          </div>
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div style={{
        flex: 1,
        display: 'grid',
        gridTemplateColumns: viewMode === 'code_max' ? '0 1fr' : viewMode === 'desc_max' ? '1fr 0' : '48% 52%',
        gap: '0.75rem',
        overflow: 'hidden',
      }}>
        {/* Left Pane: Description & Submissions */}
        <div className="glass-panel" style={{
          display: viewMode === 'code_max' ? 'none' : 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden',
          background: 'rgba(15, 23, 42, 0.95)',
        }}>
          {/* Left Tabs */}
          <div style={{
            display: 'flex',
            borderBottom: '1px solid var(--border-subtle)',
            background: 'rgba(15, 23, 42, 0.6)',
          }}>
            <button
              onClick={() => setActiveLeftTab('statement')}
              style={{
                flex: 1,
                padding: '0.6rem 1rem',
                border: 'none',
                background: activeLeftTab === 'statement' ? 'rgba(30, 41, 59, 0.7)' : 'transparent',
                color: activeLeftTab === 'statement' ? '#ffffff' : 'var(--text-muted)',
                borderBottom: activeLeftTab === 'statement' ? '2px solid var(--accent-primary)' : '2px solid transparent',
                fontSize: '0.825rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.4rem',
              }}
            >
              <FileText size={14} />
              <span>Description</span>
            </button>
            <button
              onClick={() => {
                setActiveLeftTab('history');
                if (currentUser && problem.id) loadSubmissionHistory(problem.id);
              }}
              style={{
                flex: 1,
                padding: '0.6rem 1rem',
                border: 'none',
                background: activeLeftTab === 'history' ? 'rgba(30, 41, 59, 0.7)' : 'transparent',
                color: activeLeftTab === 'history' ? '#ffffff' : 'var(--text-muted)',
                borderBottom: activeLeftTab === 'history' ? '2px solid var(--accent-primary)' : '2px solid transparent',
                fontSize: '0.825rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.4rem',
              }}
            >
              <History size={14} />
              <span>Submissions ({submissionHistory.length})</span>
            </button>
          </div>

          {/* Left Tab Content */}
          {activeLeftTab === 'statement' ? (
            <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem' }}>
              {/* Topic Tags */}
              {topics.length > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
                  {topics.map((t, idx) => (
                    <span
                      key={idx}
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
              )}

              <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.4rem', fontWeight: 700, marginBottom: '0.75rem' }}>
                {problem.title}
              </h1>

              {/* Concept Aware Banner */}
              <div style={{
                background: 'rgba(99, 102, 241, 0.1)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.85rem',
                marginBottom: '1.25rem',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#a5b4fc', fontSize: '0.8rem', fontWeight: 700, marginBottom: '0.3rem' }}>
                  <Sparkles size={15} color="var(--accent-cyan)" />
                  <span>CONCEPT-AWARE AST EVALUATION ACTIVE</span>
                </div>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-main)', lineHeight: 1.45, margin: '0 0 0.5rem 0' }}>
                  Your solution is evaluated for both <strong>functional output</strong> (60%) and <strong>conceptual compliance</strong> (40%) using static AST analysis. Solutions matching outputs via shortcuts without the required constructs will have conceptual marks withheld.
                </p>

                {expectedConcepts.length > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap', paddingTop: '0.35rem', borderTop: '1px solid rgba(99, 102, 241, 0.2)' }}>
                    <span style={{ fontSize: '0.72rem', color: '#cbd5e1', fontWeight: 600 }}>
                      Enforced Concepts:
                    </span>
                    {expectedConcepts.map((concept, idx) => (
                      <span
                        key={idx}
                        style={{
                          background: 'rgba(6, 182, 212, 0.15)',
                          border: '1px solid rgba(6, 182, 212, 0.35)',
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

              {/* Statement Markdown Render */}
              <div style={{
                fontSize: '0.88rem',
                color: 'var(--text-main)',
                lineHeight: 1.6,
                whiteSpace: 'pre-wrap',
                marginBottom: '1.5rem',
              }}>
                {problem.statement_markdown}
              </div>

              {/* Input / Output Format & Constraints */}
              {(problem.input_format || problem.output_format || problem.constraints_json) && (
                <div style={{ marginBottom: '1.5rem', background: 'rgba(30, 41, 59, 0.3)', padding: '0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                  {problem.input_format && (
                    <div style={{ marginBottom: '0.5rem' }}>
                      <strong style={{ fontSize: '0.78rem', color: '#cbd5e1' }}>Input Format:</strong>
                      <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '0.2rem 0 0 0' }}>{problem.input_format}</p>
                    </div>
                  )}
                  {problem.output_format && (
                    <div style={{ marginBottom: '0.5rem' }}>
                      <strong style={{ fontSize: '0.78rem', color: '#cbd5e1' }}>Output Format:</strong>
                      <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '0.2rem 0 0 0' }}>{problem.output_format}</p>
                    </div>
                  )}
                  {problem.constraints_json && (
                    <div>
                      <strong style={{ fontSize: '0.78rem', color: '#cbd5e1' }}>Constraints:</strong>
                      <pre style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '0.2rem 0 0 0', fontFamily: 'var(--font-mono)', whiteSpace: 'pre-wrap' }}>
                        {typeof problem.constraints_json === 'string'
                          ? problem.constraints_json
                          : JSON.stringify(problem.constraints_json, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}

              {/* Public Sample Test Cases */}
              {sampleCases.length > 0 && (
                <div>
                  <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.65rem', color: 'var(--text-main)' }}>
                    Examples & Sample Cases
                  </h3>
                  {sampleCases.map((sample, idx) => (
                    <div key={sample.id || idx} style={{
                      background: 'var(--bg-tertiary)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '0.75rem',
                      marginBottom: '0.65rem',
                    }}>
                      <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '0.35rem' }}>
                        Example {idx + 1}
                      </div>
                      {sample.input_data && (
                        <div style={{ marginBottom: '0.4rem' }}>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-subtle)' }}>Input:</div>
                          <pre style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', background: 'rgba(0,0,0,0.3)', padding: '0.35rem 0.5rem', borderRadius: '4px', margin: '0.15rem 0 0' }}>
                            {sample.input_data}
                          </pre>
                        </div>
                      )}
                      <div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-subtle)' }}>Output:</div>
                        <pre style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', background: 'rgba(0,0,0,0.3)', padding: '0.35rem 0.5rem', borderRadius: '4px', margin: '0.15rem 0 0' }}>
                          {sample.expected_output || ''}
                        </pre>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* Submissions History Tab */
            <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0 }}>
                  Submission History
                </h3>
                <button
                  onClick={() => loadSubmissionHistory(problem.id)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--accent-cyan)',
                    fontSize: '0.75rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.3rem',
                  }}
                >
                  <RefreshCw size={12} className={loadingHistory ? 'spin' : ''} />
                  <span>Refresh</span>
                </button>
              </div>

              {!currentUser ? (
                <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
                  <p style={{ marginBottom: '1rem', fontSize: '0.85rem' }}>Please log in to view your previous submissions.</p>
                  <button onClick={onOpenAuth} className="btn btn-primary" style={{ padding: '0.35rem 0.9rem', fontSize: '0.8rem' }}>
                    Log In
                  </button>
                </div>
              ) : loadingHistory ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  <RefreshCw size={18} className="spin" style={{ marginBottom: '0.5rem' }} />
                  <div>Loading submission history...</div>
                </div>
              ) : submissionHistory.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
                  <History size={28} style={{ marginBottom: '0.5rem', opacity: 0.5 }} />
                  <p style={{ fontSize: '0.85rem' }}>No submissions yet for this problem.</p>
                  <p style={{ fontSize: '0.75rem' }}>Click "Submit Solution" below to test your code.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                  {submissionHistory.map((sub, idx) => (
                    <div
                      key={sub.submission_id || idx}
                      style={{
                        background: 'rgba(30, 41, 59, 0.7)',
                        border: '1px solid var(--border-medium)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '0.75rem',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                        <span style={{
                          color: sub.passed ? '#34d399' : '#fb7185',
                          fontWeight: 700,
                          fontSize: '0.825rem',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.3rem',
                        }}>
                          {sub.passed ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
                          {sub.passed ? 'Accepted' : 'Attempted'} ({sub.score}/100 pts)
                        </span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                          {sub.created_at ? new Date(sub.created_at).toLocaleTimeString() : ''}
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        <span style={{
                          background: 'rgba(99, 102, 241, 0.2)',
                          border: '1px solid rgba(99, 102, 241, 0.4)',
                          padding: '0.1rem 0.4rem',
                          borderRadius: '3px',
                          color: '#a5b4fc',
                          textTransform: 'uppercase',
                          fontWeight: 700,
                          fontSize: '0.65rem',
                        }}>
                          {sub.language || 'python'}
                        </span>
                        {sub.functional_score !== null && <span>Functional: <strong style={{ color: '#fff' }}>{sub.functional_score}</strong></span>}
                        {sub.concept_score !== null && <span>Concept: <strong style={{ color: '#fff' }}>{sub.concept_score}</strong></span>}
                      </div>

                      {sub.code_snippet && (
                        <button
                          onClick={() => {
                            setCode(sub.code_snippet);
                            if (sub.language) setSelectedLanguage(sub.language.toLowerCase());
                          }}
                          style={{
                            marginTop: '0.4rem',
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--accent-cyan)',
                            fontSize: '0.7rem',
                            cursor: 'pointer',
                            padding: 0,
                            fontWeight: 600,
                          }}
                        >
                          Load code into editor →
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Pane: Code Editor + LeetCode-style Bottom Test Runner Drawer */}
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '0.5rem', overflow: 'hidden' }}>
          {/* Editor Header */}
          <div className="glass-panel" style={{
            padding: '0.65rem 1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(15, 23, 42, 0.95)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <FileCode2 size={16} color="var(--accent-cyan)" />
              <select
                id="language-select"
                value={selectedLanguage}
                onChange={(e) => handleLanguageChange(e.target.value)}
                style={{
                  background: 'rgba(30, 41, 59, 0.85)',
                  border: '1px solid var(--border-medium)',
                  borderRadius: 'var(--radius-sm)',
                  color: '#ffffff',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  padding: '0.25rem 0.6rem',
                  cursor: 'pointer',
                }}
              >
                {languages.map((lang) => (
                  <option
                    key={lang.id}
                    value={lang.id}
                    disabled={!lang.available}
                    style={{ background: '#0f172a', color: lang.available ? '#ffffff' : '#64748b' }}
                  >
                    {lang.name} {lang.available ? '✓ Ready' : '✗ Unavailable'}
                  </option>
                ))}
              </select>

              {/* Live Compiler Status Pill */}
              {(() => {
                const activeLangObj = languages.find((l) => l.id === selectedLanguage);
                if (activeLangObj && !activeLangObj.available) {
                  return (
                    <span
                      title={activeLangObj.status_message || 'Compiler or runtime not detected on host'}
                      style={{
                        fontSize: '0.7rem',
                        color: '#fb7185',
                        background: 'rgba(244, 63, 94, 0.15)',
                        padding: '0.2rem 0.5rem',
                        borderRadius: '4px',
                        border: '1px solid rgba(244, 63, 94, 0.3)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                      }}
                    >
                      <AlertCircle size={12} />
                      Compiler Unavailable
                    </span>
                  );
                }
                return (
                  <span style={{
                    fontSize: '0.7rem',
                    color: '#34d399',
                    background: 'rgba(16, 185, 129, 0.12)',
                    padding: '0.15rem 0.45rem',
                    borderRadius: '4px',
                    border: '1px solid rgba(16, 185, 129, 0.25)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.25rem',
                  }}>
                    <CheckCircle2 size={12} />
                    {activeLangObj?.version ? `v${activeLangObj.version}` : 'Sandbox Ready'}
                  </span>
                );
              })()}
            </div>

            {/* Quick Demo Templates */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-subtle)' }}>Templates:</span>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => handleQuickTemplate('compliant')}
                style={{ padding: '0.2rem 0.5rem', fontSize: '0.7rem', borderColor: 'rgba(16, 185, 129, 0.4)', color: '#34d399' }}
                title="Loads code that fulfills both functional output and required concepts"
              >
                Compliant
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => handleQuickTemplate('violation')}
                style={{ padding: '0.2rem 0.5rem', fontSize: '0.7rem', borderColor: 'rgba(244, 63, 94, 0.4)', color: '#fb7185' }}
                title="Matches output but violates required concepts"
              >
                Concept Violation
              </button>
            </div>
          </div>

          {/* Monaco Editor Container */}
          <div className="glass-panel" style={{
            flex: 1,
            borderRadius: 'var(--radius-sm)',
            overflow: 'hidden',
            border: '1px solid var(--border-medium)',
            minHeight: '200px',
          }}>
            <Editor
              height="100%"
              defaultLanguage="python"
              language={selectedLanguage === 'cpp' ? 'cpp' : (selectedLanguage === 'java' ? 'java' : 'python')}
              theme="vs-dark"
              value={code}
              onChange={(newVal) => setCode(newVal || '')}
              loading={
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  <RefreshCw size={18} className="spin" style={{ marginRight: '0.5rem', color: 'var(--accent-cyan)' }} />
                  Loading Monaco Code Editor...
                </div>
              }
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                fontFamily: 'var(--font-mono)',
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true,
                padding: { top: 10, bottom: 10 },
              }}
            />
          </div>

          {/* Bottom Test Runner & Execution Results Console */}
          <div className="glass-panel" style={{
            height: isConsoleOpen ? `${consoleHeight}px` : '42px',
            transition: 'height 0.2s ease',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            background: 'rgba(11, 17, 32, 0.98)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-sm)',
          }}>
            {/* Console Header Tabs */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0.35rem 0.75rem',
              borderBottom: isConsoleOpen ? '1px solid var(--border-subtle)' : 'none',
              background: 'rgba(15, 23, 42, 0.8)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Terminal size={14} color="var(--accent-cyan)" />
                <button
                  onClick={() => { setIsConsoleOpen(true); setActiveConsoleTab('testcase'); }}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: activeConsoleTab === 'testcase' ? '#ffffff' : 'var(--text-muted)',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    padding: '0.2rem 0.5rem',
                    borderBottom: activeConsoleTab === 'testcase' ? '2px solid var(--accent-cyan)' : '2px solid transparent',
                  }}
                >
                  Testcase
                </button>
                <button
                  onClick={() => { setIsConsoleOpen(true); setActiveConsoleTab('test_result'); }}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: activeConsoleTab === 'test_result' ? '#ffffff' : 'var(--text-muted)',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    padding: '0.2rem 0.5rem',
                    borderBottom: activeConsoleTab === 'test_result' ? '2px solid var(--accent-cyan)' : '2px solid transparent',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.3rem',
                  }}
                >
                  <span>Test Result</span>
                  {runResult && (
                    <span style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      background: runResult.status === 'accepted' ? '#34d399' : '#fb7185',
                    }} />
                  )}
                </button>
                <button
                  onClick={() => { setIsConsoleOpen(true); setActiveConsoleTab('submission'); }}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: activeConsoleTab === 'submission' ? '#ffffff' : 'var(--text-muted)',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    padding: '0.2rem 0.5rem',
                    borderBottom: activeConsoleTab === 'submission' ? '2px solid var(--accent-primary)' : '2px solid transparent',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.3rem',
                  }}
                >
                  <span>Evaluation</span>
                  {evalResult && (
                    <span style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      background: evalResult.total_score === 100 ? '#34d399' : '#fbbf24',
                    }} />
                  )}
                </button>
              </div>

              {/* Console Toggle & Height adjust */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <button
                  onClick={() => setIsConsoleOpen(!isConsoleOpen)}
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '0.2rem' }}
                  title={isConsoleOpen ? 'Minimize Console' : 'Expand Console'}
                >
                  {isConsoleOpen ? <ChevronDown size={15} /> : <ChevronUp size={15} />}
                </button>
              </div>
            </div>

            {/* Console Body */}
            {isConsoleOpen && (
              <div style={{ flex: 1, overflowY: 'auto', padding: '0.75rem 1rem' }}>
                {/* 1. TESTCASE TAB */}
                {activeConsoleTab === 'testcase' && (
                  <div>
                    {/* Case selector pills */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
                      {sampleCases.map((sc, idx) => (
                        <button
                          key={idx}
                          onClick={() => setSelectedCaseIdx(idx)}
                          style={{
                            background: selectedCaseIdx === idx ? 'rgba(99, 102, 241, 0.25)' : 'rgba(30, 41, 59, 0.5)',
                            border: `1px solid ${selectedCaseIdx === idx ? 'var(--accent-primary)' : 'var(--border-subtle)'}`,
                            color: selectedCaseIdx === idx ? '#ffffff' : 'var(--text-muted)',
                            padding: '0.2rem 0.6rem',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          Case {idx + 1}
                        </button>
                      ))}
                      <button
                        onClick={() => setSelectedCaseIdx(-1)}
                        style={{
                          background: selectedCaseIdx === -1 ? 'rgba(6, 182, 212, 0.25)' : 'rgba(30, 41, 59, 0.5)',
                          border: `1px solid ${selectedCaseIdx === -1 ? 'var(--accent-cyan)' : 'var(--border-subtle)'}`,
                          color: selectedCaseIdx === -1 ? '#ffffff' : 'var(--text-muted)',
                          padding: '0.2rem 0.6rem',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        + Custom Input
                      </button>
                    </div>

                    {/* Selected Case Content */}
                    {selectedCaseIdx >= 0 && sampleCases[selectedCaseIdx] && (
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                        <div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-subtle)', marginBottom: '0.25rem' }}>Input:</div>
                          <pre style={{
                            margin: 0,
                            padding: '0.5rem',
                            background: 'rgba(0,0,0,0.4)',
                            borderRadius: '4px',
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.78rem',
                            color: '#cbd5e1',
                            maxHeight: '110px',
                            overflowY: 'auto',
                          }}>
                            {sampleCases[selectedCaseIdx].input_data || '(empty)'}
                          </pre>
                        </div>
                        <div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-subtle)', marginBottom: '0.25rem' }}>Expected Output:</div>
                          <pre style={{
                            margin: 0,
                            padding: '0.5rem',
                            background: 'rgba(0,0,0,0.4)',
                            borderRadius: '4px',
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.78rem',
                            color: '#cbd5e1',
                            maxHeight: '110px',
                            overflowY: 'auto',
                          }}>
                            {sampleCases[selectedCaseIdx].expected_output || '(empty)'}
                          </pre>
                        </div>
                      </div>
                    )}

                    {selectedCaseIdx === -1 && (
                      <div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-subtle)', marginBottom: '0.25rem' }}>
                          Custom STDIN Input (will be passed to your solution):
                        </div>
                        <textarea
                          rows={3}
                          value={customInput}
                          onChange={(e) => setCustomInput(e.target.value)}
                          placeholder="Type input data here..."
                          style={{
                            width: '100%',
                            background: 'rgba(0,0,0,0.4)',
                            border: '1px solid var(--border-medium)',
                            borderRadius: '4px',
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.78rem',
                            color: '#cbd5e1',
                            padding: '0.5rem',
                            resize: 'none',
                          }}
                        />
                      </div>
                    )}
                  </div>
                )}

                {/* 2. TEST RESULT TAB (from Run Code) */}
                {activeConsoleTab === 'test_result' && (
                  <div>
                    {!runResult && !runningCode && (
                      <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        Click <strong>"Run Code"</strong> to test your solution against sample cases.
                      </div>
                    )}

                    {runningCode && (
                      <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        <RefreshCw size={18} className="spin" style={{ margin: '0 auto 0.5rem', color: 'var(--accent-cyan)' }} />
                        <div>Executing in secure sandbox...</div>
                      </div>
                    )}

                    {runResult && !runningCode && (
                      <div>
                        {/* Status bar */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{
                              padding: '0.2rem 0.6rem',
                              borderRadius: 'var(--radius-sm)',
                              fontSize: '0.75rem',
                              fontWeight: 700,
                              background: runResult.status === 'accepted' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                              color: runResult.status === 'accepted' ? '#34d399' : '#fb7185',
                              border: `1px solid ${runResult.status === 'accepted' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
                              textTransform: 'uppercase',
                            }}>
                              {runResult.status === 'accepted' ? 'Accepted' : runResult.status?.replace('_', ' ')}
                            </span>
                            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                              <Clock size={12} /> {runResult.execution_time_ms ? `${runResult.execution_time_ms.toFixed(1)} ms` : '< 1 ms'}
                            </span>
                          </div>

                          {/* Instant AST Concept Verification */}
                          {Array.isArray(runResult.concept_checks) && runResult.concept_checks.length > 0 && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                              {runResult.concept_checks.map((cc, i) => (
                                <span
                                  key={i}
                                  style={{
                                    fontSize: '0.7rem',
                                    padding: '0.15rem 0.5rem',
                                    borderRadius: '4px',
                                    fontWeight: 600,
                                    background: cc.passed ? 'rgba(16, 185, 129, 0.12)' : 'rgba(244, 63, 94, 0.12)',
                                    color: cc.passed ? '#34d399' : '#fb7185',
                                    border: `1px solid ${cc.passed ? 'rgba(16, 185, 129, 0.25)' : 'rgba(244, 63, 94, 0.25)'}`,
                                  }}
                                >
                                  {cc.passed ? '⚡' : '⚠️'} {cc.concept}: {cc.passed ? 'Satisfied' : 'Missing'}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Syntax error alert */}
                        {!runResult.syntax_valid && !runResult.compilation_error && runResult.syntax_error_message && (
                          <div style={{ background: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.3)', padding: '0.5rem', borderRadius: '4px', fontSize: '0.75rem', color: '#fb7185', marginBottom: '0.5rem' }}>
                            {runResult.syntax_error_message}
                          </div>
                        )}

                        {/* Compilation error alert */}
                        {(runResult.compilation_error || runResult.status === 'compilation_error') && (
                          <div style={{
                            background: 'rgba(244, 63, 94, 0.12)',
                            border: '1px solid rgba(244, 63, 94, 0.4)',
                            borderRadius: '4px',
                            padding: '0.65rem 0.85rem',
                            fontSize: '0.75rem',
                            color: '#fb7185',
                            marginBottom: '0.75rem',
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontWeight: 700, marginBottom: '0.35rem' }}>
                              <AlertCircle size={14} color="var(--accent-rose)" />
                              <span>Compilation Error ({selectedLanguage.toUpperCase()})</span>
                            </div>
                            <pre style={{
                              margin: 0,
                              padding: '0.5rem',
                              background: 'rgba(0, 0, 0, 0.5)',
                              borderRadius: '4px',
                              fontFamily: 'var(--font-mono)',
                              fontSize: '0.72rem',
                              color: '#fca5a5',
                              whiteSpace: 'pre-wrap',
                              maxHeight: '140px',
                              overflowY: 'auto',
                            }}>
                              {runResult.compile_output || runResult.syntax_error_message || 'Compilation failed with non-zero exit status.'}
                            </pre>
                          </div>
                        )}

                        {/* Intelligent Feedback Card */}
                        {runResult.status !== 'accepted' && runResult.intelligent_feedback && (
                          <IntelligentFeedbackCard
                            feedback={runResult.intelligent_feedback}
                            onShowHints={handleRevealNextHint}
                            onShowSolution={handleOpenSolution}
                          />
                        )}

                        {/* Test cases output list */}
                        {Array.isArray(runResult.case_results) && runResult.case_results.map((cr, idx) => (
                          <div key={idx} style={{
                            background: 'rgba(0,0,0,0.3)',
                            border: `1px solid ${cr.passed ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.2)'}`,
                            borderRadius: '4px',
                            padding: '0.5rem 0.75rem',
                            marginBottom: '0.4rem',
                            fontSize: '0.75rem',
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                              <span style={{ fontWeight: 600, color: cr.passed ? '#34d399' : '#fb7185', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                {cr.passed ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
                                Case {cr.case_number} ({cr.status})
                              </span>
                              <span style={{ fontSize: '0.7rem', color: 'var(--text-subtle)' }}>
                                {cr.execution_time_ms ? `${cr.execution_time_ms.toFixed(1)} ms` : ''}
                              </span>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem', marginTop: '0.3rem' }}>
                              <div>
                                <span style={{ color: 'var(--text-subtle)', fontSize: '0.68rem' }}>Input:</span>
                                <div style={{ fontFamily: 'var(--font-mono)', color: '#cbd5e1' }}>{cr.input_data || '(none)'}</div>
                              </div>
                              {cr.expected_output && (
                                <div>
                                  <span style={{ color: 'var(--text-subtle)', fontSize: '0.68rem' }}>Expected:</span>
                                  <div style={{ fontFamily: 'var(--font-mono)', color: '#cbd5e1' }}>{cr.expected_output}</div>
                                </div>
                              )}
                              <div>
                                <span style={{ color: 'var(--text-subtle)', fontSize: '0.68rem' }}>Your Output:</span>
                                <div style={{ fontFamily: 'var(--font-mono)', color: cr.passed ? '#34d399' : '#fb7185' }}>
                                  {cr.actual_output || '(none)'}
                                </div>
                              </div>
                            </div>

                            {/* Failure Explanation */}
                            {!cr.passed && cr.failure_explanation && (
                              <div style={{
                                marginTop: '0.4rem',
                                background: 'rgba(244, 63, 94, 0.08)',
                                border: '1px solid rgba(244, 63, 94, 0.25)',
                                borderRadius: '4px',
                                padding: '0.35rem 0.6rem',
                                color: '#fca5a5',
                                fontSize: '0.72rem',
                                display: 'flex',
                                alignItems: 'flex-start',
                                gap: '0.35rem',
                              }}>
                                <AlertCircle size={13} color="#fb7185" style={{ flexShrink: 0, marginTop: '0.1rem' }} />
                                <div>
                                  <strong>Failure Explanation:</strong> {cr.failure_explanation}
                                </div>
                              </div>
                            )}

                            {cr.stderr && (
                              <div style={{ marginTop: '0.3rem', color: '#fb7185', fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}>
                                Stderr: {cr.stderr}
                              </div>
                            )}
                          </div>
                        ))}

                        {/* Progressive Hints & Show Solution */}
                        {runResult.status !== 'accepted' && (
                          <ProgressiveHintsCard
                            hints={hints || runResult.learning_hints}
                            revealedLevel={revealedHintLevel}
                            onRevealNext={handleRevealNextHint}
                            onShowSolution={handleOpenSolution}
                            loading={loadingHints}
                          />
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* 3. EVALUATION TAB (from Submit Solution) */}
                {activeConsoleTab === 'submission' && (
                  <div>
                    {!evalResult && !evaluating && (
                      <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        Click <strong>"Submit Solution"</strong> to run the full grading suite against hidden tests.
                      </div>
                    )}

                    {evaluating && (
                      <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        <RefreshCw size={18} className="spin" style={{ margin: '0 auto 0.5rem', color: 'var(--accent-primary)' }} />
                        <div>Grading functional tests & AST concept compliance...</div>
                      </div>
                    )}

                    {evalResult && !evaluating && (
                      <div>
                        {/* Score Banner */}
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          paddingBottom: '0.65rem',
                          borderBottom: '1px solid var(--border-subtle)',
                          marginBottom: '0.75rem',
                        }}>
                          <div>
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Evaluation Verdict</div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '0.2rem' }}>
                              <span style={{
                                padding: '0.2rem 0.55rem',
                                borderRadius: '4px',
                                fontSize: '0.78rem',
                                fontWeight: 700,
                                textTransform: 'uppercase',
                                background: evalResult.total_score === 100 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                                color: evalResult.total_score === 100 ? '#34d399' : (evalResult.total_score >= 60 ? '#fbbf24' : '#fb7185'),
                                border: `1px solid ${evalResult.total_score === 100 ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
                              }}>
                                {evalResult.verdict || evalResult.eval_verdict || (evalResult.total_score === 100 ? 'Accepted' : 'Wrong Answer')}
                              </span>
                              {evalResult.summary_feedback && (
                                <span style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>{evalResult.summary_feedback}</span>
                              )}
                            </div>
                          </div>

                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.3rem',
                            fontSize: '1.5rem',
                            fontWeight: 800,
                            fontFamily: 'var(--font-heading)',
                            color: evalResult.total_score === 100 ? '#34d399' : evalResult.total_score > 0 ? '#fbbf24' : '#f43f5e',
                          }}>
                            <span>{evalResult.total_score}</span>
                            <span style={{ fontSize: '0.85rem', color: 'var(--text-subtle)' }}>/100 pts</span>
                          </div>
                        </div>

                        {/* Intelligent Feedback Card */}
                        {evalResult.total_score < 100 && evalResult.intelligent_feedback && (
                          <IntelligentFeedbackCard
                            feedback={evalResult.intelligent_feedback}
                            onShowHints={handleRevealNextHint}
                            onShowSolution={handleOpenSolution}
                          />
                        )}

                        {/* Compilation Error alert in Evaluation */}
                        {(evalResult.summary_feedback?.toLowerCase().includes('compilation error') ||
                          evalResult.test_case_results?.some((tc) => tc.status === 'compilation_error')) && (
                          <div style={{
                            background: 'rgba(244, 63, 94, 0.12)',
                            border: '1px solid rgba(244, 63, 94, 0.4)',
                            borderRadius: '4px',
                            padding: '0.65rem 0.85rem',
                            fontSize: '0.75rem',
                            color: '#fb7185',
                            marginBottom: '0.75rem',
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontWeight: 700, marginBottom: '0.35rem' }}>
                              <AlertCircle size={14} color="var(--accent-rose)" />
                              <span>Compilation Error ({selectedLanguage.toUpperCase()})</span>
                            </div>
                            <pre style={{
                              margin: 0,
                              padding: '0.5rem',
                              background: 'rgba(0, 0, 0, 0.5)',
                              borderRadius: '4px',
                              fontFamily: 'var(--font-mono)',
                              fontSize: '0.72rem',
                              color: '#fca5a5',
                              whiteSpace: 'pre-wrap',
                              maxHeight: '140px',
                              overflowY: 'auto',
                            }}>
                              {evalResult.test_case_results?.find((tc) => tc.status === 'compilation_error')?.error_message ||
                                evalResult.summary_feedback ||
                                'Compilation failed.'}
                            </pre>
                          </div>
                        )}

                        {/* Criteria Breakdown */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem', marginBottom: '0.75rem' }}>
                          {Array.isArray(evalResult.criteria_scores) && evalResult.criteria_scores.map((crit) => (
                            <div key={crit.criterion} style={{
                              background: 'rgba(0,0,0,0.3)',
                              border: '1px solid var(--border-subtle)',
                              borderRadius: 'var(--radius-sm)',
                              padding: '0.5rem',
                            }}>
                              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                                {crit.criterion?.replace('_', ' ')}
                              </div>
                              <div style={{ fontSize: '0.95rem', fontWeight: 700, margin: '0.1rem 0' }}>
                                {crit.awarded_points} <span style={{ fontSize: '0.65rem', color: 'var(--text-subtle)' }}>/ {crit.max_points}</span>
                              </div>
                              <div style={{
                                fontSize: '0.65rem',
                                fontWeight: 600,
                                color: crit.passed ? 'var(--accent-emerald)' : 'var(--accent-rose)'
                              }}>
                                {crit.passed ? 'PASSED' : 'WITHHELD'}
                              </div>
                            </div>
                          ))}
                        </div>

                        {/* AST Concept Evidence */}
                        {Array.isArray(evalResult.concept_evidence) && evalResult.concept_evidence.length > 0 && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                            {evalResult.concept_evidence.map((ev, i) => (
                              <div key={i} style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                padding: '0.4rem 0.6rem',
                                background: ev.passed ? 'rgba(16, 185, 129, 0.08)' : 'rgba(244, 63, 94, 0.08)',
                                border: `1px solid ${ev.passed ? 'rgba(16, 185, 129, 0.25)' : 'rgba(244, 63, 94, 0.25)'}`,
                                borderRadius: 'var(--radius-sm)',
                                fontSize: '0.75rem',
                              }}>
                                {ev.passed ? <CheckCircle2 size={14} color="var(--accent-emerald)" /> : <XCircle size={14} color="var(--accent-rose)" />}
                                <span style={{ color: ev.passed ? '#d1fae5' : '#ffe4e6' }}>{ev.message}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Progressive Hints (if not full score) */}
                        {evalResult.total_score < 100 ? (
                          <ProgressiveHintsCard
                            hints={hints || evalResult.learning_hints}
                            revealedLevel={revealedHintLevel}
                            onRevealNext={handleRevealNextHint}
                            onShowSolution={handleOpenSolution}
                            loading={loadingHints}
                          />
                        ) : (
                          <div style={{
                            marginTop: '0.75rem',
                            padding: '0.75rem 1rem',
                            background: 'rgba(16, 185, 129, 0.08)',
                            border: '1px solid rgba(16, 185, 129, 0.25)',
                            borderRadius: '8px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#d1fae5', fontSize: '0.8rem' }}>
                              <CheckCircle2 size={16} color="var(--accent-emerald)" />
                              <span>Full marks achieved! Compare your code with the verified reference implementation.</span>
                            </div>
                            <button
                              type="button"
                              onClick={handleOpenSolution}
                              className="btn btn-secondary"
                              style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem', borderColor: 'rgba(16, 185, 129, 0.4)', color: '#34d399' }}
                            >
                              View Reference Solution
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Action Bar (Run Code + Submit Solution + Show Correct Solution) */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0.4rem 0',
          }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-subtle)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
              <Cpu size={13} />
              <span>Sandbox runtime: 3.0s limit, memory-bounded isolated container</span>
            </div>

            {(() => {
              const currentLangObj = languages.find((l) => l.id === selectedLanguage);
              const isLangAvailable = currentLangObj ? currentLangObj.available : true;
              return (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {/* SHOW CORRECT SOLUTION BUTTON */}
                  <button
                    type="button"
                    onClick={handleOpenSolution}
                    disabled={runningCode || evaluating}
                    className="btn btn-secondary"
                    title="View verified reference solution and pedagogical walkthrough"
                    style={{
                      padding: '0.5rem 0.9rem',
                      fontSize: '0.825rem',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.35rem',
                      borderColor: 'rgba(6, 182, 212, 0.4)',
                      color: '#38bdf8',
                    }}
                  >
                    <Sparkles size={14} color="var(--accent-cyan)" />
                    <span>Show Correct Solution</span>
                  </button>

                  {/* RUN CODE BUTTON */}
                  <button
                    onClick={handleRunCode}
                    disabled={runningCode || evaluating || !isLangAvailable}
                    className="btn btn-secondary"
                    title={!isLangAvailable ? `${currentLangObj?.name || selectedLanguage} compiler not available on host` : 'Run on sample test cases'}
                    style={{
                      padding: '0.5rem 1rem',
                      fontSize: '0.825rem',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.35rem',
                      opacity: !isLangAvailable ? 0.6 : 1,
                      cursor: !isLangAvailable ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {runningCode ? (
                      <>
                        <RefreshCw size={14} className="spin" />
                        <span>Running...</span>
                      </>
                    ) : (
                      <>
                        <Play size={14} fill="currentColor" />
                        <span>Run Code</span>
                      </>
                    )}
                  </button>

                  {/* SUBMIT SOLUTION BUTTON */}
                  <button
                    onClick={handleSubmit}
                    disabled={evaluating || runningCode || !isLangAvailable}
                    className="btn btn-primary"
                    title={!isLangAvailable ? `${currentLangObj?.name || selectedLanguage} compiler not available on host` : 'Submit solution for grading'}
                    style={{
                      padding: '0.5rem 1.25rem',
                      fontSize: '0.825rem',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.35rem',
                      opacity: !isLangAvailable ? 0.6 : 1,
                      cursor: !isLangAvailable ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {evaluating ? (
                      <>
                        <RefreshCw size={14} className="spin" />
                        <span>Grading Tests & AST...</span>
                      </>
                    ) : (
                      <>
                        <Send size={14} />
                        <span>Submit Solution</span>
                      </>
                    )}
                  </button>
                </div>
              );
            })()}
          </div>

          {/* Error notification alert */}
          {errorMsg && (
            <div style={{
              background: 'rgba(244, 63, 94, 0.1)',
              border: '1px solid rgba(244, 63, 94, 0.3)',
              borderRadius: 'var(--radius-sm)',
              padding: '0.65rem 0.85rem',
              color: '#fb7185',
              fontSize: '0.8rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
            }}>
              <XCircle size={15} color="var(--accent-rose)" />
              <span>{errorMsg}</span>
            </div>
          )}
        </div>
      </div>

      {/* Verified Solution & Pedagogical Guide Modal */}
      <VerifiedSolutionModal
        isOpen={showSolutionModal}
        onClose={() => setShowSolutionModal(false)}
        solutionData={solutionData}
        loading={solutionLoading}
        error={solutionError}
        selectedLanguage={selectedLanguage}
        onLoadIntoEditor={() => setShowLoadConfirmModal(true)}
        problemTitle={problem?.title || 'Problem'}
      />

      {/* Load Solution Confirmation Modal */}
      <LoadSolutionConfirmModal
        isOpen={showLoadConfirmModal}
        onClose={() => setShowLoadConfirmModal(false)}
        onConfirm={handleConfirmLoadSolution}
        language={selectedLanguage}
      />
    </div>
  );
}
