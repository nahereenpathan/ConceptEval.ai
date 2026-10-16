/**
 * API Client for Concept-Aware Code Evaluation Platform
 * Centralized HTTP layer handling authentication tokens, standard error formats, and API v1 endpoints.
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('concept_eval_token') || null;
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('concept_eval_token', token);
    } else {
      localStorage.removeItem('concept_eval_token');
    }
  }

  async request(endpoint, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const errorDetail = data.error || {
          code: 'REQUEST_FAILED',
          message: data.detail || `Server responded with status ${response.status}`,
        };
        throw errorDetail;
      }

      return data;
    } catch (err) {
      if (err.code) throw err;
      throw {
        code: 'NETWORK_ERROR',
        message: 'Could not connect to FastAPI backend on http://localhost:8000. Is the server running?',
      };
    }
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
  async listProblems(difficulty = null) {
    const query = difficulty ? `?difficulty=${difficulty}` : '';
    return this.request(`/problems${query}`);
  }

  async getProblem(id) {
    return this.request(`/problems/${id}`);
  }

  async getSampleCases(id) {
    return this.request(`/problems/${id}/samples`);
  }

  async getTopics() {
    return this.request('/problems/topics');
  }

  // Submissions endpoints
  async createSubmission(problemId, sourceCode, problemVersionNumber = 1) {
    return this.request('/submissions', {
      method: 'POST',
      body: JSON.stringify({
        problem_id: problemId,
        problem_version_number: problemVersionNumber,
        language: 'python',
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
}

export const api = new ApiClient();
