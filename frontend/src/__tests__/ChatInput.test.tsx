import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatInput } from '@/components/chat/ChatInput';

describe('ChatInput', () => {
  it('renders textarea with default placeholder', () => {
    render(<ChatInput onSend={() => {}} />);
    expect(screen.getByRole('textbox', { name: /chat message/i })).toBeInTheDocument();
  });

  it('send button is disabled when input is empty', () => {
    render(<ChatInput onSend={() => {}} />);
    expect(screen.getByRole('button', { name: /send message/i })).toBeDisabled();
  });

  it('send button enables after typing', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={() => {}} />);
    await user.type(screen.getByRole('textbox', { name: /chat message/i }), 'hello');
    expect(screen.getByRole('button', { name: /send message/i })).toBeEnabled();
  });

  it('calls onSend with trimmed text and clears input on button click', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);
    const textarea = screen.getByRole('textbox', { name: /chat message/i });
    await user.type(textarea, '  forecast spring 2026  ');
    await user.click(screen.getByRole('button', { name: /send message/i }));
    expect(onSend).toHaveBeenCalledWith('forecast spring 2026');
    expect(textarea).toHaveValue('');
  });

  it('submits on Enter key', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);
    await user.type(screen.getByRole('textbox', { name: /chat message/i }), 'hello{Enter}');
    expect(onSend).toHaveBeenCalledWith('hello');
  });

  it('does not submit on Shift+Enter', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);
    await user.type(
      screen.getByRole('textbox', { name: /chat message/i }),
      'line one{Shift>}{Enter}{/Shift}line two'
    );
    expect(onSend).not.toHaveBeenCalled();
  });

  it('quick action buttons call onSend directly', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);
    await user.click(screen.getByRole('button', { name: 'Forecast Spring 2026' }));
    expect(onSend).toHaveBeenCalledWith('Forecast Spring 2026');
  });

  it('disables all controls when isLoading is true', () => {
    render(<ChatInput onSend={() => {}} isLoading={true} />);
    expect(screen.getByRole('textbox', { name: /chat message/i })).toBeDisabled();
    screen
      .getAllByRole('button')
      .forEach((btn) => expect(btn).toBeDisabled());
  });
});
