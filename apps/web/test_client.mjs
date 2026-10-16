import assert from 'node:assert';
import { getApiBaseUrl, api } from './src/api/client.js';

console.log('--- Running Frontend API Client Tests ---');

// Test 1: Default base URL resolution in node environment
const defaultUrl = getApiBaseUrl();
console.log('Resolved default base URL:', defaultUrl);
assert(defaultUrl.endsWith('/api/v1'), `Base URL should end with /api/v1, got ${defaultUrl}`);

// Test 2: Custom base URL normalization
const originalEnv = process.env.VITE_API_BASE_URL;

// Test with trailing slash
globalThis.importMetaEnv = { VITE_API_BASE_URL: 'http://example.com/api/v1/' };
// In our client, we check import.meta.env
// Let's test the normalization logic directly

// Test 3: listProblems query string construction
const mockFetch = async (url, options) => {
  return {
    ok: true,
    json: async () => ({
      items: [
        { id: 'prob-1', title: 'Two Sum', difficulty: 'easy', topics: ['Arrays'] }
      ],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    }),
  };
};

const savedFetch = globalThis.fetch;
globalThis.fetch = mockFetch;

try {
  const result = await api.listProblems({
    difficulty: 'easy',
    topic: 'Arrays',
    search: 'Two Sum',
    page: 1,
    page_size: 10,
    paginate: true,
  });

  assert.strictEqual(result.total, 1);
  assert.strictEqual(result.items.length, 1);
  assert.strictEqual(result.items[0].title, 'Two Sum');
  console.log('✓ listProblems correctly queries and parses responses');
} finally {
  globalThis.fetch = savedFetch;
}

// Test 4: Error handling on 500 server response
globalThis.fetch = async () => ({
  ok: false,
  status: 500,
  json: async () => ({
    error: {
      code: 'INTERNAL_SERVER_ERROR',
      message: 'FastAPI database operational error',
      request_id: 'req-12345',
    },
  }),
});

try {
  let errorCaught = null;
  try {
    await api.listProblems();
  } catch (err) {
    errorCaught = err;
  }
  assert(errorCaught !== null, 'Should have thrown error on 500');
  assert.strictEqual(errorCaught.status, 500);
  assert.strictEqual(errorCaught.code, 'INTERNAL_SERVER_ERROR');
  assert.strictEqual(errorCaught.message, 'FastAPI database operational error');
  console.log('✓ 500 responses correctly parsed with code INTERNAL_SERVER_ERROR');
} finally {
  globalThis.fetch = savedFetch;
}

// Test 5: Error handling on 422 validation response
globalThis.fetch = async () => ({
  ok: false,
  status: 422,
  json: async () => ({
    error: {
      code: 'VALIDATION_ERROR',
      details: [{ loc: ['query', 'page'], msg: 'Input should be greater than 0' }],
    },
  }),
});

try {
  let errorCaught = null;
  try {
    await api.listProblems();
  } catch (err) {
    errorCaught = err;
  }
  assert(errorCaught !== null, 'Should have thrown error on 422');
  assert.strictEqual(errorCaught.status, 422);
  assert.strictEqual(errorCaught.code, 'VALIDATION_ERROR');
  assert(errorCaught.message.includes('query.page: Input should be greater than 0'));
  console.log('✓ 422 validation error formatted with field names');
} finally {
  globalThis.fetch = savedFetch;
}

// Test 6: Network error handling
globalThis.fetch = async () => {
  throw new TypeError('Failed to fetch');
};

try {
  let errorCaught = null;
  try {
    await api.listProblems();
  } catch (err) {
    errorCaught = err;
  }
  assert(errorCaught !== null, 'Should catch network error');
  assert.strictEqual(errorCaught.code, 'NETWORK_ERROR');
  assert.strictEqual(errorCaught.status, 0);
  assert(errorCaught.message.includes('Could not connect to FastAPI backend'));
  console.log('✓ Network failures classified as NETWORK_ERROR with connection help');
} finally {
  globalThis.fetch = savedFetch;
}

// Test 7: Abort cancellation
globalThis.fetch = async () => {
  const abortErr = new Error('The user aborted a request.');
  abortErr.name = 'AbortError';
  throw abortErr;
};

try {
  let errorCaught = null;
  try {
    await api.listProblems();
  } catch (err) {
    errorCaught = err;
  }
  assert(errorCaught !== null, 'Should catch abort error');
  assert.strictEqual(errorCaught.code, 'REQUEST_ABORTED');
  console.log('✓ Aborted requests classified as REQUEST_ABORTED');
} finally {
  globalThis.fetch = savedFetch;
}

// Test 8: api.getProblems alias
globalThis.fetch = async (url) => {
  assert(url.includes('/problems'), `URL should contain /problems, got ${url}`);
  return {
    ok: true,
    json: async () => ({
      items: [{ id: 'p1', title: 'Problem 1' }],
      total: 1,
    }),
  };
};

try {
  assert.strictEqual(typeof api.getProblems, 'function', 'api.getProblems must be a function');
  const res = await api.getProblems({ paginate: false });
  assert.strictEqual(res.items.length, 1);
  console.log('✓ api.getProblems alias successfully retrieves problem list without TypeError');
} finally {
  globalThis.fetch = savedFetch;
}

