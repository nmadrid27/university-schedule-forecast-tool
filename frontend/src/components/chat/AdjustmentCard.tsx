'use client';

import { Adjustment, adjustmentLabel } from '@/lib/adjustments';

interface AdjustmentCardProps {
  adjustments: Adjustment[];
}

export function AdjustmentCard({ adjustments }: AdjustmentCardProps) {
  if (adjustments.length === 0) return null;

  return (
    <div className="mt-2 rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950 p-3">
      <div className="flex items-center gap-2 mb-2">
        <div className="h-2 w-2 rounded-full bg-blue-500" />
        <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">
          {adjustments.length === 1 ? 'Adjustment Applied' : `${adjustments.length} Adjustments Applied`}
        </span>
      </div>
      <div className="space-y-1">
        {adjustments.map((adj) => (
          <div key={adj.id} className="flex items-center gap-2 text-xs text-blue-600 dark:text-blue-400">
            <span className="font-medium">{adjustmentLabel(adj)}</span>
            {adj.reason && (
              <span className="text-blue-500/70 dark:text-blue-400/60">
                — {adj.reason}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
