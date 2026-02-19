'use client';

import { Card, CardContent } from '@/components/ui/card';
import { ForecastSummary } from '@/lib/types';

interface MetricsCardsProps {
    summary: ForecastSummary;
}

export function MetricsCards({ summary }: MetricsCardsProps) {
    const metrics = [
        {
            label: 'Total Students',
            value: Math.round(summary.totalStudents).toLocaleString(),
            icon: <UsersIcon className="h-6 w-6 text-muted-foreground" />,
        },
        {
            label: 'Sections',
            value: summary.totalSections.toString(),
            icon: <LayersIcon className="h-6 w-6 text-muted-foreground" />,
        },
        {
            label: 'Courses Forecasted',
            value: summary.coursesForecasted.toString(),
            icon: <BarChartIcon className="h-6 w-6 text-muted-foreground" />,
        },
    ];

    return (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            {metrics.map((metric) => (
                <Card key={metric.label} className="bg-muted/30">
                    <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                            {metric.icon}
                        </div>
                        <div className="mt-2">
                            <p className="text-2xl font-bold">{metric.value}</p>
                            <p className="text-xs text-muted-foreground">{metric.label}</p>
                        </div>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
}

function UsersIcon({ className }: { className?: string }) {
    return (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
    );
}

function LayersIcon({ className }: { className?: string }) {
    return (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
            <path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z" />
            <path d="m22.4 10.08-8.58 3.91a2 2 0 0 1-1.66 0l-8.58-3.9" />
            <path d="m22.4 14.08-8.58 3.91a2 2 0 0 1-1.66 0l-8.58-3.9" />
        </svg>
    );
}

function BarChartIcon({ className }: { className?: string }) {
    return (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
            <line x1="12" x2="12" y1="20" y2="10" />
            <line x1="18" x2="18" y1="20" y2="4" />
            <line x1="6" x2="6" y1="20" y2="16" />
        </svg>
    );
}
