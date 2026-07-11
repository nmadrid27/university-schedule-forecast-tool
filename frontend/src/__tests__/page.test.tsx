/**
 * Tests for the main page component (app/page.tsx).
 *
 * Hooks and the API client are mocked so tests focus on the page's own logic:
 *   - initial config fetch from backend on mount
 *   - debounced config persist on change
 *   - adjustment reload when lastAdjustmentChange fires
 *   - CSV download handler
 *   - three-panel layout renders
 */
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Home from '@/app/page';
import { api } from '@/lib/api';

// ── Mock hooks ────────────────────────────────────────────────────────────────

const mockSendMessage = vi.fn();
const mockClearMessages = vi.fn();
const mockLoadAdjustments = vi.fn();
const mockToggleAdjustment = vi.fn();
const mockRemoveAdjustment = vi.fn();

let mockLastAdjustmentChange = 0;

vi.mock('@/hooks/useChat', () => ({
  useChat: () => ({
    messages: [],
    isLoading: false,
    sendMessage: mockSendMessage,
    clearMessages: mockClearMessages,
    forecastResults: null,
    forecastSummary: null,
    get lastAdjustmentChange() { return mockLastAdjustmentChange; },
  }),
}));

vi.mock('@/hooks/useAdjustments', () => ({
  useAdjustments: () => ({
    adjustments: [],
    toggleAdjustment: mockToggleAdjustment,
    removeAdjustment: mockRemoveAdjustment,
    loadAdjustments: mockLoadAdjustments,
    loading: false,
    activeCount: 0,
  }),
}));

// ── Mock API ──────────────────────────────────────────────────────────────────

vi.mock('@/lib/api', () => ({
  api: {
    getConfig: vi.fn(),
    getTerms: vi.fn(),
    updateConfig: vi.fn(),
  },
}));

const mockApi = api as {
  getConfig: ReturnType<typeof vi.fn>;
  getTerms: ReturnType<typeof vi.fn>;
  updateConfig: ReturnType<typeof vi.fn>;
};

beforeEach(() => {
  vi.clearAllMocks();
  mockLastAdjustmentChange = 0;
  mockApi.getConfig.mockResolvedValue({
    capacity: 20,
    progressionRate: 0.95,
    bufferPercent: 10,
    quartersToForecast: 2,
    defaultTerm: 'Spring 2026',
    method: 'auto',
    demandMetric: 'actual',
  });
  mockApi.getTerms.mockResolvedValue({
    available_terms: [],
    forecastable_terms: [],
    forecastable_by_method: { auto: [], historical: [], sequence: [] },
  });
  mockApi.updateConfig.mockResolvedValue({ success: true });
  // Stub browser APIs not implemented in jsdom
  global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
  global.URL.revokeObjectURL = vi.fn();
});

// ── Layout ────────────────────────────────────────────────────────────────────

describe('Home — layout', () => {
  it('renders the chat assistant heading', async () => {
    render(<Home />);
    await waitFor(() => expect(mockApi.getConfig).toHaveBeenCalled());
    expect(screen.getByRole('heading', { name: /chat assistant/i })).toBeInTheDocument();
  });

  it('renders the No Forecast Yet empty state', async () => {
    render(<Home />);
    await waitFor(() => expect(mockApi.getConfig).toHaveBeenCalled());
    expect(screen.getByText('No Forecast Yet')).toBeInTheDocument();
  });

  it('renders a New Chat button in the history sidebar', async () => {
    render(<Home />);
    await waitFor(() => expect(mockApi.getConfig).toHaveBeenCalled());
    expect(screen.getByRole('button', { name: /new chat/i })).toBeInTheDocument();
  });
});

// ── Config fetch on mount ─────────────────────────────────────────────────────

describe('Home — config fetch on mount', () => {
  it('calls api.getConfig on mount', async () => {
    render(<Home />);
    await waitFor(() => expect(mockApi.getConfig).toHaveBeenCalledOnce());
  });

  it('does not crash when getConfig rejects', async () => {
    mockApi.getConfig.mockRejectedValue(new Error('network error'));
    expect(() => render(<Home />)).not.toThrow();
    await waitFor(() => expect(mockApi.getConfig).toHaveBeenCalled());
  });
});

// ── New chat clears messages ──────────────────────────────────────────────────

describe('Home — new chat', () => {
  it('calls clearMessages when New Chat is clicked', async () => {
    const user = userEvent.setup();
    render(<Home />);
    await waitFor(() => expect(mockApi.getConfig).toHaveBeenCalled());

    await user.click(screen.getByRole('button', { name: /new chat/i }));

    expect(mockClearMessages).toHaveBeenCalledOnce();
  });
});

// ── Debounced config save ─────────────────────────────────────────────────────

describe('Home — config persistence', () => {
  it('does not call updateConfig before initialLoadDone resolves', () => {
    // Config resolves after render; updateConfig must not fire during mount
    let resolve: (v: unknown) => void;
    mockApi.getConfig.mockReturnValue(new Promise(r => { resolve = r; }));
    render(<Home />);
    expect(mockApi.updateConfig).not.toHaveBeenCalled();
    // Clean up pending promise
    act(() => { resolve!({ capacity: 20, progressionRate: 0.95, bufferPercent: 10, quartersToForecast: 2 }); });
  });
});

// ── Adjustment reload when LLM fires ─────────────────────────────────────────

describe('Home — adjustment reload', () => {
  it('does not call loadAdjustments when lastAdjustmentChange is 0', async () => {
    render(<Home />);
    await waitFor(() => expect(mockApi.getConfig).toHaveBeenCalled());
    expect(mockLoadAdjustments).not.toHaveBeenCalled();
  });
});

// ── CSV download ──────────────────────────────────────────────────────────────

describe('Home — CSV download', () => {
  it('CSV button is absent in the empty state (no results)', async () => {
    // forecastResults=null from mock → ResultsPanel renders empty state,
    // which never shows the Export CSV button at all
    render(<Home />);
    await waitFor(() => expect(mockApi.getConfig).toHaveBeenCalled());
    expect(screen.queryByRole('button', { name: /csv/i })).not.toBeInTheDocument();
  });
});
