import { useEffect } from 'react';
import { useDashboardStore } from '../store/dashboardStore';
import { useIoTConnection } from './useIoTConnection';

/**
 * Hook to automatically connect the IoT service on mount
 * and feed messages into the Zustand store.
 * Also handles disconnecting on unmount.
 * @param autoReconnect If true, forces a connection when idle.
 */
export function useAutoConnect(autoReconnect = true) {
  const { connect, disconnect, connectionState, error } = useIoTConnection();
  
  useEffect(() => {
    // If IoT connection has an error, push it to Zustand
    if (error) {
      useDashboardStore.setState({ error });
    }
  }, [error]);

  useEffect(() => {
    if (autoReconnect && (connectionState === 'idle' || connectionState === 'disconnected')) {
      connect();
    } else if (!autoReconnect && connectionState === 'connected') {
      disconnect();
    }
  }, [autoReconnect, connectionState, connect, disconnect]);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);
}
