/**
 * Tests for ApiClient in lib/api.ts.
 * fetch is mocked globally in vitest setup; we stub it per-test.
 */
import { api } from '@/lib/api';

function mockFetch(status: number, body: unknown) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: vi.fn().mockResolvedValue(body),
  }));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

// ─── Request basics ───────────────────────────────────────────────────────

describe('ApiClient — request mechanics', () => {
  it('sends Content-Type: application/json header', async () => {
    mockFetch(200, { status: 'healthy' });
    await api.healthCheck();
    const [, opts] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect((opts.headers as Record<string, string>)['Content-Type']).toBe('application/json');
  });

  it('throws when response is not ok', async () => {
    mockFetch(500, { detail: 'Internal Server Error' });
    await expect(api.healthCheck()).rejects.toThrow('Internal Server Error');
  });

  it('throws with status code in message when no detail field', async () => {
    mockFetch(404, {});
    await expect(api.healthCheck()).rejects.toThrow('404');
  });
});

// ─── sendMessage ──────────────────────────────────────────────────────────

describe('ApiClient — sendMessage', () => {
  it('POSTs to /api/chat with serialized body', async () => {
    mockFetch(200, { message: 'ok', parsedCommand: {}, llm_used: false });
    await api.sendMessage({ message: 'hello' });
    const [url, opts] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toMatch(/\/api\/chat$/);
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toMatchObject({ message: 'hello' });
  });
});

// ─── runForecast ──────────────────────────────────────────────────────────

describe('ApiClient — runForecast', () => {
  it('POSTs to /api/forecast', async () => {
    mockFetch(200, { results: [], summary: {} });
    await api.runForecast({ term: 'Spring 2026' });
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toMatch(/\/api\/forecast$/);
  });

  it('includes term in request body', async () => {
    mockFetch(200, { results: [], summary: {} });
    await api.runForecast({ term: 'Fall 2026' });
    const [, opts] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(JSON.parse(opts.body).term).toBe('Fall 2026');
  });
});

// ─── getConfig / updateConfig ─────────────────────────────────────────────

describe('ApiClient — config endpoints', () => {
  it('getConfig GETs /api/config', async () => {
    mockFetch(200, { capacity: 20, progressionRate: 0.95, bufferPercent: 10, quartersToForecast: 2 });
    await api.getConfig();
    const [url, opts] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toMatch(/\/api\/config$/);
    expect(opts.method).toBe('GET');
  });

  it('updateConfig PUTs /api/config', async () => {
    mockFetch(200, { success: true });
    await api.updateConfig({ capacity: 25 });
    const [url, opts] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toMatch(/\/api\/config$/);
    expect(opts.method).toBe('PUT');
    expect(JSON.parse(opts.body).capacity).toBe(25);
  });
});

// ─── Adjustment endpoints ─────────────────────────────────────────────────

describe('ApiClient — adjustments', () => {
  it('getAdjustments encodes term in URL', async () => {
    mockFetch(200, { term: 'Spring 2026', adjustments: [] });
    await api.getAdjustments('Spring 2026');
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toMatch(/Spring%202026/);
  });

  it('toggleAdjustment PUTs to toggle endpoint', async () => {
    mockFetch(200, { term: 'Spring 2026', adjustments: [] });
    await api.toggleAdjustment('Spring 2026', 'adj-1');
    const [url, opts] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toMatch(/adj-1\/toggle$/);
    expect(opts.method).toBe('PUT');
  });

  it('removeAdjustment DELETEs adjustment by id', async () => {
    mockFetch(200, { term: 'Spring 2026', adjustments: [] });
    await api.removeAdjustment('Spring 2026', 'adj-1');
    const [url, opts] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toMatch(/adj-1$/);
    expect(opts.method).toBe('DELETE');
  });
});

// ─── LLM endpoints ───────────────────────────────────────────────────────

describe('ApiClient — LLM endpoints', () => {
  it('getLLMStatus GETs /api/llm/status', async () => {
    mockFetch(200, { provider: 'none', model: null, base_url: null, has_key: false, configured: false });
    await api.getLLMStatus();
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toMatch(/\/api\/llm\/status$/);
  });

  it('updateLLMConfig PUTs /api/llm/config', async () => {
    mockFetch(200, { success: true, provider: 'anthropic', model: null, configured: false });
    await api.updateLLMConfig({ provider: 'anthropic', api_key: 'sk-test' });
    const [url, opts] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toMatch(/\/api\/llm\/config$/);
    expect(opts.method).toBe('PUT');
    expect(JSON.parse(opts.body).provider).toBe('anthropic');
  });
});
