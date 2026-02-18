'use client';

import { useState, useCallback, useEffect } from 'react';
import { Adjustment } from '@/lib/adjustments';
import { api } from '@/lib/api';

// Cast API response to typed Adjustment (API returns string literals as plain strings)
function castAdjustments(raw: Array<Record<string, unknown>>): Adjustment[] {
  return raw as unknown as Adjustment[];
}

export function useAdjustments(term: string) {
  const [adjustments, setAdjustments] = useState<Adjustment[]>([]);
  const [loading, setLoading] = useState(false);

  const loadAdjustments = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getAdjustments(term);
      setAdjustments(castAdjustments(data.adjustments as unknown as Array<Record<string, unknown>>));
    } catch {
      // Adjustments are optional — if the endpoint isn't available, that's fine
      setAdjustments([]);
    } finally {
      setLoading(false);
    }
  }, [term]);

  useEffect(() => {
    if (term) {
      loadAdjustments();
    }
  }, [term, loadAdjustments]);

  const toggleAdjustment = useCallback(async (adjId: string) => {
    try {
      const data = await api.toggleAdjustment(term, adjId);
      setAdjustments(castAdjustments(data.adjustments as unknown as Array<Record<string, unknown>>));
    } catch (err) {
      console.error('Failed to toggle adjustment:', err);
    }
  }, [term]);

  const removeAdjustment = useCallback(async (adjId: string) => {
    try {
      const data = await api.removeAdjustment(term, adjId);
      setAdjustments(castAdjustments(data.adjustments as unknown as Array<Record<string, unknown>>));
    } catch (err) {
      console.error('Failed to remove adjustment:', err);
    }
  }, [term]);

  const addAdjustment = useCallback(async (adj: Omit<Adjustment, 'id' | 'enabled' | 'source'>) => {
    try {
      await api.addAdjustment(term, adj);
      await loadAdjustments();
    } catch (err) {
      console.error('Failed to add adjustment:', err);
    }
  }, [term, loadAdjustments]);

  return {
    adjustments,
    loading,
    loadAdjustments,
    toggleAdjustment,
    removeAdjustment,
    addAdjustment,
    activeCount: adjustments.filter(a => a.enabled).length,
  };
}
