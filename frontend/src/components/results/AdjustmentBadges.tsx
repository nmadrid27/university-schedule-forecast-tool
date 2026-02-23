'use client';

import { Adjustment, adjustmentLabel } from '@/lib/adjustments';

interface AdjustmentBadgesProps {
  adjustments: Adjustment[];
  onToggle: (id: string) => void;
  onRemove: (id: string) => void;
}

export function AdjustmentBadges({ adjustments, onToggle, onRemove }: AdjustmentBadgesProps) {
  if (adjustments.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mb-4">
      <span className="text-xs font-medium text-muted-foreground self-center">
        Adjustments:
      </span>
      {adjustments.map((adj) => (
        <div key={adj.id} className="inline-flex items-center rounded-full border overflow-hidden">
          <button
            type="button"
            onClick={() => onToggle(adj.id)}
            className={`
              inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium
              transition-colors cursor-pointer
              ${adj.enabled
                ? 'bg-blue-50 border-blue-200 text-blue-700 dark:bg-blue-950 dark:border-blue-800 dark:text-blue-300'
                : 'bg-muted/50 border-border text-muted-foreground line-through'
              }
            `}
            title={adj.reason || (adj.enabled ? 'Click to disable' : 'Click to enable')}
          >
            {adj.source === 'llm' && (
              <span className="text-[10px] opacity-60">AI</span>
            )}
            {adjustmentLabel(adj)}
          </button>
          <button
            type="button"
            onClick={() => onRemove(adj.id)}
            className="px-2 py-1 text-xs hover:text-red-500 cursor-pointer transition-colors"
            aria-label={`Remove ${adjustmentLabel(adj)} adjustment`}
          >
            &times;
          </button>
        </div>
      ))}
    </div>
  );
}
