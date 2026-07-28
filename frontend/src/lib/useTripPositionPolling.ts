import { useEffect, useRef, useState } from "react";
import { fetchTripPositions } from "./api";
import type { TripPosition } from "./types";

interface UseTripPositionPollingResult {
  latestPosition: TripPosition | null;
  positionHistory: TripPosition[];
  error: string | null;
}

export function useTripPositionPolling(
  tripId: number | undefined,
  intervalMs = 15000,
): UseTripPositionPollingResult {
  const [latestPosition, setLatestPosition] = useState<TripPosition | null>(null);
  const [positionHistory, setPositionHistory] = useState<TripPosition[]>([]);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!tripId) return;

    let cancelled = false;

    function handlePositions(res: { ok: true; positions: TripPosition[] }) {
      if (cancelled) return;
      const sorted = [...res.positions].sort(
        (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      );
      setPositionHistory(sorted);
      if (sorted.length > 0) {
        setLatestPosition(sorted[sorted.length - 1]);
      }
      setError(null);
    }

    const tid = tripId;
    function poll() {
      fetchTripPositions(tid).then(handlePositions).catch(e => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Polling failed");
      });
    }

    poll();
    intervalRef.current = setInterval(poll, intervalMs);

    return () => {
      cancelled = true;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [tripId, intervalMs]);

  return { latestPosition, positionHistory, error };
}
