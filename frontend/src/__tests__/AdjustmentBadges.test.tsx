import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AdjustmentBadges } from '@/components/results/AdjustmentBadges';
import type { Adjustment } from '@/lib/adjustments';

const makeAdj = (overrides: Partial<Adjustment> = {}): Adjustment => ({
  id: 'adj-1',
  type: 'output',
  operation: 'multiply',
  value: 1.1,
  scope: { course: 'FOUN 110' },
  reason: 'More retakes expected',
  enabled: true,
  source: 'manual',
  ...overrides,
});

describe('AdjustmentBadges', () => {
  it('renders nothing when adjustments list is empty', () => {
    const { container } = render(
      <AdjustmentBadges adjustments={[]} onToggle={() => {}} onRemove={() => {}} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('renders the adjustment label', () => {
    render(
      <AdjustmentBadges adjustments={[makeAdj()]} onToggle={() => {}} onRemove={() => {}} />
    );
    // multiply 1.1 → "+10% seats [FOUN 110]"
    expect(screen.getByText(/\+10% seats/i)).toBeInTheDocument();
  });

  it('calls onToggle with the adjustment id when badge is clicked', async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(
      <AdjustmentBadges adjustments={[makeAdj()]} onToggle={onToggle} onRemove={() => {}} />
    );
    await user.click(screen.getByTitle(/retakes expected/i));
    expect(onToggle).toHaveBeenCalledWith('adj-1');
  });

  it('calls onRemove when × is clicked — not onToggle', async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    const onRemove = vi.fn();
    render(
      <AdjustmentBadges adjustments={[makeAdj()]} onToggle={onToggle} onRemove={onRemove} />
    );
    await user.click(screen.getByRole('button', { name: /remove/i }));
    expect(onRemove).toHaveBeenCalledWith('adj-1');
    expect(onToggle).not.toHaveBeenCalled();
  });

  it('applies line-through style when adjustment is disabled', () => {
    render(
      <AdjustmentBadges
        adjustments={[makeAdj({ enabled: false })]}
        onToggle={() => {}}
        onRemove={() => {}}
      />
    );
    // The outer badge button has line-through class when disabled
    const badge = screen.getByTitle(/retakes expected/i);
    expect(badge.className).toContain('line-through');
  });

  it('remove button is not nested inside the badge button', () => {
    render(
      <AdjustmentBadges adjustments={[makeAdj()]} onToggle={() => {}} onRemove={() => {}} />
    );
    const removeBtn = screen.getByRole('button', { name: /remove/i });
    // Walk up from the parent — if × is inside another button, parentElement.closest('button') is non-null
    expect(removeBtn.parentElement!.closest('button')).toBeNull();
  });

  it('shows AI label for LLM-sourced adjustments', () => {
    render(
      <AdjustmentBadges
        adjustments={[makeAdj({ source: 'llm' })]}
        onToggle={() => {}}
        onRemove={() => {}}
      />
    );
    expect(screen.getByText('AI')).toBeInTheDocument();
  });
});
