/**
 * Vitest setup for the frontend test suite.
 *
 * Responsibilities:
 *   * deterministic environment for every test (no real clock dependency, no real network);
 *   * fail loudly when a test tries to reach the network instead of silently resolving,
 *     which would let a component look "working" against a live API;
 *   * keep the DOM clean between tests.
 *
 * Deliberately dependency-free: Testing Library / jsdom matchers are optional at this
 * stage because the frontend is delivered from P24-01 onward. When those packages are
 * added to the frontend member, import their matchers here — do not weaken this file.
 */

const DEFAULT_TIMEOUT_MS = 10_000;

beforeEach(() => {
  document.body.innerHTML = "";
  window.localStorage.clear();
  window.sessionStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

// A test that reaches the network is a test that is not isolated: fail it explicitly.
vi.stubGlobal(
  "fetch",
  vi.fn(() => {
    throw new Error(
      "network access is not allowed in unit tests; inject a client adapter or mock fetch explicitly",
    );
  }),
);

vi.stubGlobal("__TEST_DEFAULT_TIMEOUT_MS__", DEFAULT_TIMEOUT_MS);
