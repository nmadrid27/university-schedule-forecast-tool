'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MetricsCards } from './MetricsCards';
import { DataTable } from './DataTable';
import { AdjustmentBadges } from './AdjustmentBadges';
import { ForecastResult, ForecastSummary } from '@/lib/types';
import { Adjustment } from '@/lib/adjustments';

interface ResultsPanelProps {
    results: ForecastResult[] | null;
    summary: ForecastSummary | null;
    onDownload?: () => void;
    onCompare?: () => void;
    adjustments?: Adjustment[];
    onToggleAdjustment?: (id: string) => void;
    onRemoveAdjustment?: (id: string) => void;
}

export function ResultsPanel({
    results,
    summary,
    onDownload,
    onCompare,
    adjustments = [],
    onToggleAdjustment,
    onRemoveAdjustment,
}: ResultsPanelProps) {
    // Empty state
    if (!results || !summary) {
        return (
            <div className="flex flex-col h-full">
                <div className="border-b border-border p-4">
                    <h2 className="text-lg font-semibold">Forecast Results</h2>
                    <p className="text-sm text-muted-foreground">
                        Results will appear here after running a forecast
                    </p>
                </div>
                <div className="flex-1 flex items-center justify-center p-8">
                    <div className="text-center max-w-sm">
                        <div className="text-6xl mb-4">📊</div>
                        <h3 className="text-lg font-medium mb-2">No Forecast Yet</h3>
                        <p className="text-sm text-muted-foreground">
                            Ask me to &quot;Forecast a term&quot; or select one from the sidebar to see enrollment projections here.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    // Format last updated
    const lastUpdated = summary.lastUpdated.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
    });

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="border-b border-border p-4">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-lg font-semibold">Forecast Results</h2>
                        <p className="text-sm text-muted-foreground">
                            {summary.method} • Updated {lastUpdated}
                            {summary.adjustmentsApplied ? ` • ${summary.adjustmentsApplied} adjustment${summary.adjustmentsApplied > 1 ? 's' : ''} applied` : ''}
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={onDownload} disabled={!onDownload}>
                            <DownloadIcon className="h-4 w-4 mr-1" />
                            CSV
                        </Button>
                        <Button variant="outline" size="sm" onClick={onCompare} disabled={!onCompare}>
                            Compare
                        </Button>
                    </div>
                </div>
            </div>

            {/* Content */}
            <ScrollArea className="flex-1 p-4">
                {/* Adjustment Badges */}
                {adjustments.length > 0 && onToggleAdjustment && onRemoveAdjustment && (
                    <AdjustmentBadges
                        adjustments={adjustments}
                        onToggle={onToggleAdjustment}
                        onRemove={onRemoveAdjustment}
                    />
                )}

                {/* Metrics */}
                <MetricsCards summary={summary} />

                <Separator className="my-4" />

                {/* Data Table */}
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-base">
                            Course Projections ({results.length} courses)
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-0">
                        <DataTable data={results} />
                    </CardContent>
                </Card>

                {/* Source info */}
                <p className="text-xs text-muted-foreground mt-4 text-center">
                    Source: Enrollment Data • Model: {summary.method} •
                    Courses: {summary.coursesForecasted}
                </p>
            </ScrollArea>
        </div>
    );
}

function DownloadIcon({ className }: { className?: string }) {
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
        >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" x2="12" y1="15" y2="3" />
        </svg>
    );
}
