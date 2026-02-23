import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DataTable } from '@/components/results/DataTable';
import type { ForecastResult } from '@/lib/types';

const rows: ForecastResult[] = [
  { course: 'FOUN 230', campus: 'Savannah', projectedSeats: 80, sections: 4 },
  { course: 'FOUN 110', campus: 'Savannah', projectedSeats: 120, sections: 6 },
  { course: 'FOUN 120', campus: 'SCADnow',  projectedSeats: 40,  sections: 2 },
];

describe('DataTable', () => {
  it('renders all rows', () => {
    render(<DataTable data={rows} />);

    expect(screen.getByText('FOUN 230')).toBeInTheDocument();
    expect(screen.getByText('FOUN 110')).toBeInTheDocument();
    expect(screen.getByText('FOUN 120')).toBeInTheDocument();
  });

  it('clicking Course header sorts rows ascending by course name', async () => {
    const user = userEvent.setup();
    render(<DataTable data={rows} />);

    await user.click(screen.getByRole('button', { name: /course/i }));

    const cells = screen.getAllByRole('cell').filter((c) =>
      c.textContent?.startsWith('FOUN')
    );
    expect(cells[0]).toHaveTextContent('FOUN 110');
    expect(cells[1]).toHaveTextContent('FOUN 120');
    expect(cells[2]).toHaveTextContent('FOUN 230');
  });

  it('clicking Course header twice sorts descending', async () => {
    const user = userEvent.setup();
    render(<DataTable data={rows} />);

    const courseBtn = screen.getByRole('button', { name: /course/i });
    await user.click(courseBtn);
    await user.click(courseBtn);

    const cells = screen.getAllByRole('cell').filter((c) =>
      c.textContent?.startsWith('FOUN')
    );
    expect(cells[0]).toHaveTextContent('FOUN 230');
    expect(cells[1]).toHaveTextContent('FOUN 120');
    expect(cells[2]).toHaveTextContent('FOUN 110');
  });

  it('clicking a different header resets sort direction to ascending', async () => {
    const user = userEvent.setup();
    render(<DataTable data={rows} />);

    // Sort by Course descending first
    const courseBtn = screen.getByRole('button', { name: /course/i });
    await user.click(courseBtn);
    await user.click(courseBtn);

    // Now click Sections — should sort ascending (smallest first)
    await user.click(screen.getByRole('button', { name: /sections/i }));

    const cells = screen.getAllByRole('cell').filter((c) =>
      c.textContent?.startsWith('FOUN')
    );
    // After ascending sections sort: 2 → 4 → 6 (FOUN 120, FOUN 230, FOUN 110)
    expect(cells[0]).toHaveTextContent('FOUN 120');
    expect(cells[2]).toHaveTextContent('FOUN 110');
  });

  it('renders em dash when changePercent is undefined', () => {
    render(<DataTable data={[{ course: 'FOUN 110', campus: 'Savannah', projectedSeats: 100, sections: 5 }]} />);

    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('renders positive changePercent with + prefix', () => {
    render(<DataTable data={[{ course: 'FOUN 110', campus: 'Savannah', projectedSeats: 100, sections: 5, changePercent: 12.5 }]} />);

    expect(screen.getByText('+12.5%')).toBeInTheDocument();
  });

  it('shows adjusted dot for rows with adjusted flag', () => {
    render(<DataTable data={[{ course: 'FOUN 110', campus: 'Savannah', projectedSeats: 100, sections: 5, adjusted: true }]} />);

    expect(screen.getByRole('img', { name: /adjusted/i })).toBeInTheDocument();
  });
});
