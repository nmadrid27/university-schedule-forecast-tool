'use client';

import { useState, useMemo } from 'react';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { ForecastResult } from '@/lib/types';

interface DataTableProps {
    data: ForecastResult[];
}

type SortKey = 'course' | 'campus' | 'projectedSeats' | 'sections' | 'changePercent';
type SortDirection = 'asc' | 'desc';

export function DataTable({ data }: DataTableProps) {
    const [sortKey, setSortKey] = useState<SortKey | null>(null);
    const [sortDir, setSortDir] = useState<SortDirection>('asc');

    const handleSort = (key: SortKey) => {
        if (sortKey === key) {
            setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
        } else {
            setSortKey(key);
            setSortDir('asc');
        }
    };

    const sorted = useMemo(() => {
        if (!sortKey) return data;
        return [...data].sort((a, b) => {
            const av = a[sortKey] ?? 0;
            const bv = b[sortKey] ?? 0;
            if (typeof av === 'string' && typeof bv === 'string') {
                return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
            }
            const na = typeof av === 'number' ? av : 0;
            const nb = typeof bv === 'number' ? bv : 0;
            return sortDir === 'asc' ? na - nb : nb - na;
        });
    }, [data, sortKey, sortDir]);

    const sortIndicator = (key: SortKey) => {
        if (sortKey !== key) return null;
        return <span aria-hidden="true" className="ml-1">{sortDir === 'asc' ? '\u2191' : '\u2193'}</span>;
    };

    return (
        <div className="rounded-lg border border-border overflow-hidden">
            <Table>
                <TableHeader>
                    <TableRow className="bg-muted/50">
                        <TableHead>
                            <button type="button" onClick={() => handleSort('course')} className="font-semibold cursor-pointer inline-flex items-center hover:text-foreground transition-colors">
                                Course{sortIndicator('course')}
                            </button>
                        </TableHead>
                        <TableHead>
                            <button type="button" onClick={() => handleSort('campus')} className="font-semibold cursor-pointer inline-flex items-center hover:text-foreground transition-colors">
                                Campus{sortIndicator('campus')}
                            </button>
                        </TableHead>
                        <TableHead className="text-right">
                            <button type="button" onClick={() => handleSort('projectedSeats')} className="font-semibold cursor-pointer inline-flex items-center ml-auto hover:text-foreground transition-colors">
                                Projected{sortIndicator('projectedSeats')}
                            </button>
                        </TableHead>
                        <TableHead className="text-right">
                            <button type="button" onClick={() => handleSort('sections')} className="font-semibold cursor-pointer inline-flex items-center ml-auto hover:text-foreground transition-colors">
                                Sections{sortIndicator('sections')}
                            </button>
                        </TableHead>
                        <TableHead className="text-right">
                            <button type="button" onClick={() => handleSort('changePercent')} className="font-semibold cursor-pointer inline-flex items-center ml-auto hover:text-foreground transition-colors">
                                Change{sortIndicator('changePercent')}
                            </button>
                        </TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {sorted.map((row, index) => (
                        <TableRow key={`${row.course}-${row.campus}-${index}`}>
                            <TableCell className="font-medium">
                                <span className="inline-flex items-center gap-1.5">
                                    {row.adjusted && (
                                        <span
                                            className="h-2 w-2 rounded-full bg-blue-500 shrink-0"
                                            title="Adjusted"
                                            role="img"
                                            aria-label="This row has been adjusted"
                                        />
                                    )}
                                    {row.course}
                                </span>
                            </TableCell>
                            <TableCell className="text-muted-foreground">{row.campus}</TableCell>
                            <TableCell className="text-right">{Math.round(row.projectedSeats)}</TableCell>
                            <TableCell className="text-right">{row.sections}</TableCell>
                            <TableCell className="text-right">
                                {row.changePercent !== undefined ? (
                                    <span
                                        className={
                                            row.changePercent > 0
                                                ? 'text-green-600 dark:text-green-400'
                                                : row.changePercent < 0
                                                    ? 'text-red-600 dark:text-red-400'
                                                    : 'text-muted-foreground'
                                        }
                                    >
                                        {row.changePercent > 0 ? '+' : ''}
                                        {row.changePercent}%
                                    </span>
                                ) : (
                                    <span className="text-muted-foreground">—</span>
                                )}
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    );
}