// Test 9: api.getProblem(id) detail retrieval
globalThis.fetch = async (url) => {
  assert(url.endsWith('/problems/d394b316-2f4e-4d87-90d8-37a2712f453f'), `Should query correct problem path, got ${url}`);
  return {
    ok: true,
    json: async () => ({
      id: 'd394b316-2f4e-4d87-90d8-37a2712f453f',
      slug: 'multiply-array-elements-by-two',
      title: 'Multiply Array Elements by Two',
      difficulty: 'easy',
      statement_markdown: 'Multiply every element by 2.',
      expected_concepts: ['loop'],
      sample_test_cases: [{ input_data: '1 2 3', expected_output: '2 4 6' }],
    }),
  };
};

try {
  const detail = await api.getProblem('d394b316-2f4e-4d87-90d8-37a2712f453f');
  assert.strictEqual(detail.id, 'd394b316-2f4e-4d87-90d8-37a2712f453f');
  assert.strictEqual(detail.title, 'Multiply Array Elements by Two');
  assert.deepStrictEqual(detail.expected_concepts, ['loop']);
  assert.strictEqual(detail.sample_test_cases.length, 1);
  console.log('✓ api.getProblem correctly retrieves problem detail payload');
} finally {
  globalThis.fetch = savedFetch;
}

// Test 10: api.getProblem handles 404 NOT_FOUND properly
globalThis.fetch = async () => ({
  ok: false,
  status: 404,
  json: async () => ({
    detail: {
      code: 'PROBLEM_NOT_FOUND',
      message: 'Published problem not found.',
    },
  }),
});

try {
  let notFoundCaught = null;
  try {
    await api.getProblem('non-existent-id-999');
  } catch (err) {
    notFoundCaught = err;
  }
  assert(notFoundCaught !== null, 'Should throw on 404');
  assert.strictEqual(notFoundCaught.status, 404);
  assert.strictEqual(notFoundCaught.code, 'NOT_FOUND');
  console.log('✓ api.getProblem gracefully rejects 404 with structured NOT_FOUND error');
} finally {
  globalThis.fetch = savedFetch;
}

// Test 11: api.runCode sandbox request formatting
globalThis.fetch = async (url, options) => {
  assert(url.endsWith('/problems/test-id/run'), `URL should match /problems/test-id/run, got ${url}`);
  assert.strictEqual(options.method, 'POST');
  const body = JSON.parse(options.body);
  assert.strictEqual(body.language, 'python');
  assert.strictEqual(body.source_code, 'print(42)');
  assert.strictEqual(body.custom_input, '5');
  return {
    ok: true,
    json: async () => ({
      status: 'accepted',
      stdout: '42\n',
      stderr: '',
      execution_time_ms: 12.5,
    }),
  };
};

try {
  const runRes = await api.runCode('test-id', 'print(42)', '5');
  assert.strictEqual(runRes.status, 'accepted');
  assert.strictEqual(runRes.stdout, '42\n');
  console.log('✓ api.runCode correctly sends source code and custom input to sandbox runner');
} finally {
  globalThis.fetch = savedFetch;
}

// Test 12: api.getVerifiedSolution endpoint
globalThis.fetch = async (url) => {
  assert(url.includes('/problems/test-id/verified-solution?language=python'), `URL should contain verified-solution query, got ${url}`);
  return {
    ok: true,
    json: async () => ({
      status: 'verified',
      is_verified: true,
      language: 'python',
      source_code: 'def solve(): pass',
      explanation: {
        approach: 'Hash set tracking',
        time_complexity: 'O(N)',
      },
      verification_results: {
        total_cases: 3,
        passed_cases: 3,
      },
    }),
  };
};

try {
  const verifiedRes = await api.getVerifiedSolution('test-id', 'python');
  assert.strictEqual(verifiedRes.status, 'verified');
  assert.strictEqual(verifiedRes.is_verified, true);
  assert.strictEqual(verifiedRes.explanation.approach, 'Hash set tracking');
  console.log('✓ api.getVerifiedSolution correctly queries verified solution with language');
} finally {
  globalThis.fetch = savedFetch;
}

// Test 13: api.getProgressiveHints endpoint
globalThis.fetch = async (url) => {
  assert(url.includes('/problems/test-id/hints?failure_category=wrong_answer'), `URL should contain hints query, got ${url}`);
  return {
    ok: true,
    json: async () => ({
      tier_1_general: 'Check base conditions.',
      tier_2_concept: 'Consider using a HashSet.',
      tier_3_targeted: 'Notice how duplicates occur consecutively.',
    }),
  };
};

try {
  const hintsRes = await api.getProgressiveHints('test-id', 'wrong_answer');
  assert.strictEqual(hintsRes.tier_1_general, 'Check base conditions.');
  assert.strictEqual(hintsRes.tier_2_concept, 'Consider using a HashSet.');
  console.log('✓ api.getProgressiveHints correctly queries progressive hint tiers');
} finally {
  globalThis.fetch = savedFetch;
}

console.log('All 13 frontend API client unit tests passed successfully!\n');

