import { render, screen } from '@testing-library/react';
import { ChatWindow } from '@/components/chat/ChatWindow';
import type { Message } from '@/lib/types';

const makeMsg = (overrides: Partial<Message> = {}): Message => ({
  id: 'msg-1',
  role: 'assistant',
  content: 'Hello there.',
  timestamp: new Date('2026-02-23T10:00:00'),
  ...overrides,
});

describe('ChatWindow', () => {
  it('renders Chat Assistant heading', () => {
    render(<ChatWindow messages={[]} isLoading={false} onSendMessage={() => {}} />);
    expect(screen.getByRole('heading', { name: /chat assistant/i })).toBeInTheDocument();
  });

  it('renders each message in the log', () => {
    const messages = [
      makeMsg({ id: '1', content: 'First message' }),
      makeMsg({ id: '2', content: 'Second message', role: 'user' }),
    ];
    render(<ChatWindow messages={messages} isLoading={false} onSendMessage={() => {}} />);
    expect(screen.getByText('First message')).toBeInTheDocument();
    expect(screen.getByText('Second message')).toBeInTheDocument();
  });

  it('shows loading indicator when isLoading is true', () => {
    render(<ChatWindow messages={[]} isLoading={true} onSendMessage={() => {}} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Thinking...')).toBeInTheDocument();
  });

  it('hides loading indicator when isLoading is false', () => {
    render(<ChatWindow messages={[]} isLoading={false} onSendMessage={() => {}} />);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('renders the chat input area', () => {
    render(<ChatWindow messages={[]} isLoading={false} onSendMessage={() => {}} />);
    expect(screen.getByRole('textbox', { name: /chat message/i })).toBeInTheDocument();
  });

  it('messages container has log role for screen readers', () => {
    render(<ChatWindow messages={[]} isLoading={false} onSendMessage={() => {}} />);
    expect(screen.getByRole('log')).toBeInTheDocument();
  });
});
