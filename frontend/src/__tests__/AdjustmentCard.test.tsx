import { render, screen } from '@testing-library/react';
import { AdjustmentCard } from '@/components/chat/AdjustmentCard';
import type { Adjustment } from '@/lib/adjustments';

const makeAdj = (overrides: Partial<Adjustment> = {}): Adjustment => ({
  id: 'a1',
  type: 'output',
  operation: 'multiply',
  value: 1.1,
  scope: {},
  reason: 'buffer up',
  enabled: true,
  source: 'manual',
  ...overrides,
});

describe('AdjustmentCard', () => {
  it('renders nothing when adjustments array is empty', () => {
    const { container } = render(<AdjustmentCard adjustments={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows singular label for one adjustment', () => {
    render(<AdjustmentCard adjustments={[makeAdj()]} />);
    expect(screen.getByText('Adjustment Applied')).toBeInTheDocument();
  });

  it('shows plural label with count for multiple adjustments', () => {
    render(<AdjustmentCard adjustments={[makeAdj({ id: 'a1' }), makeAdj({ id: 'a2' })]} />);
    expect(screen.getByText('2 Adjustments Applied')).toBeInTheDocument();
  });

  it('renders the adjustment label text', () => {
    render(<AdjustmentCard adjustments={[makeAdj()]} />);
    // multiply 1.1 → "+10% seats"
    expect(screen.getByText('+10% seats')).toBeInTheDocument();
  });

  it('renders the reason when present', () => {
    render(<AdjustmentCard adjustments={[makeAdj({ reason: 'advisor request' })]} />);
    expect(screen.getByText(/advisor request/i)).toBeInTheDocument();
  });

  it('omits reason span when reason is empty', () => {
    render(<AdjustmentCard adjustments={[makeAdj({ reason: '' })]} />);
    expect(screen.queryByText(/—/)).not.toBeInTheDocument();
  });

  it('renders all adjustments in the list', () => {
    const adjs = [
      makeAdj({ id: 'a1', value: 1.1 }),
      makeAdj({ id: 'a2', operation: 'add', value: 5 }),
    ];
    render(<AdjustmentCard adjustments={adjs} />);
    expect(screen.getByText('+10% seats')).toBeInTheDocument();
    expect(screen.getByText('+5 seats')).toBeInTheDocument();
  });
});
