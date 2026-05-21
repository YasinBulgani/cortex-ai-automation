"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // 5 dakika boyunca cache'i "taze" say — gereksiz refetch onle
        staleTime: 5 * 60 * 1000,
        // 30 dakika boyunca garbage-collect etme
        gcTime: 30 * 60 * 1000,
        // Pencere odaga geldiginde tekrar cek (UX icin iyi)
        refetchOnWindowFocus: true,
        // Ag kesintisinden sonra tekrar dene (3 kez, artarak)
        retry: 2,
        retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
      },
      mutations: {
        retry: 0,
      },
    },
  });
}

export function QueryProvider({ children }: { children: ReactNode }) {
  // Client-side singleton — her render'da yeni QueryClient olusturma
  const [client] = useState(makeQueryClient);
  return (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}
