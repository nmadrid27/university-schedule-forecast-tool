'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { ChatWindow } from '@/components/chat';
import { ResultsPanel } from '@/components/results';
import { HistorySidebar, ConfigSidebar } from '@/components/sidebar';
import { useChat } from '@/hooks/useChat';
import { useAdjustments } from '@/hooks/useAdjustments';
import { ForecastConfig } from '@/lib/types';
import { api } from '@/lib/api';

export default function Home() {
  const [config, setConfig] = useState<ForecastConfig>({
    capacity: 20,
    progressionRate: 0.95,
    bufferPercent: 10,
    quartersToForecast: 2,
    term: 'Spring 2026',
  });

  const { messages, isLoading, sendMessage, runForecast, clearMessages, forecastResults, forecastSummary, lastAdjustmentChange } = useChat(config);
  const { adjustments, toggleAdjustment, removeAdjustment, loadAdjustments } = useAdjustments(config.term);

  const [showConfig, setShowConfig] = useState(true);
  const initialLoadDone = useRef(false);
  const configSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load config from backend on mount so frontend and disk stay in sync
  useEffect(() => {
    api.getConfig()
      .then((diskConfig) => {
        setConfig((prev) => ({
          ...prev,
          capacity: diskConfig.capacity,
          progressionRate: diskConfig.progressionRate,
          bufferPercent: diskConfig.bufferPercent,
          quartersToForecast: diskConfig.quartersToForecast,
        }));
      })
      .catch(() => {
        // Backend not running — keep hardcoded defaults
      })
      .finally(() => {
        initialLoadDone.current = true;
      });
  }, []);

  // Persist config changes to disk (debounced, skips initial load)
  useEffect(() => {
    if (!initialLoadDone.current) return;
    if (configSaveTimer.current) clearTimeout(configSaveTimer.current);
    configSaveTimer.current = setTimeout(() => {
      api.updateConfig({
        capacity: config.capacity,
        progressionRate: config.progressionRate,
        bufferPercent: config.bufferPercent,
        quartersToForecast: config.quartersToForecast,
        defaultTerm: config.term,
      }).catch(() => {});
    }, 500);
    return () => {
      if (configSaveTimer.current) clearTimeout(configSaveTimer.current);
    };
  }, [config.capacity, config.progressionRate, config.bufferPercent, config.quartersToForecast, config.term]);

  // Reload adjustments when LLM extracts new ones via chat
  useEffect(() => {
    if (lastAdjustmentChange > 0) {
      loadAdjustments();
    }
  }, [lastAdjustmentChange, loadAdjustments]);

  const handleConfigChange = useCallback((partial: Partial<ForecastConfig>) => {
    setConfig((prev) => ({ ...prev, ...partial }));
  }, []);

  const handleNewChat = () => {
    clearMessages();
  };

  const handleDownload = useCallback(() => {
    if (!forecastResults) return;
    // Create CSV content
    const headers = ['Course', 'Campus', 'Projected Seats', 'Sections', 'Change %'];
    const rows = forecastResults.map(r => [
      r.course,
      r.campus,
      r.projectedSeats.toString(),
      r.sections.toString(),
      r.changePercent !== undefined ? `${r.changePercent}%` : 'N/A'
    ]);
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');

    // Create download link
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `forecast_${config.term.replace(/\s+/g, '_').toLowerCase()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [forecastResults, config.term]);

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Left Sidebar - History (hidden on small screens via component className) */}
      <HistorySidebar onNewChat={handleNewChat} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col md:flex-row min-w-0">
        {/* Chat Panel */}
        <div className="md:w-[40%] md:min-w-[320px] h-1/2 md:h-full border-b md:border-b-0 md:border-r border-border">
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            onSendMessage={sendMessage}
          />
        </div>

        {/* Results Panel */}
        <div className="flex-1 min-w-0 h-1/2 md:h-full">
          <ResultsPanel
            results={forecastResults}
            summary={forecastSummary}
            onDownload={forecastResults ? handleDownload : undefined}
            adjustments={adjustments}
            onToggleAdjustment={toggleAdjustment}
            onRemoveAdjustment={removeAdjustment}
          />
        </div>
      </div>

      {/* Right Sidebar - Config */}
      <ConfigSidebar
        config={config}
        onConfigChange={handleConfigChange}
        onRunForecast={() => runForecast(config.term)}
        isRunning={isLoading}
        onToggleCollapse={() => setShowConfig((prev) => !prev)}
        isCollapsed={!showConfig}
      />
    </div>
  );
}
