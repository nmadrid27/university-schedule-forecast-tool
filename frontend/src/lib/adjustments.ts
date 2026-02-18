// TypeScript types for the forecast adjustment system

export interface AdjustmentScope {
  course?: string | null;
  campus?: string | null;
}

export interface Adjustment {
  id: string;
  type: 'config' | 'output';
  parameter?: string | null;  // capacity, progression_rate, buffer_percent
  operation?: string | null;  // multiply, add, set
  value: number;
  scope: AdjustmentScope;
  reason: string;
  enabled: boolean;
  source: 'llm' | 'manual';
}

export interface TermAdjustments {
  term: string;
  adjustments: Adjustment[];
}

export function adjustmentLabel(adj: Adjustment): string {
  const scope = [];
  if (adj.scope.course) scope.push(adj.scope.course);
  if (adj.scope.campus) scope.push(adj.scope.campus);
  const scopeStr = scope.length > 0 ? ` [${scope.join(', ')}]` : '';

  if (adj.type === 'config' && adj.parameter) {
    const param = adj.parameter.replace(/_/g, ' ');
    return `${param} = ${adj.value}${scopeStr}`;
  }

  if (adj.type === 'output' && adj.operation) {
    if (adj.operation === 'multiply') {
      const pct = Math.round((adj.value - 1) * 100);
      const sign = pct >= 0 ? '+' : '';
      return `${sign}${pct}% seats${scopeStr}`;
    }
    if (adj.operation === 'add') {
      const sign = adj.value >= 0 ? '+' : '';
      return `${sign}${adj.value} seats${scopeStr}`;
    }
    if (adj.operation === 'set') {
      return `set to ${adj.value} seats${scopeStr}`;
    }
  }

  return `${adj.type}: ${adj.value}${scopeStr}`;
}
