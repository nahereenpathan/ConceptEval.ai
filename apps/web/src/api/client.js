/**
 * API Client for Concept-Aware Code Evaluation Platform
 * Centralized HTTP layer handling authentication tokens, standard error formats, and API v1 endpoints.
 */

export function getApiBaseUrl() {
  if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) {
    let base = import.meta.env.VITE_API_BASE_URL.trim().replace(/\/+$/, '');
    if (!base.endsWith('/api/v1')) {
      if (base.endsWith('/api')) {
        base = `${base}/v1`;
      } else {
        base = `${base}/api/v1`;
      }
    }
    return base;
  }
  if (typeof window !== 'undefined' && window.location) {
    const hostname = window.location.hostname || '127.0.0.1';
    // Use 127.0.0.1 directly when on localhost to guarantee matching FastAPI default binding
    const targetHost = (hostname === 'localhost' || hostname === '127.0.0.1') ? '127.0.0.1' : hostname;
    return `${window.location.protocol}//${targetHost}:8000/api/v1`;
  }
  return 'http://127.0.0.1:8000/api/v1';
}

class ApiClient {
  constructor() {
    this.token = typeof localStorage !== 'undefined' ? localStorage.getItem('concept_eval_token') || null : null;
  }

  get baseUrl() {
    return getApiBaseUrl();
  }

  setToken(token) {
    this.token = token;
    if (typeof localStorage !== 'undefined') {
      if (token) {
        localStorage.setItem('concept_eval_token', token);
      } else {
        localStorage.removeItem('concept_eval_token');
      }
    }
  }

