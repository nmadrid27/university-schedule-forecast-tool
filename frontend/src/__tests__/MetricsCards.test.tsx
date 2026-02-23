import { render, screen } from '@testing-library/react';
import { MetricsCards } from '@/components/results/MetricsCards';
import type { ForecastSummary } from '@/lib/types';

const summary: ForecastSummary = {
  totalStudents: 1234,
  totalSections: 62,
  coursesForecasted: 11,
  method: 'Sequence-based',
};

describe('MetricsCards', () => {
  it('displays total students rounded and localised', () => {
    render(<MetricsCards summary={summary} />);
    expect(screen.getByText('1,234')).toBeInTheDocument();
  });

  it('displays total sections', () => {
    render(<MetricsCards summary={summary} />);
    expect(screen.getByText('62')).toBeInTheDocument();
  });

  it('displays courses forecasted', () => {
    render(<MetricsCards summary={summary} />);
    expect(screen.getByText('11')).toBeInTheDocument();
  });

  it('rounds fractional total students', () => {
    render(<MetricsCards summary={{ ...summary, totalStudents: 99.7 }} />);
    expect(screen.getByText('100')).toBeInTheDocument();
  });
});
