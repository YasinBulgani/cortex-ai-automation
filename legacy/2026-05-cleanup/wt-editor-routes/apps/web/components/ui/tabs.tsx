"use client";

import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

type TabsVariant = "underline" | "pill";

interface TabsContextValue {
  variant: TabsVariant;
}

const TabsCtx = React.createContext<TabsContextValue>({ variant: "underline" });

export const Tabs = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Root> & { variant?: TabsVariant }
>(({ variant = "underline", ...props }, ref) => (
  <TabsCtx.Provider value={{ variant }}>
    <TabsPrimitive.Root ref={ref} {...props} />
  </TabsCtx.Provider>
));
Tabs.displayName = "Tabs";

export const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => {
  const { variant } = React.useContext(TabsCtx);
  return (
    <TabsPrimitive.List
      ref={ref}
      className={cn(
        variant === "pill"
          ? "inline-flex items-center gap-1 rounded-full border border-slate-700 bg-slate-900 p-1"
          : "inline-flex h-9 items-center gap-1 rounded-lg border border-slate-800 bg-slate-900/40 p-1",
        className
      )}
      {...props}
    />
  );
});
TabsList.displayName = TabsPrimitive.List.displayName;

export const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => {
  const { variant } = React.useContext(TabsCtx);
  return (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap text-sm font-medium text-slate-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:pointer-events-none disabled:opacity-50",
        variant === "pill"
          ? "rounded-full px-4 py-1.5 hover:text-white data-[state=active]:bg-blue-600 data-[state=active]:text-white"
          : "rounded px-3 py-1.5 hover:text-white data-[state=active]:bg-slate-900 data-[state=active]:text-white data-[state=active]:shadow-sm",
        className
      )}
      {...props}
    />
  );
});
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

export const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn("mt-4 focus-visible:outline-none", className)}
    {...props}
  />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;
