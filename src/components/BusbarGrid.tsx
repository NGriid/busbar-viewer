import { useDashboardStore } from '../store/dashboardStore';
import { BusbarCard } from './BusbarCard';
import { getFreshnessLevel } from '../utils/freshness';

export function BusbarGrid() {
  const busbarsById = useDashboardStore((s) => s.busbarsById);
  const ui = useDashboardStore((s) => s.ui);
  const setSearchQuery = useDashboardStore((s) => s.setSearchQuery);
  const setFilterMode = useDashboardStore((s) => s.setFilterMode);
  const setSortMode = useDashboardStore((s) => s.setSortMode);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  const handleFilter = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setFilterMode(e.target.value as typeof ui.filterMode);
  };

  const handleSort = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSortMode(e.target.value as typeof ui.sortMode);
  };

  let busbars = Object.values(busbarsById);

  // Search
  if (ui.searchQuery) {
    const q = ui.searchQuery.toLowerCase();
    busbars = busbars.filter(b => b.deviceId.toLowerCase().includes(q));
  }

  // Filter
  if (ui.filterMode !== 'all') {
    busbars = busbars.filter(b => {
      const freshness = getFreshnessLevel(b.lastSeenAt);
      if (ui.filterMode === 'stale') return freshness === 'stale' || freshness === 'offline';
      if (ui.filterMode === 'error') return (b.errorFlags && b.errorFlags > 0);
      // overloaded needs matching from terminal state; we simplify and handle overloaded inside terminal cards directly, or we can fetch terminals. Let's do a simple check.
      if (ui.filterMode === 'overloaded') {
        const terminals = useDashboardStore.getState().terminalsByBusbarId[b.deviceId];
        if (!terminals) return false;
        return Object.values(terminals).some(t => t.overloadStatus === 1);
      }
      return true;
    });
  }

  // Sort
  busbars.sort((a, b) => {
    if (ui.sortMode === 'id') return a.deviceId.localeCompare(b.deviceId);
    if (ui.sortMode === 'lastSeen') return new Date(b.lastSeenAt).getTime() - new Date(a.lastSeenAt).getTime();
    if (ui.sortMode === 'overloadCount') {
       // Just sort by error flags for now if no full terminal link.
       const tA = useDashboardStore.getState().terminalsByBusbarId[a.deviceId];
       const tB = useDashboardStore.getState().terminalsByBusbarId[b.deviceId];
       const overA = tA ? Object.values(tA).filter(t => t.overloadStatus === 1).length : 0;
       const overB = tB ? Object.values(tB).filter(t => t.overloadStatus === 1).length : 0;
       return overB - overA;
    }
    return 0;
  });

  return (
    <div className="busbar-grid-section">
      <div className="busbar-grid-controls">
        <input 
          type="text" 
          placeholder="Search by ID..."
          value={ui.searchQuery}
          onChange={handleSearch}
        />
        <select value={ui.filterMode} onChange={handleFilter}>
          <option value="all">All Devices</option>
          <option value="stale">Stale / Offline</option>
          <option value="overloaded">Overloaded</option>
          <option value="error">Errors</option>
        </select>
        <select value={ui.sortMode} onChange={handleSort}>
          <option value="id">Sort by ID</option>
          <option value="lastSeen">Sort by Last Seen</option>
          <option value="overloadCount">Sort by Overloads</option>
        </select>
      </div>

      {busbars.length === 0 ? (
        <div className="empty-state">No busbars match the current filters.</div>
      ) : (
        <div className="busbar-grid">
          {busbars.map(b => <BusbarCard key={b.deviceId} busbar={b} />)}
        </div>
      )}
    </div>
  );
}
