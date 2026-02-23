import { render, screen } from '@testing-library/react';
import { MessageBubble } from '@/components/chat/MessageBubble';
import type { Message } from '@/lib/types';

const makeMsg = (overrides: Partial<Message> = {}): Message => ({
  id: 'msg-1',
  role: 'assistant',
  content: 'Here is your forecast.',
  timestamp: new Date('2026-02-23T10:00:00'),
  ...overrides,
});

describe('MessageBubble', () => {
  it('renders message content', () => {
    render(<MessageBubble message={makeMsg()} />);
    expect(screen.getByText('Here is your forecast.')).toBeInTheDocument();
  });

  it('shows U avatar for user messages', () => {
    render(<MessageBubble message={makeMsg({ role: 'user' })} />);
    expect(screen.getByText('U')).toBeInTheDocument();
  });

  it('shows AI avatar for assistant messages', () => {
    render(<MessageBubble message={makeMsg()} />);
    expect(screen.getByText('AI')).toBeInTheDocument();
  });

  it('renders **bold** markers as <strong> elements', () => {
    render(<MessageBubble message={makeMsg({ content: 'Check **FOUN 110** now.' })} />);
    const strong = screen.getByText('FOUN 110');
    expect(strong.tagName).toBe('STRONG');
  });

  it('shows AI badge when llm_used is true', () => {
    render(
      <MessageBubble
        message={makeMsg({ metadata: { llm_used: true } })}
      />
    );
    // Avatar text is "AI"; the badge is a separate small span — find all and confirm two
    const aiElements = screen.getAllByText('AI');
    expect(aiElements.length).toBeGreaterThanOrEqual(2);
  });

  it('shows intent badge for known intents', () => {
    render(
      <MessageBubble
        message={makeMsg({
          metadata: { parsedCommand: { intent: 'forecast', parameters: {}, confidence: 0.9 } },
        })}
      />
    );
    expect(screen.getByText('forecast')).toBeInTheDocument();
  });

  it('does not show intent badge for unknown intent', () => {
    render(
      <MessageBubble
        message={makeMsg({
          metadata: { parsedCommand: { intent: 'unknown', parameters: {}, confidence: 0.3 } },
        })}
      />
    );
    expect(screen.queryByText('unknown')).not.toBeInTheDocument();
  });
});
