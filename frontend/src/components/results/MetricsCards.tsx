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
            value: summary.totalStudents.toLocaleString(),
            icon: '👥',
            trend: '+5%',
            trendUp: true,
        },
        {
            label: 'Sections',
            value: summary.totalSections.toString(),
            icon: '📚',
            trend: '+3',
            trendUp: true,
        },
        {
            label: 'Accuracy',
            value: `${summary.accuracy || 94}%`,
            icon: '🎯',
            trend: null,
            trendUp: null,
        },
    ];

    return (
        <div className="grid grid-cols-3 gap-4 mb-6">
            {metrics.map((metric) => (
                <Card key={metric.label} className="bg-muted/30">
                    <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                            <span className="text-2xl">{metric.icon}</span>
                            {metric.trend && (
                                <span
                                    className={`text-xs font-medium ${metric.trendUp ? 'text-green-500' : 'text-red-500'
                                        }`}
                                >
                                    {metric.trendUp ? '↑' : '↓'} {metric.trend}
                                </span>
                            )}
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
