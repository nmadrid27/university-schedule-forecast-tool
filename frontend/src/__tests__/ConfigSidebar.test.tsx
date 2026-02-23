import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigSidebar } from '@/components/sidebar/ConfigSidebar';
import type { ForecastConfig } from '@/lib/types';

const baseConfig: ForecastConfig = {
  capacity: 20,
  progressionRate: 0.95,
  bufferPercent: 10,
  quartersToForecast: 2,
  term: 'Spring 2026',
};

describe('ConfigSidebar', () => {
  it('renders current capacity value', () => {
    render(<ConfigSidebar config={baseConfig} />);
    expect(screen.getByRole('spinbutton', { name: /section capacity/i })).toHaveValue(20);
  });

  it('calls onConfigChange with new capacity when input changes', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    render(<ConfigSidebar config={baseConfig} onConfigChange={onConfigChange} />);

    const input = screen.getByRole('spinbutton', { name: /section capacity/i });
    fireEvent.change(input, { target: { value: '25' } });

    expect(onConfigChange).toHaveBeenLastCalledWith({ capacity: 25 });
  });

  it('calls onConfigChange with new term when select changes', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    render(<ConfigSidebar config={baseConfig} onConfigChange={onConfigChange} />);

    await user.selectOptions(
      screen.getByRole('combobox', { name: /forecast term/i }),
      'Fall 2026'
    );

    expect(onConfigChange).toHaveBeenCalledWith({ term: 'Fall 2026' });
  });

  it('calls onConfigChange with reset defaults when Reset button is clicked', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    render(<ConfigSidebar config={baseConfig} onConfigChange={onConfigChange} />);

    await user.click(screen.getByRole('button', { name: /reset configuration to defaults/i }));

    expect(onConfigChange).toHaveBeenCalledWith(
      expect.objectContaining({ capacity: 20, progressionRate: 0.95, bufferPercent: 10 })
    );
  });

  it('calls onToggleCollapse when collapse button is clicked', async () => {
    const user = userEvent.setup();
    const onToggleCollapse = vi.fn();
    render(<ConfigSidebar config={baseConfig} onToggleCollapse={onToggleCollapse} />);

    await user.click(screen.getByRole('button', { name: /collapse configuration/i }));

    expect(onToggleCollapse).toHaveBeenCalled();
  });

  it('renders collapsed state with expand button', () => {
    render(<ConfigSidebar config={baseConfig} isCollapsed={true} />);
    expect(screen.getByRole('button', { name: /expand configuration/i })).toBeInTheDocument();
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument();
  });
});
