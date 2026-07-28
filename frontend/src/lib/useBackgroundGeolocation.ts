import { useEffect, useRef, useState } from "react";
import { reportTripPosition } from "./api";

interface GeoState {
  isWatching: boolean;
  currentPosition: { lat: number; lon: number; accuracy: number } | null;
  error: string | null;
  positionCount: number;
}

interface UseBackgroundGeolocationOptions {
  tripId: number | undefined;
  enabled?: boolean;
}

export function useBackgroundGeolocation({
  tripId,
  enabled = false,
}: UseBackgroundGeolocationOptions) {
  const [state, setState] = useState<GeoState>({
    isWatching: false,
    currentPosition: null,
    error: navigator.geolocation ? null : "Geolocation not supported",
    positionCount: 0,
  });
  const watchIdRef = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled || !tripId) {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
      return;
    }

    if (!navigator.geolocation) return;

    let cancelled = false;

    const id = navigator.geolocation.watchPosition(
      (pos) => {
        if (cancelled) return;
        const data = {
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
          source: "gps" as const,
        };

        setState(prev => ({
          ...prev,
          isWatching: true,
          currentPosition: { lat: data.lat, lon: data.lon, accuracy: data.accuracy ?? 0 },
          error: null,
          positionCount: prev.positionCount + 1,
        }));

        reportTripPosition(tripId, data).catch(() => {
          const queue = JSON.parse(localStorage.getItem("offline_queue") || "[]");
          queue.push({ type: "position", data: { tripId, ...data, timestamp: new Date().toISOString() } });
          localStorage.setItem("offline_queue", JSON.stringify(queue));
        });
      },
      (err) => {
        if (cancelled) return;
        setState(prev => ({ ...prev, error: err.message }));
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 30000 },
    );

    watchIdRef.current = id;

    return () => {
      cancelled = true;
      navigator.geolocation.clearWatch(id);
      watchIdRef.current = null;
    };
  }, [enabled, tripId]);

  return state;
}
