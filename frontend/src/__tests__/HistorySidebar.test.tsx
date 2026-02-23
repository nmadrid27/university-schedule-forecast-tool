import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HistorySidebar } from '@/components/sidebar/HistorySidebar';

describe('HistorySidebar', () => {
  it('shows empty state when no conversations are passed', () => {
    render(<HistorySidebar onNewChat={() => {}} />);

    expect(screen.getByText(/no conversations yet/i)).toBeInTheDocument();
  });

  it('renders a New Chat button', () => {
    render(<HistorySidebar onNewChat={() => {}} />);

    expect(screen.getByRole('button', { name: /new chat/i })).toBeInTheDocument();
  });

  it('calls onNewChat when the New Chat button is clicked', async () => {
    const user = userEvent.setup();
    const onNewChat = vi.fn();
    render(<HistorySidebar onNewChat={onNewChat} />);

    await user.click(screen.getByRole('button', { name: /new chat/i }));

    expect(onNewChat).toHaveBeenCalledOnce();
  });

  it('renders conversation titles when provided', () => {
    const conversations = [
      { id: '1', title: 'Spring 2026 Forecast', date: 'Today' },
      { id: '2', title: 'Fall 2026 Projection', date: 'Today' },
    ];
    render(<HistorySidebar onNewChat={() => {}} conversations={conversations} />);

    expect(screen.getByText('Spring 2026 Forecast')).toBeInTheDocument();
    expect(screen.getByText('Fall 2026 Projection')).toBeInTheDocument();
  });

  it('does not show empty state when conversations are provided', () => {
    const conversations = [{ id: '1', title: 'Any forecast', date: 'Today' }];
    render(<HistorySidebar onNewChat={() => {}} conversations={conversations} />);

    expect(screen.queryByText(/no conversations yet/i)).not.toBeInTheDocument();
  });
});
