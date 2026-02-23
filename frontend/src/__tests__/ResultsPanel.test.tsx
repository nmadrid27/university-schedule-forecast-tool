import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ResultsPanel } from '@/components/results/ResultsPanel';
import type { ForecastResult, ForecastSummary } from '@/lib/types';
import type { Adjustment } from '@/lib/adjustments';

const makeResult = (overrides: Partial<ForecastResult> = {}): ForecastResult => ({
  course: 'FOUN 110',
  campus: 'SAV',
  projectedSeats: 120,
  sections: 6,
  ...overrides,
});

const makeSummary = (overrides: Partial<ForecastSummary> = {}): ForecastSummary => ({
  totalStudents: 500,
  totalSections: 25,
  coursesForecasted: 10,
  method: 'Sequence-based',
  lastUpdated: new Date('2026-02-23T10:00:00'),
  ...overrides,
});

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

// ─── Empty state ──────────────────────────────────────────────────────────────

describe('ResultsPanel — empty state', () => {
  it('shows No Forecast Yet heading when results is null', () => {
    render(<ResultsPanel results={null} summary={null} />);
    expect(screen.getByText('No Forecast Yet')).toBeInTheDocument();
  });

  it('shows placeholder description when no results', () => {
    render(<ResultsPanel results={null} summary={null} />);
    expect(screen.getByText(/results will appear here/i)).toBeInTheDocument();
  });

  it('does not render metrics or table when results is null', () => {
    render(<ResultsPanel results={null} summary={null} />);
    expect(screen.queryByText(/course projections/i)).not.toBeInTheDocument();
  });
});

// ─── Results state ────────────────────────────────────────────────────────────

describe('ResultsPanel — with results', () => {
  it('shows Forecast Results heading', () => {
    render(<ResultsPanel results={[makeResult()]} summary={makeSummary()} />);
    expect(screen.getByRole('heading', { name: /forecast results/i })).toBeInTheDocument();
  });

  it('shows method name in subtitle', () => {
    render(<ResultsPanel results={[makeResult()]} summary={makeSummary()} />);
    // method appears in both the subtitle and the footer source line
    expect(screen.getAllByText(/sequence-based/i).length).toBeGreaterThanOrEqual(1);
  });

  it('shows course count in table heading', () => {
    const results = [makeResult(), makeResult({ course: 'FOUN 120' })];
    render(<ResultsPanel results={results} summary={makeSummary()} />);
    expect(screen.getByText(/2 courses/i)).toBeInTheDocument();
  });

  it('CSV button is disabled when onDownload is not provided', () => {
    render(<ResultsPanel results={[makeResult()]} summary={makeSummary()} />);
    expect(screen.getByRole('button', { name: /csv/i })).toBeDisabled();
  });

  it('CSV button is enabled when onDownload is provided', () => {
    render(<ResultsPanel results={[makeResult()]} summary={makeSummary()} onDownload={() => {}} />);
    expect(screen.getByRole('button', { name: /csv/i })).toBeEnabled();
  });

  it('calls onDownload when CSV button is clicked', async () => {
    const user = userEvent.setup();
    const onDownload = vi.fn();
    render(<ResultsPanel results={[makeResult()]} summary={makeSummary()} onDownload={onDownload} />);
    await user.click(screen.getByRole('button', { name: /csv/i }));
    expect(onDownload).toHaveBeenCalled();
  });
});

// ─── Adjustments applied count ────────────────────────────────────────────────

describe('ResultsPanel — adjustments applied text', () => {
  it('shows singular "1 adjustment applied"', () => {
    render(<ResultsPanel results={[makeResult()]} summary={makeSummary({ adjustmentsApplied: 1 })} />);
    expect(screen.getByText(/1 adjustment applied/i)).toBeInTheDocument();
  });

  it('shows plural "2 adjustments applied"', () => {
    render(<ResultsPanel results={[makeResult()]} summary={makeSummary({ adjustmentsApplied: 2 })} />);
    expect(screen.getByText(/2 adjustments applied/i)).toBeInTheDocument();
  });

  it('shows no adjustment text when adjustmentsApplied is undefined', () => {
    render(<ResultsPanel results={[makeResult()]} summary={makeSummary()} />);
    expect(screen.queryByText(/adjustment applied/i)).not.toBeInTheDocument();
  });
});

// ─── AdjustmentBadges visibility ─────────────────────────────────────────────

describe('ResultsPanel — adjustment badges', () => {
  it('renders adjustment badges when adjustments and handlers are present', () => {
    render(
      <ResultsPanel
        results={[makeResult()]}
        summary={makeSummary()}
        adjustments={[makeAdj()]}
        onToggleAdjustment={() => {}}
        onRemoveAdjustment={() => {}}
      />
    );
    expect(screen.getByText(/Adjustments:/i)).toBeInTheDocument();
  });

  it('does not render badges when adjustments list is empty', () => {
    render(
      <ResultsPanel
        results={[makeResult()]}
        summary={makeSummary()}
        adjustments={[]}
        onToggleAdjustment={() => {}}
        onRemoveAdjustment={() => {}}
      />
    );
    expect(screen.queryByText(/Adjustments:/i)).not.toBeInTheDocument();
  });

  it('does not render badges when handlers are missing', () => {
    render(
      <ResultsPanel
        results={[makeResult()]}
        summary={makeSummary()}
        adjustments={[makeAdj()]}
      />
    );
    expect(screen.queryByText(/Adjustments:/i)).not.toBeInTheDocument();
  });
});
