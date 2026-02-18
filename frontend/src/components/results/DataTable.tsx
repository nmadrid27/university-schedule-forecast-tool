'use client';

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

export function DataTable({ data }: DataTableProps) {
    return (
        <div className="rounded-lg border border-border overflow-hidden">
            <Table>
                <TableHeader>
                    <TableRow className="bg-muted/50">
                        <TableHead className="font-semibold">Course</TableHead>
                        <TableHead className="font-semibold">Campus</TableHead>
                        <TableHead className="text-right font-semibold">Projected</TableHead>
                        <TableHead className="text-right font-semibold">Sections</TableHead>
                        <TableHead className="text-right font-semibold">Change</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {data.map((row, index) => (
                        <TableRow key={`${row.course}-${row.campus}-${index}`}>
                            <TableCell className="font-medium">
                                <span className="inline-flex items-center gap-1.5">
                                    {row.adjusted && (
                                        <span className="h-2 w-2 rounded-full bg-blue-500 shrink-0" title="Adjusted" />
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
                                                ? 'text-green-500'
                                                : row.changePercent < 0
                                                    ? 'text-red-500'
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