  async request(endpoint, options = {}) {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${this.baseUrl}${cleanEndpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    let response;
    try {
      response = await fetch(url, {
        ...options,
        headers,
      });
    } catch (netErr) {
      if (netErr.name === 'AbortError') {
        throw {
          code: 'REQUEST_ABORTED',
          status: 0,
          url,
          message: 'Request was cancelled.',
          originalError: netErr.message || String(netErr),
        };
      }

      // Browser network error or CORS preflight failure
      const currentOrigin = typeof window !== 'undefined' ? window.location.origin : 'current origin';
      throw {
        code: 'NETWORK_ERROR',
        status: 0,
        url,
        message: `Could not connect to FastAPI backend at ${url}. Ensure backend is running on 127.0.0.1:8000 and CORS allows origin ${currentOrigin}.`,
        originalError: netErr.message || String(netErr),
      };
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      let code = 'SERVER_ERROR';
      let message = `Server responded with status ${response.status}`;

      if (response.status === 401) {
        code = 'AUTHENTICATION_REQUIRED';
        message = typeof data.detail === 'string' ? data.detail : 'Authentication required. Please log in.';
      } else if (response.status === 403) {
        code = 'ACCESS_DENIED';
        message = typeof data.detail === 'string' ? data.detail : 'Access denied for this resource.';
      } else if (response.status === 404) {
        code = 'NOT_FOUND';
        message = typeof data.detail === 'string' ? data.detail : 'Requested endpoint or resource was not found.';
      } else if (response.status === 422) {
        code = 'VALIDATION_ERROR';
        if (data.error && data.error.details && Array.isArray(data.error.details)) {
          message = data.error.details.map((d) => (d.loc ? `${d.loc.join('.')}: ${d.msg}` : d.msg)).join('; ');
        } else if (Array.isArray(data.detail)) {
          message = data.detail.map((d) => (d.loc ? `${d.loc.join('.')}: ${d.msg}` : d.msg)).join('; ');
        } else {
          message = data.error?.message || 'Request payload failed schema validation.';
        }
      } else if (response.status >= 500) {
        code = data.error?.code || 'SERVER_ERROR';
        message = data.error?.message || (typeof data.detail === 'string' ? data.detail : `FastAPI internal server error (${response.status}).`);
      } else if (data.error && data.error.message) {
        code = data.error.code || 'REQUEST_FAILED';
        message = data.error.message;
      } else if (typeof data.detail === 'string') {
        code = 'CLIENT_ERROR';
        message = data.detail;
      }

      throw {
        code,
        status: response.status,
        url,
        message,
        data,
      };
    }

    return data;
  }

  // Auth endpoints
  async login(email, password) {
    const res = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (res.access_token) {
      this.setToken(res.access_token);
    }
    return res;
  }

  async register(email, password, displayName) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name: displayName }),
    });
  }

  async getMe() {
    return this.request('/auth/me');
  }

  // Problems endpoints
  async listProblems(options = null) {
    if (typeof options === 'string') {
      return this.request(`/problems?difficulty=${encodeURIComponent(options)}`);
    }

    const params = new URLSearchParams();
    if (options && typeof options === 'object') {
      if (options.difficulty && options.difficulty !== 'all') params.append('difficulty', options.difficulty);
      if (options.topic && options.topic !== 'all') params.append('topic', options.topic);
      if (options.search) params.append('search', options.search);
      if (options.status && options.status !== 'all') params.append('status', options.status);
      if (options.saved_only) params.append('saved_only', 'true');
      if (options.sort_by) params.append('sort_by', options.sort_by);
      if (options.sort_order) params.append('sort_order', options.sort_order);
      if (options.page) params.append('page', options.page);
      if (options.page_size) params.append('page_size', options.page_size);
      if (options.paginate !== undefined) {
        params.append('paginate', options.paginate ? 'true' : 'false');
      } else {
        // Default to paginated mode for rich UI
        params.append('paginate', 'true');
      }
    }

    const qs = params.toString();
    return this.request(`/problems${qs ? `?${qs}` : ''}`);
  }

  async getProblems(options = null) {
    return this.listProblems(options);
  }

  async getProblem(id) {
    return this.request(`/problems/${id}`);
  }

  async runCode(problemId, sourceCode, customInput = null, language = 'python') {
    return this.request(`/problems/${problemId}/run`, {
      method: 'POST',
      body: JSON.stringify({
        language: language || 'python',
        source_code: sourceCode,
        custom_input: customInput,
      }),
    });
  }

  async getSampleCases(id) {
    return this.request(`/problems/${id}/samples`);
  }

  async getTopics() {
    return this.request('/problems/topics');
  }

  async getLanguages() {
    return this.request('/problems/languages');
  }

  async toggleBookmark(problemId) {
    return this.request(`/problems/${problemId}/bookmark`, {
      method: 'POST',
    });
  }

  async getMyBookmarks() {
    return this.request('/problems/bookmarks/me');
  }

  async getMyRecentProblems() {
    return this.request('/problems/recent/me');
  }

  async getProblemSubmissions(problemId) {
    return this.request(`/problems/${problemId}/submissions`);
  }

  async importProblemDataset(payload) {
    return this.request('/problems/import', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async importCsvDataset(payload) {
    return this.request('/problems/import-csv', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getVerifiedSolution(problemId, language = 'python') {
    const params = new URLSearchParams();
    if (language) params.append('language', language);
    const qs = params.toString();
    return this.request(`/problems/${problemId}/verified-solution${qs ? `?${qs}` : ''}`);
  }

  async getProgressiveHints(problemId, failureCategory = null) {
    const params = new URLSearchParams();
    if (failureCategory) params.append('failure_category', failureCategory);
    const qs = params.toString();
    return this.request(`/problems/${problemId}/hints${qs ? `?${qs}` : ''}`);
  }


  // Submissions endpoints
  async createSubmission(problemId, sourceCode, problemVersionNumber = 1, language = 'python') {
    return this.request('/submissions', {
      method: 'POST',
      body: JSON.stringify({
        problem_id: problemId,
        problem_version_number: problemVersionNumber,
        language: language || 'python',
        source_code: sourceCode,
      }),
    });
  }

  async getSubmission(id) {
    return this.request(`/submissions/${id}`);
  }

  async getUserSubmissions() {
    return this.request('/submissions');
  }

  // Authoring & NLP Intent
  async extractIntent(problemText) {
    return this.request('/authoring/extract-intent', {
      method: 'POST',
      body: JSON.stringify({ problem_text: problemText }),
    });
  }

  async getAuthoredProblems() {
    return this.request('/authoring/problems');
  }

  async createAuthoredProblem(payload) {
    return this.request('/authoring/problems', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async validateAuthoredProblem(payload) {
    return this.request('/authoring/validate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async publishAuthoredProblem(problemId) {
    return this.request(`/authoring/problems/${problemId}/publish`, {
      method: 'POST',
    });
  }
}

export const api = new ApiClient();
