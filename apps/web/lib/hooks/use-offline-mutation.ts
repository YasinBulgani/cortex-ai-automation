/**
 * useOfflineMutation — Handle mutations offline with background sync
 *
 * Usage:
 *   const { mutate, isPending, isQueued } = useOfflineMutation({
 *     mutationFn: (data) => api.patch('/items/1', data),
 *   });
 */

import { useCallback, useEffect, useState } from "react";
import {
  isOnline,
  onOnline,
  onOffline,
  queueOfflineMutation,
  getQueuedMutations,
  removeQueuedMutation,
  requestBackgroundSync,
} from "@/lib/pwa";
import { apiClient } from "@/lib/api-client";

export interface UseOfflineMutationOptions<TData = unknown> {
  mutationFn: (data: TData) => Promise<unknown>;
  onSuccess?: (data: unknown) => void;
  onError?: (error: Error) => void;
  onQueuedSuccess?: (queuedCount: number) => void;
}

export interface UseOfflineMutationResult<TData> {
  mutate: (data: TData) => Promise<void>;
  isPending: boolean;
  isQueued: boolean;
  queuedCount: number;
}

/**
 * Hook for handling mutations with offline support
 */
export function useOfflineMutation<TData = unknown>(
  options: UseOfflineMutationOptions<TData>
): UseOfflineMutationResult<TData> {
  const [isPending, setIsPending] = useState(false);
  const [isQueued, setIsQueued] = useState(false);
  const [queuedCount, setQueuedCount] = useState(0);

  // Check queued items on mount
  useEffect(() => {
    getQueuedMutations().then((items) => {
      setQueuedCount(items.length);
      setIsQueued(items.length > 0);
    });
  }, []);

  // Sync queued mutations when coming online
  useEffect(() => {
    const unsubscribe = onOnline(async () => {
      const items = await getQueuedMutations();
      if (items.length === 0) return;

      setIsPending(true);
      let syncedCount = 0;

      for (const item of items) {
        try {
          const response = await fetch(item.url, {
            method: item.method,
            headers: {
              "Content-Type": "application/json",
              ...item.headers,
            },
            body: item.body,
          });

          if (response.ok) {
            await removeQueuedMutation(item.id!);
            syncedCount++;
          }
        } catch (err) {
          console.error("Failed to sync queued mutation:", err);
        }
      }

      if (syncedCount > 0) {
        options.onQueuedSuccess?.(syncedCount);
        const remaining = await getQueuedMutations();
        setQueuedCount(remaining.length);
        setIsQueued(remaining.length > 0);
      }

      setIsPending(false);
    });

    return unsubscribe;
  }, [options]);

  const mutate = useCallback(
    async (data: TData) => {
      setIsPending(true);

      try {
        // Try to execute immediately
        if (isOnline()) {
          const result = await options.mutationFn(data);
          options.onSuccess?.(result);
          setIsPending(false);
          return;
        }

        // Queue for later if offline
        const body = JSON.stringify(data);
        await queueOfflineMutation("/api/v1/mutation", "POST", body, {
          "Content-Type": "application/json",
        });

        const items = await getQueuedMutations();
        setQueuedCount(items.length);
        setIsQueued(true);

        // Request background sync
        try {
          await requestBackgroundSync("sync-mutations");
        } catch (err) {
          console.error("Background sync registration failed:", err);
        }

        setIsPending(false);
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        options.onError?.(error);
        setIsPending(false);
        throw error;
      }
    },
    [options]
  );

  return {
    mutate,
    isPending,
    isQueued,
    queuedCount,
  };
}
