'use client';

import { useRef, type ChangeEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import type { DemandMetric, ForecastConfig, ForecastMethod, TermOption } from '@/lib/types';
import { api } from '@/lib/api';
import { LLMSettings } from './LLMSettings';

interface ConfigSidebarProps {
    config: ForecastConfig;
    onConfigChange?: (config: Partial<ForecastConfig>) => void;
    onRunForecast?: () => void;
    isRunning?: boolean;
    onToggleCollapse?: () => void;
    isCollapsed?: boolean;
    termsByMethod?: Partial<Record<ForecastMethod, TermOption[]>>;
}

const TERM_OPTIONS: TermOption[] = [
    'Fall 2025', 'Winter 2026', 'Spring 2026', 'Summer 2026',
    'Fall 2026', 'Winter 2027', 'Spring 2027', 'Summer 2027',
].map((label) => ({ termCode: label, label }));

const METHOD_LABELS: Record<ForecastMethod, string> = {
    auto: 'Auto (recommended)',
    historical: 'Same-season historical',
    sequence: 'Sequence map',
};

const DEMAND_LABELS: Record<DemandMetric, string> = {
    actual: 'Actual enrollment',
    max: 'Scheduled seats / max enrollment',
    actual_plus_waitlist: 'Actual + waitlist',
};

const DEFAULT_CONFIG: ForecastConfig = {
    capacity: 20,
    progressionRate: 0.95,
    bufferPercent: 10,
    quartersToForecast: 2,
    term: 'Spring 2026',
    method: 'auto',
    demandMetric: 'actual',
};

export function ConfigSidebar({
    config,
    onConfigChange,
    onRunForecast,
    isRunning = false,
    onToggleCollapse,
    isCollapsed = false,
    termsByMethod = {},
}: ConfigSidebarProps) {
    const handleReset = () => {
        onConfigChange?.(DEFAULT_CONFIG);
    };

    const method = config.method ?? 'auto';
    // An empty array from /api/terms (fresh install, nothing imported yet) is
    // not nullish; fall through to the next non-empty list so the dropdown
    // never collapses to a single term.
    const firstNonEmpty = (...lists: (TermOption[] | undefined)[]) =>
        lists.find((l) => l && l.length > 0);
    const optionsForMethod = firstNonEmpty(termsByMethod[method], termsByMethod.auto) ?? TERM_OPTIONS;
    const termOptions = optionsForMethod.some((t) => t.label === config.term)
        ? optionsForMethod
        : [{ termCode: config.term, label: config.term }, ...optionsForMethod];

    const fileInputRef = useRef<HTMLInputElement>(null);
    const importKindRef = useRef<'master' | 'admits'>('master');

    const triggerImport = (kind: 'master' | 'admits') => {
        importKindRef.current = kind;
        fileInputRef.current?.click();
    };

    const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        e.target.value = ''; // reset so the same file can be re-selected
        if (!file) return;
        try {
            const res = await api.importDataFile(file, importKindRef.current);
            alert(`Imported ${res.kind === 'admits' ? 'admits report' : 'Master Schedule'}. Stored as ${res.stored_as}`);
        } catch (err) {
            alert(`Import failed: ${err instanceof Error ? err.message : String(err)}`);
        }
    };

    if (isCollapsed) {
        return (
            <div className="w-12 border-l border-border bg-muted/20 flex flex-col items-center py-4">
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={onToggleCollapse}
                    aria-label="Expand configuration"
                >
                    <SettingsIcon className="h-5 w-5" />
                </Button>
            </div>
        );
    }

    return (
        <div className="w-72 border-l border-border bg-muted/20 flex flex-col">
            {/* Header */}
            <div className="p-4 flex items-center justify-between">
                <h3 className="font-semibold">Configuration</h3>
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={onToggleCollapse}
                    aria-label="Collapse configuration"
                >
                    <ChevronRightIcon className="h-4 w-4" />
                </Button>
            </div>

            <Separator />

            {/* Config sections */}
            <div className="flex-1 p-4 space-y-6 overflow-y-auto">
                {/* Data */}
                <ConfigSection title="Data">
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".xlsx,.xls,.xlsm,.csv"
                        className="hidden"
                        onChange={handleFileChange}
                    />
                    <button
                        type="button"
                        onClick={() => triggerImport('master')}
                        className="w-full rounded-md border px-3 py-2 text-sm font-medium hover:bg-accent"
                    >
                        Import Master Schedule…
                    </button>
                    <button
                        type="button"
                        onClick={() => triggerImport('admits')}
                        className="w-full mt-2 rounded-md border px-3 py-2 text-sm font-medium hover:bg-accent"
                    >
                        Import Admits (optional)…
                    </button>
                </ConfigSection>

                {/* Forecast Horizon */}
                <ConfigSection title="Forecast Horizon">
                    <label htmlFor="config-method" className="text-xs text-muted-foreground mb-1 block">
                        Forecast Method
                    </label>
                    <select
                        id="config-method"
                        value={method}
                        onChange={(e) => onConfigChange?.({ method: e.target.value as ForecastMethod })}
                        className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
                    >
                        {(Object.keys(METHOD_LABELS) as ForecastMethod[]).map((key) => (
                            <option key={key} value={key}>{METHOD_LABELS[key]}</option>
                        ))}
                    </select>

                    <label htmlFor="config-term" className="text-xs text-muted-foreground mb-1 mt-3 block">
                        Forecast Term
                    </label>
                    <select
                        id="config-term"
                        value={config.term}
                        onChange={(e) => onConfigChange?.({ term: e.target.value })}
                        className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
                    >
                        {termOptions.map((t) => (
                            <option key={`${t.termCode}-${t.label}`} value={t.label}>{t.label}</option>
                        ))}
                    </select>

                    <label htmlFor="config-demand" className="text-xs text-muted-foreground mb-1 mt-3 block">
                        Planning Metric
                    </label>
                    <select
                        id="config-demand"
                        value={config.demandMetric ?? 'actual'}
                        onChange={(e) => onConfigChange?.({ demandMetric: e.target.value as DemandMetric })}
                        className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
                    >
                        {(Object.keys(DEMAND_LABELS) as DemandMetric[]).map((key) => (
                            <option key={key} value={key}>{DEMAND_LABELS[key]}</option>
                        ))}
                    </select>
                    <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                        Auto uses same-season history when available, then falls back to the sequence map.
                    </p>
                    <Button
                        type="button"
                        className="mt-3 w-full"
                        onClick={onRunForecast}
                        disabled={isRunning}
                    >
                        {isRunning ? 'Running…' : `Run Forecast`}
                    </Button>
                </ConfigSection>

                {/* Parameters */}
                <ConfigSection title="Parameters">
                    <div className="space-y-3">
                        <div>
                            <label htmlFor="config-capacity" className="text-xs text-muted-foreground mb-1 block">
                                Section Capacity
                            </label>
                            <input
                                id="config-capacity"
                                type="number"
                                min={1}
                                max={100}
                                value={config.capacity}
                                onChange={(e) => onConfigChange?.({ capacity: Math.max(1, Math.min(100, Number(e.target.value))) })}
                                className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                            />
                        </div>
                        <div>
                            <label htmlFor="config-progression" className="text-xs text-muted-foreground mb-1 block">
                                Progression Rate <span className="text-muted-foreground/70">(sequence only)</span>
                            </label>
                            <div className="flex items-center gap-2">
                                <input
                                    id="config-progression"
                                    type="range"
                                    min={0}
                                    max={100}
                                    value={Math.round(config.progressionRate * 100)}
                                    onChange={(e) => onConfigChange?.({ progressionRate: Number(e.target.value) / 100 })}
                                    className="flex-1"
                                />
                                <span className="text-sm font-medium w-12 text-right">{(config.progressionRate * 100).toFixed(0)}%</span>
                            </div>
                        </div>
                        <div>
                            <label htmlFor="config-buffer" className="text-xs text-muted-foreground mb-1 block">
                                Buffer
                            </label>
                            <div className="flex items-center gap-2">
                                <input
                                    id="config-buffer"
                                    type="range"
                                    min={0}
                                    max={100}
                                    value={config.bufferPercent}
                                    onChange={(e) => onConfigChange?.({ bufferPercent: Number(e.target.value) })}
                                    className="flex-1"
                                />
                                <span className="text-sm font-medium w-12 text-right">{config.bufferPercent}%</span>
                            </div>
                        </div>
                    </div>
                </ConfigSection>

                {/* Model Info */}
                <ConfigSection title="Model">
                    <div className="text-sm text-muted-foreground space-y-1">
                        <p>{METHOD_LABELS[method]}</p>
                        <p className="text-xs">Metric: {DEMAND_LABELS[config.demandMetric ?? 'actual']}</p>
                    </div>
                </ConfigSection>

                {/* AI Assistant */}
                <ConfigSection title="AI Assistant">
                    <LLMSettings />
                </ConfigSection>
            </div>

            <Separator />

            {/* Footer */}
            <div className="p-4">
                <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={handleReset}
                    aria-label="Reset configuration to defaults"
                >
                    Reset to Defaults
                </Button>
            </div>
        </div>
    );
}

function ConfigSection({
    title,
    children,
}: {
    title: string;
    children: React.ReactNode;
}) {
    return (
        <div>
            <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium">{title}</h4>
            </div>
            {children}
        </div>
    );
}

function SettingsIcon({ className }: { className?: string }) {
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
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
            <circle cx="12" cy="12" r="3" />
        </svg>
    );
}

function ChevronRightIcon({ className }: { className?: string }) {
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
            <path d="m9 18 6-6-6-6" />
        </svg>
    );
}
