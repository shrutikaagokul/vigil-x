import React, { useMemo, useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  QueueHeader,
  CapacityRow,
  QueueWorklist,
  QueuePreviewPanel,
  QueueEmptyState,
  QueueErrorState,
} from '@/components/queue';
import { getQueue } from '@/services/queueService';
import { QueueSortOption, QueueItem } from '@/types/queue';

export const QueuePage: React.FC = () => {
  const navigate = useNavigate();
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Capacity & Server Parameters
  const [generalHours, setGeneralHours] = useState<number>(40);
  const [networkHours, setNetworkHours] = useState<number>(20);
  const [horizon, setHorizon] = useState<string>('30d');
  const [sort] = useState<QueueSortOption>('priority');

  // Client Presentation Filters
  const [selectedSeverity, setSelectedSeverity] = useState<string>('');
  const [selectedRule, setSelectedRule] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Selection State
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

  // TanStack Query for Queue Data
  const {
    data: queueResponse,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['queue', { generalHours, networkHours, horizon, sort }],
    queryFn: () =>
      getQueue({
        general_hours: generalHours,
        network_hours: networkHours,
        horizon,
        sort,
      }),
  });

  // Collect available unique rule IDs
  const availableRules = useMemo(() => {
    if (!queueResponse?.items) return ['R06', 'R07', 'R08', 'R09', 'R10'];
    const rulesSet = new Set<string>();
    queueResponse.items.forEach((item) => {
      item.rules_triggered.forEach((r) => rulesSet.add(r));
    });
    return Array.from(rulesSet).sort();
  }, [queueResponse?.items]);

  // Client-side filtering & sorting
  const filteredItems: readonly QueueItem[] = useMemo(() => {
    if (!queueResponse?.items) return [];
    let items = [...queueResponse.items];

    if (selectedSeverity) {
      items = items.filter(
        (item) => item.severity.toLowerCase() === selectedSeverity.toLowerCase(),
      );
    }

    if (selectedRule) {
      items = items.filter((item) => item.rules_triggered.includes(selectedRule));
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      items = items.filter(
        (item) =>
          item.case_id.toLowerCase().includes(q) ||
          (item.name && item.name.toLowerCase().includes(q)) ||
          item.focal_provider_name.toLowerCase().includes(q) ||
          item.focal_provider_id.toLowerCase().includes(q) ||
          item.specialty.toLowerCase().includes(q) ||
          item.primary_indicator.toLowerCase().includes(q),
      );
    }

    return items;
  }, [queueResponse?.items, selectedSeverity, selectedRule, searchQuery]);

  // Client-side capacity calculations
  const totalCapacity = generalHours + networkHours;

  const { addressableCount, usedHours, totalAtRisk, addressableIds } = useMemo(() => {
    let accGen = 0;
    let accNet = 0;
    let fit = 0;
    let riskSum = 0;
    const addressableSet = new Set<string>();

    filteredItems.forEach((item) => {
      riskSum += item.exposure_high || item.est_dollars || 0;
      const effort = typeof item.effort_hours === 'number' && !isNaN(item.effort_hours) ? item.effort_hours : null;
      const pool = item.pool === 'network' || item.requires_network_specialist ? 'network' : (item.pool === 'general' ? 'general' : null);

      if (effort !== null && effort > 0 && pool !== null) {
        if (pool === 'network') {
          if (accNet + effort <= networkHours) {
            fit++;
            accNet += effort;
            addressableSet.add(item.case_id);
          }
        } else {
          if (accGen + effort <= generalHours) {
            fit++;
            accGen += effort;
            addressableSet.add(item.case_id);
          }
        }
      }
    });

    return {
      addressableCount: fit,
      usedHours: accGen + accNet,
      totalAtRisk: riskSum,
      addressableIds: addressableSet,
    };
  }, [filteredItems, generalHours, networkHours]);

  // Synchronize selection: select first item by default or if selection became invalid
  useEffect(() => {
    if (filteredItems.length > 0) {
      if (!selectedCaseId || !filteredItems.some((i) => i.case_id === selectedCaseId)) {
        setSelectedCaseId(filteredItems[0].case_id);
      }
    } else {
      setSelectedCaseId(null);
    }
  }, [filteredItems, selectedCaseId]);

  // Selected item object & rank
  const selectedIndex = useMemo(() => {
    return filteredItems.findIndex((i) => i.case_id === selectedCaseId);
  }, [filteredItems, selectedCaseId]);

  const selectedCase = useMemo(() => {
    return selectedIndex >= 0 ? filteredItems[selectedIndex] : null;
  }, [filteredItems, selectedIndex]);

  const selectedRank = selectedIndex >= 0 ? selectedIndex + 1 : 1;
  const isSelectedDeferred = selectedCase ? !addressableIds.has(selectedCase.case_id) : false;

  // Global Keyboard Navigation (ArrowUp, ArrowDown, Enter, "/")
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const activeTag = document.activeElement?.tagName.toLowerCase();
      const isInputFocused = activeTag === 'input' || activeTag === 'select' || activeTag === 'textarea';

      // Focus search with "/"
      if (e.key === '/' && !isInputFocused) {
        e.preventDefault();
        searchInputRef.current?.focus();
        return;
      }

      // Enter to open selected case
      if (e.key === 'Enter' && !isInputFocused && selectedCaseId) {
        e.preventDefault();
        navigate(`/cases/${selectedCaseId}`);
        return;
      }

      // Arrow navigation
      if (!isInputFocused && filteredItems.length > 0) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          const nextIndex = Math.min(filteredItems.length - 1, selectedIndex + 1);
          setSelectedCaseId(filteredItems[nextIndex].case_id);
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          const prevIndex = Math.max(0, selectedIndex - 1);
          setSelectedCaseId(filteredItems[prevIndex].case_id);
        }
      }
    },
    [filteredItems, selectedIndex, selectedCaseId, navigate],
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const handleClearFilters = () => {
    setSelectedSeverity('');
    setSelectedRule('');
    setSearchQuery('');
  };

  const isFiltered = Boolean(selectedSeverity || selectedRule || searchQuery.trim());

  return (
    <main className="w-full flex flex-col pb-12" role="main">
      {/* 1. Page Header */}
      <QueueHeader
        fitCount={addressableCount}
        totalAtRisk={totalAtRisk}
        horizon={horizon}
        onHorizonChange={setHorizon}
      />

      {/* 2. Capacity & Filter Row */}
      <CapacityRow
        generalHours={generalHours}
        networkHours={networkHours}
        searchQuery={searchQuery}
        selectedSeverity={selectedSeverity}
        selectedRule={selectedRule}
        availableRules={availableRules}
        searchInputRef={searchInputRef}
        onGeneralHoursChange={setGeneralHours}
        onNetworkHoursChange={setNetworkHours}
        onSearchChange={setSearchQuery}
        onSeverityChange={setSelectedSeverity}
        onRuleChange={setSelectedRule}
        onClearFilters={handleClearFilters}
      />

      {/* 3. Split View: Left Worklist + Right Preview Panel */}
      <div className="w-full px-[3rem] mt-6">
        {isError ? (
          <QueueErrorState error={error as Error} onRetry={() => refetch()} />
        ) : filteredItems.length === 0 ? (
          <QueueEmptyState isFiltered={isFiltered} onClearFilters={handleClearFilters} />
        ) : (
          <div className="flex items-start">
            {/* Left Worklist */}
            <QueueWorklist
              items={filteredItems}
              selectedCaseId={selectedCaseId}
              addressableIds={addressableIds}
              addressableCount={addressableCount}
              allocatedHours={totalCapacity}
              usedHours={usedHours}
              onSelectCase={(id) => setSelectedCaseId(id)}
            />

            {/* Right Preview Panel */}
            <QueuePreviewPanel
              selectedCase={selectedCase}
              rank={selectedRank}
              isDeferred={isSelectedDeferred}
            />
          </div>
        )}
      </div>
    </main>
  );
};
