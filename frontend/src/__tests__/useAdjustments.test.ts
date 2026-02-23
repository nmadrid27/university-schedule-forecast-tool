import { renderHook, waitFor, act } from '@testing-library/react';
import { useAdjustments } from '@/hooks/useAdjustments';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  api: {
    getAdjustments: vi.fn(),
    toggleAdjustment: vi.fn(),
    removeAdjustment: vi.fn(),
    addAdjustment: vi.fn(),
  },
}));

const mockApi = api as {
  getAdjustments: ReturnType<typeof vi.fn>;
  toggleAdjustment: ReturnType<typeof vi.fn>;
  removeAdjustment: ReturnType<typeof vi.fn>;
  addAdjustment: ReturnType<typeof vi.fn>;
};

const adj1 = {
  id: 'a1', type: 'output', operation: 'multiply', value: 1.1,
  scope: {}, reason: 'Test', enabled: true, source: 'manual',
};
const adj2 = {
  id: 'a2', type: 'output', operation: 'add', value: 5,
  scope: {}, reason: 'More', enabled: false, source: 'llm',
};

beforeEach(() => {
  vi.clearAllMocks();
  mockApi.getAdjustments.mockResolvedValue({ term: 'Spring 2026', adjustments: [adj1] });
});

describe('useAdjustments', () => {
  it('loads adjustments on mount', async () => {
    const { result } = renderHook(() => useAdjustments('Spring 2026'));
    await waitFor(() => expect(result.current.adjustments).toHaveLength(1));
    expect(mockApi.getAdjustments).toHaveBeenCalledWith('Spring 2026');
  });

  it('sets loading true during fetch then false after', async () => {
    let resolve: (v: unknown) => void;
    mockApi.getAdjustments.mockReturnValue(new Promise(r => { resolve = r; }));
    const { result } = renderHook(() => useAdjustments('Spring 2026'));
    expect(result.current.loading).toBe(true);
    await act(async () => {
      resolve!({ term: 'Spring 2026', adjustments: [adj1] });
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
  });

  it('sets empty array when fetch fails', async () => {
    mockApi.getAdjustments.mockRejectedValue(new Error('network error'));
    const { result } = renderHook(() => useAdjustments('Spring 2026'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.adjustments).toEqual([]);
  });

  it('re-fetches when term changes', async () => {
    mockApi.getAdjustments.mockResolvedValue({ term: 'Spring 2026', adjustments: [adj1] });
    const { result, rerender } = renderHook(({ term }) => useAdjustments(term), {
      initialProps: { term: 'Spring 2026' },
    });
    await waitFor(() => expect(result.current.adjustments).toHaveLength(1));

    mockApi.getAdjustments.mockResolvedValue({ term: 'Fall 2026', adjustments: [] });
    rerender({ term: 'Fall 2026' });
    await waitFor(() => expect(mockApi.getAdjustments).toHaveBeenCalledWith('Fall 2026'));
  });

  it('toggleAdjustment calls api and updates state', async () => {
    const toggled = { ...adj1, enabled: false };
    mockApi.toggleAdjustment.mockResolvedValue({ term: 'Spring 2026', adjustments: [toggled] });
    const { result } = renderHook(() => useAdjustments('Spring 2026'));
    await waitFor(() => expect(result.current.adjustments).toHaveLength(1));

    await act(async () => { await result.current.toggleAdjustment('a1'); });
    expect(mockApi.toggleAdjustment).toHaveBeenCalledWith('Spring 2026', 'a1');
    expect(result.current.adjustments[0].enabled).toBe(false);
  });

  it('removeAdjustment calls api and updates state', async () => {
    mockApi.removeAdjustment.mockResolvedValue({ term: 'Spring 2026', adjustments: [] });
    const { result } = renderHook(() => useAdjustments('Spring 2026'));
    await waitFor(() => expect(result.current.adjustments).toHaveLength(1));

    await act(async () => { await result.current.removeAdjustment('a1'); });
    expect(mockApi.removeAdjustment).toHaveBeenCalledWith('Spring 2026', 'a1');
    expect(result.current.adjustments).toHaveLength(0);
  });

  it('activeCount equals number of enabled adjustments', async () => {
    mockApi.getAdjustments.mockResolvedValue({
      term: 'Spring 2026', adjustments: [adj1, adj2],
    });
    const { result } = renderHook(() => useAdjustments('Spring 2026'));
    await waitFor(() => expect(result.current.adjustments).toHaveLength(2));
    // adj1 enabled=true, adj2 enabled=false → activeCount=1
    expect(result.current.activeCount).toBe(1);
  });
});
