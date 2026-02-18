'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';

interface LLMStatus {
  provider: string;
  model: string | null;
  base_url: string | null;
  has_key: boolean;
  configured: boolean;
}

const PROVIDERS = [
  { value: 'none', label: 'None (regex only)' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'ollama', label: 'Ollama (local)' },
  { value: 'custom', label: 'Custom endpoint' },
];

const DEFAULT_MODELS: Record<string, string> = {
  openai: 'gpt-4o-mini',
  anthropic: 'claude-sonnet-4-5-20250514',
  ollama: 'llama3.2',
  custom: 'gpt-4o-mini',
};

export function LLMSettings() {
  const [status, setStatus] = useState<LLMStatus | null>(null);
  const [provider, setProvider] = useState('none');
  const [model, setModel] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const loadStatus = useCallback(async () => {
    try {
      const s = await api.getLLMStatus();
      setStatus(s);
      setProvider(s.provider || 'none');
      setModel(s.model || '');
      setBaseUrl(s.base_url || '');
    } catch {
      // LLM endpoints may not exist on older backends
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      await api.updateLLMConfig({
        provider,
        model: model || DEFAULT_MODELS[provider] || null,
        base_url: baseUrl || null,
        api_key: apiKey || undefined,
      });
      setApiKey(''); // Clear after save
      await loadStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const needsKey = provider !== 'none' && provider !== 'ollama';
  const needsUrl = provider === 'ollama' || provider === 'custom';

  return (
    <div className="space-y-3">
      {/* Status indicator */}
      <div className="flex items-center gap-2">
        <div
          className={`h-2 w-2 rounded-full ${
            status?.configured ? 'bg-green-500' : 'bg-muted-foreground/30'
          }`}
        />
        <span className="text-xs text-muted-foreground">
          {status?.configured ? `Connected (${status.provider})` : 'Not configured'}
        </span>
      </div>

      {/* Provider select */}
      <div>
        <label className="text-xs text-muted-foreground mb-1 block">Provider</label>
        <select
          value={provider}
          onChange={(e) => {
            setProvider(e.target.value);
            setModel(DEFAULT_MODELS[e.target.value] || '');
            if (e.target.value === 'ollama') {
              setBaseUrl('http://localhost:11434/v1');
            } else {
              setBaseUrl('');
            }
          }}
          className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        >
          {PROVIDERS.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
      </div>

      {/* Model */}
      {provider !== 'none' && (
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Model</label>
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder={DEFAULT_MODELS[provider] || 'model-name'}
            className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
      )}

      {/* Base URL */}
      {needsUrl && (
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Base URL</label>
          <input
            type="text"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="http://localhost:11434/v1"
            className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
      )}

      {/* API Key */}
      {needsKey && (
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">
            API Key {status?.has_key && <span className="text-green-500">(saved)</span>}
          </label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={status?.has_key ? '••••••••' : 'sk-...'}
            className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <p className="text-[10px] text-muted-foreground mt-1">
            Stored locally in .env.local, never committed to git.
          </p>
        </div>
      )}

      {error && (
        <p className="text-xs text-red-500">{error}</p>
      )}

      {/* Save button */}
      {provider !== 'none' && (
        <Button
          variant="outline"
          size="sm"
          className="w-full"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save Configuration'}
        </Button>
      )}

      {/* Disable LLM button if currently configured */}
      {provider === 'none' && status?.configured && (
        <Button
          variant="outline"
          size="sm"
          className="w-full"
          onClick={async () => {
            await api.updateLLMConfig({ provider: 'none' });
            await loadStatus();
          }}
        >
          Disable AI Assistant
        </Button>
      )}
    </div>
  );
}
