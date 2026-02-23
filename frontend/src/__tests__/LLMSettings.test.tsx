import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LLMSettings } from '@/components/sidebar/LLMSettings';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  api: {
    getLLMStatus: vi.fn(),
    updateLLMConfig: vi.fn(),
  },
}));

const mockApi = api as {
  getLLMStatus: ReturnType<typeof vi.fn>;
  updateLLMConfig: ReturnType<typeof vi.fn>;
};

const unconfiguredStatus = {
  provider: 'none', model: null, base_url: null, has_key: false, configured: false,
};
const anthropicStatus = {
  provider: 'anthropic', model: 'claude-haiku-4-5-20251001', base_url: null,
  has_key: true, configured: true,
};

beforeEach(() => {
  vi.clearAllMocks();
  mockApi.getLLMStatus.mockResolvedValue(unconfiguredStatus);
  mockApi.updateLLMConfig.mockResolvedValue({ success: true });
});

// ─── Initial state ─────────────────────────────────────────────────────────

describe('LLMSettings — initial state', () => {
  it('shows Not configured when status is unconfigured', async () => {
    render(<LLMSettings />);
    await waitFor(() => expect(screen.getByText(/not configured/i)).toBeInTheDocument());
  });

  it('shows Connected with provider name when configured', async () => {
    mockApi.getLLMStatus.mockResolvedValue(anthropicStatus);
    render(<LLMSettings />);
    await waitFor(() => expect(screen.getByText(/connected.*anthropic/i)).toBeInTheDocument());
  });

  it('renders provider select with all options', async () => {
    render(<LLMSettings />);
    const select = screen.getByLabelText(/provider/i);
    expect(select).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole('option', { name: /none/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /openai/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /anthropic/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /ollama/i })).toBeInTheDocument();
    });
  });
});

// ─── Conditional field visibility ──────────────────────────────────────────

describe('LLMSettings — conditional fields', () => {
  it('hides model and save button when provider is none', async () => {
    render(<LLMSettings />);
    await waitFor(() => expect(screen.queryByLabelText(/^model/i)).not.toBeInTheDocument());
    expect(screen.queryByRole('button', { name: /save configuration/i })).not.toBeInTheDocument();
  });

  it('shows model input when provider is anthropic', async () => {
    render(<LLMSettings />);
    await userEvent.selectOptions(screen.getByLabelText(/provider/i), 'anthropic');
    expect(screen.getByLabelText(/^model/i)).toBeInTheDocument();
  });

  it('shows API key input for providers that need a key', async () => {
    render(<LLMSettings />);
    await userEvent.selectOptions(screen.getByLabelText(/provider/i), 'openai');
    expect(screen.getByLabelText(/api key/i)).toBeInTheDocument();
  });

  it('hides API key for ollama (no key needed)', async () => {
    render(<LLMSettings />);
    await userEvent.selectOptions(screen.getByLabelText(/provider/i), 'ollama');
    expect(screen.queryByLabelText(/api key/i)).not.toBeInTheDocument();
  });

  it('shows base URL for ollama and pre-fills localhost', async () => {
    render(<LLMSettings />);
    await userEvent.selectOptions(screen.getByLabelText(/provider/i), 'ollama');
    const urlInput = screen.getByLabelText(/base url/i);
    expect(urlInput).toBeInTheDocument();
    expect(urlInput).toHaveValue('http://localhost:11434/v1');
  });

  it('hides base URL for anthropic', async () => {
    render(<LLMSettings />);
    await userEvent.selectOptions(screen.getByLabelText(/provider/i), 'anthropic');
    expect(screen.queryByLabelText(/base url/i)).not.toBeInTheDocument();
  });
});

// ─── Save action ───────────────────────────────────────────────────────────

describe('LLMSettings — save', () => {
  it('calls updateLLMConfig with provider and model on save', async () => {
    render(<LLMSettings />);
    await userEvent.selectOptions(screen.getByLabelText(/provider/i), 'anthropic');
    await userEvent.click(screen.getByRole('button', { name: /save configuration/i }));
    await waitFor(() => expect(mockApi.updateLLMConfig).toHaveBeenCalledWith(
      expect.objectContaining({ provider: 'anthropic' })
    ));
  });

  it('re-fetches status after save', async () => {
    render(<LLMSettings />);
    await userEvent.selectOptions(screen.getByLabelText(/provider/i), 'anthropic');
    await userEvent.click(screen.getByRole('button', { name: /save configuration/i }));
    await waitFor(() => expect(mockApi.getLLMStatus).toHaveBeenCalledTimes(2));
  });

  it('shows error message when save fails', async () => {
    mockApi.updateLLMConfig.mockRejectedValue(new Error('Network error'));
    render(<LLMSettings />);
    await userEvent.selectOptions(screen.getByLabelText(/provider/i), 'anthropic');
    await userEvent.click(screen.getByRole('button', { name: /save configuration/i }));
    await waitFor(() => expect(screen.getByText(/network error/i)).toBeInTheDocument());
  });

  it('shows Disable AI Assistant button when provider=none but status is configured', async () => {
    mockApi.getLLMStatus.mockResolvedValue(anthropicStatus);
    render(<LLMSettings />);
    // Wait for status to load; default select value is 'none' (set from loaded status: anthropic)
    // After load, select is set to 'anthropic' — switch back to none to see button
    await waitFor(() => screen.getByText(/connected/i));
    await userEvent.selectOptions(screen.getByLabelText(/provider/i), 'none');
    expect(screen.getByRole('button', { name: /disable ai assistant/i })).toBeInTheDocument();
  });
});
