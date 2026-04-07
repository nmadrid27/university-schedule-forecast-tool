import { renderHook, waitFor, act } from '@testing-library/react';
import { useChat } from '@/hooks/useChat';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  api: {
    sendMessage: vi.fn(),
    runForecast: vi.fn(),
  },
}));

const mockApi = api as {
  sendMessage: ReturnType<typeof vi.fn>;
  runForecast: ReturnType<typeof vi.fn>;
};

const defaultChatResponse = {
  message: 'Here is some info.',
  parsedCommand: { intent: 'unknown', parameters: {}, confidence: 0.5 },
  llm_used: false,
  adjustments: [],
};

const forecastRows = [
  { course: 'FOUN 110', campus: 'SAV', projectedSeats: 120, sections: 6 },
];
const forecastSummaryRaw = {
  totalStudents: 120, totalSections: 6, coursesForecasted: 1, method: 'Sequence-based',
};

beforeEach(() => {
  vi.clearAllMocks();
  mockApi.sendMessage.mockResolvedValue(defaultChatResponse);
  mockApi.runForecast.mockResolvedValue({ results: forecastRows, summary: forecastSummaryRaw });
});

// ─── Initial state ────────────────────────────────────────────────────────────

describe('useChat — initial state', () => {
  it('starts with a greeting assistant message', () => {
    const { result } = renderHook(() => useChat());
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].role).toBe('assistant');
    expect(result.current.messages[0].content).toMatch(/forecasting/i);
  });

  it('starts with isLoading false and null forecast state', () => {
    const { result } = renderHook(() => useChat());
    expect(result.current.isLoading).toBe(false);
    expect(result.current.forecastResults).toBeNull();
    expect(result.current.forecastSummary).toBeNull();
    expect(result.current.lastAdjustmentChange).toBe(0);
  });
});

// ─── sendMessage ──────────────────────────────────────────────────────────────

describe('useChat — sendMessage', () => {
  it('appends user message immediately', async () => {
    const { result } = renderHook(() => useChat());
    await act(async () => { await result.current.sendMessage('hello'); });
    const userMsg = result.current.messages.find(m => m.role === 'user');
    expect(userMsg?.content).toBe('hello');
  });

  it('sets isLoading true during fetch then false after', async () => {
    let resolveChat!: (v: unknown) => void;
    mockApi.sendMessage.mockReturnValue(new Promise(r => { resolveChat = r; }));
    const { result } = renderHook(() => useChat());

    act(() => { result.current.sendMessage('hello'); });
    expect(result.current.isLoading).toBe(true);

    await act(async () => { resolveChat(defaultChatResponse); });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
  });

  it('appends assistant response after fetch completes', async () => {
    const { result } = renderHook(() => useChat());
    await act(async () => { await result.current.sendMessage('help me'); });
    const assistantMsgs = result.current.messages.filter(m => m.role === 'assistant');
    // greeting + new response = 2
    expect(assistantMsgs).toHaveLength(2);
    expect(assistantMsgs[1].content).toBe('Here is some info.');
  });

  it('calls runForecast when intent is forecast', async () => {
    mockApi.sendMessage.mockResolvedValue({
      ...defaultChatResponse,
      parsedCommand: { intent: 'forecast', parameters: { term: 'Spring 2026' }, confidence: 0.9 },
    });
    const { result } = renderHook(() => useChat());
    await act(async () => { await result.current.sendMessage('forecast spring 2026'); });
    expect(mockApi.runForecast).toHaveBeenCalledWith(
      expect.objectContaining({ term: 'Spring 2026' })
    );
    expect(result.current.forecastResults).toEqual(forecastRows);
    expect(result.current.forecastSummary?.method).toBe('Sequence-based');
  });

  it('calls runForecast when intent is adjust', async () => {
    mockApi.sendMessage.mockResolvedValue({
      ...defaultChatResponse,
      parsedCommand: { intent: 'adjust', parameters: {}, confidence: 0.9 },
      adjustments: [{ id: 'x1' }],
    });
    const { result } = renderHook(() => useChat());
    await act(async () => { await result.current.sendMessage('add 10% buffer'); });
    expect(mockApi.runForecast).toHaveBeenCalled();
  });

  it('does NOT call runForecast for non-forecast intents', async () => {
    mockApi.sendMessage.mockResolvedValue({
      ...defaultChatResponse,
      parsedCommand: { intent: 'help', parameters: {}, confidence: 0.9 },
    });
    const { result } = renderHook(() => useChat());
    await act(async () => { await result.current.sendMessage('help'); });
    expect(mockApi.runForecast).not.toHaveBeenCalled();
  });

  it('updates lastAdjustmentChange when adjustments are extracted', async () => {
    mockApi.sendMessage.mockResolvedValue({
      ...defaultChatResponse,
      parsedCommand: { intent: 'adjust', parameters: {}, confidence: 0.9 },
      adjustments: [{ id: 'a1', type: 'output', value: 1.1 }],
    });
    const { result } = renderHook(() => useChat());
    const before = result.current.lastAdjustmentChange;
    await act(async () => { await result.current.sendMessage('add adjustment'); });
    expect(result.current.lastAdjustmentChange).toBeGreaterThan(before);
  });

  it('adds error message and clears isLoading when API fails', async () => {
    mockApi.sendMessage.mockRejectedValue(new Error('Network error'));
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const { result } = renderHook(() => useChat());
    await act(async () => { await result.current.sendMessage('forecast'); });
    expect(result.current.isLoading).toBe(false);
    const msgs = result.current.messages;
    expect(msgs[msgs.length - 1].content).toMatch(/backend server/i);
  });
});

// ─── clearMessages ────────────────────────────────────────────────────────────

describe('useChat — clearMessages', () => {
  it('resets to a single greeting and clears forecast state', async () => {
    mockApi.sendMessage.mockResolvedValue({
      ...defaultChatResponse,
      parsedCommand: { intent: 'forecast', parameters: { term: 'Spring 2026' }, confidence: 0.9 },
    });
    const { result } = renderHook(() => useChat());
    await act(async () => { await result.current.sendMessage('forecast'); });
    // Confirm there are forecast results and multiple messages
    expect(result.current.forecastResults).not.toBeNull();

    act(() => { result.current.clearMessages(); });
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].role).toBe('assistant');
    expect(result.current.forecastResults).toBeNull();
    expect(result.current.forecastSummary).toBeNull();
  });
});
