import { adjustmentLabel } from '@/lib/adjustments';
import type { Adjustment } from '@/lib/adjustments';

const base: Omit<Adjustment, 'type' | 'value'> = {
  id: 'a1',
  reason: 'test',
  enabled: true,
  source: 'manual',
  scope: {},
};

describe('adjustmentLabel', () => {
  // --- output / multiply ---

  it('formats a positive multiply as +N% seats', () => {
    expect(adjustmentLabel({ ...base, type: 'output', operation: 'multiply', value: 1.1 }))
      .toBe('+10% seats');
  });

  it('formats a negative multiply as -N% seats (no double sign)', () => {
    expect(adjustmentLabel({ ...base, type: 'output', operation: 'multiply', value: 0.9 }))
      .toBe('-10% seats');
  });

  it('formats a 2× multiply as +100% seats', () => {
    expect(adjustmentLabel({ ...base, type: 'output', operation: 'multiply', value: 2.0 }))
      .toBe('+100% seats');
  });

  it('formats a no-op multiply (1.0) as +0% seats', () => {
    expect(adjustmentLabel({ ...base, type: 'output', operation: 'multiply', value: 1.0 }))
      .toBe('+0% seats');
  });

  // --- output / add ---

  it('formats a positive add as +N seats', () => {
    expect(adjustmentLabel({ ...base, type: 'output', operation: 'add', value: 5 }))
      .toBe('+5 seats');
  });

  it('formats a negative add as -N seats', () => {
    expect(adjustmentLabel({ ...base, type: 'output', operation: 'add', value: -3 }))
      .toBe('-3 seats');
  });

  // --- output / set ---

  it('formats a set operation as "set to N seats"', () => {
    expect(adjustmentLabel({ ...base, type: 'output', operation: 'set', value: 40 }))
      .toBe('set to 40 seats');
  });

  // --- config ---

  it('formats a config parameter as "param = value"', () => {
    expect(adjustmentLabel({ ...base, type: 'config', parameter: 'capacity', value: 25 }))
      .toBe('capacity = 25');
  });

  it('converts underscores in parameter names to spaces', () => {
    expect(adjustmentLabel({ ...base, type: 'config', parameter: 'progression_rate', value: 0.9 }))
      .toBe('progression rate = 0.9');
  });

  // --- scope ---

  it('appends course scope in brackets', () => {
    expect(adjustmentLabel({
      ...base, type: 'output', operation: 'multiply', value: 1.1,
      scope: { course: 'FOUN 110' },
    })).toBe('+10% seats [FOUN 110]');
  });

  it('appends campus scope in brackets', () => {
    expect(adjustmentLabel({
      ...base, type: 'output', operation: 'add', value: 2,
      scope: { campus: 'SCADnow' },
    })).toBe('+2 seats [SCADnow]');
  });

  it('appends both course and campus separated by comma', () => {
    expect(adjustmentLabel({
      ...base, type: 'output', operation: 'set', value: 30,
      scope: { course: 'FOUN 130', campus: 'SCADnow' },
    })).toBe('set to 30 seats [FOUN 130, SCADnow]');
  });

  it('omits scope brackets when scope is empty', () => {
    expect(adjustmentLabel({ ...base, type: 'output', operation: 'add', value: 1, scope: {} }))
      .toBe('+1 seats');
  });

  // --- fallback ---

  it('falls back to "type: value" for unknown operation', () => {
    expect(adjustmentLabel({ ...base, type: 'output', operation: 'unknown', value: 5 }))
      .toBe('output: 5');
  });

  it('falls back to "type: value" for config without parameter', () => {
    expect(adjustmentLabel({ ...base, type: 'config', value: 20 }))
      .toBe('config: 20');
  });
});
