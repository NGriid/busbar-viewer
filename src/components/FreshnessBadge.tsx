import { getFreshnessColor, getFreshnessLabel, getRelativeTime, formatFullTime } from '../utils/freshness';
import type { FreshnessLevel } from '../types/dashboard';
import { useFreshnessTick } from '../hooks/useFreshnessTick';

interface FreshnessBadgeProps {
  level: FreshnessLevel;
  lastSeenAt: string;
  className?: string;
  showText?: boolean;
}

export function FreshnessBadge({ level, lastSeenAt, className = '', showText = true }: FreshnessBadgeProps) {
  // Subscribe to 1s ticks so relative time text updates automatically
  useFreshnessTick();

  const color = getFreshnessColor(level);
  const label = getFreshnessLabel(level);
  const relative = getRelativeTime(lastSeenAt);
  const full = formatFullTime(lastSeenAt);

  return (
    <div 
      className={`freshness-badge ${className}`} 
      title={`Last seen: ${full}`}
      style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
    >
      <div 
        style={{ 
          width: '8px', 
          height: '8px', 
          borderRadius: '50%', 
          backgroundColor: color,
          boxShadow: `0 0 8px ${color}`
        }} 
      />
      {showText && (
        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          {label} • {relative}
        </span>
      )}
    </div>
  );
}
