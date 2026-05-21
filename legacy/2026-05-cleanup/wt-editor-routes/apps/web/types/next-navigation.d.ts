import "next/navigation";

declare module "next/navigation" {
  export function useParams<
    T extends Record<string, string | string[]> = Record<string, string | string[]>,
  >(): T;
}

export {};
