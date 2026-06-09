/**
 * useCaseDetail hook - manages case detail state and lazy-loading
 * Related to Finding #1: Case detail lazy tabs implementation
 */
import { useState, useCallback } from "react";

export interface CaseDetail {
  id: string;
  name: string;
  description?: string;
  steps?: string[];
  expectedResult?: string;
  status?: "draft" | "review" | "approved" | "obsolete";
  createdAt?: string;
  updatedAt?: string;
  author?: string;
  assignee?: string;
  comments?: Array<{ id: string; author: string; text: string; date: string }>;
  relatedDefects?: Array<{ id: string; title: string }>;
  relatedRequirements?: Array<{ id: string; title: string }>;
  automationStatus?: "manual" | "automated" | "in_progress";
  tags?: string[];
}

export function useCaseDetail(initialCaseId?: string) {
  const [caseId, setCaseId] = useState<string | null>(initialCaseId || null);
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");

  const loadCaseDetail = useCallback(async (id: string) => {
    setLoading(true);
    try {
      // Simulate API call - replace with actual endpoint
      const response = await fetch(`/api/v1/test-cases/${id}`);
      const data = await response.json();
      setCaseId(id);
      setCaseData(data);
    } catch (error) {
      console.error("Failed to load case detail:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    caseId,
    caseData,
    loading,
    activeTab,
    setActiveTab,
    loadCaseDetail,
  };
}
