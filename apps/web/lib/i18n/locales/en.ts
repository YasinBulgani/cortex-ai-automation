/**
 * English translations.
 * Must match the shape of `tr.ts` (TranslationDictionary).
 */
import type { TranslationDictionary } from "./tr";

export const en: TranslationDictionary = {
  // ── Common ────────────────────────────────────────────────────────────────
  common: {
    save: "Save",
    cancel: "Cancel",
    delete: "Delete",
    edit: "Edit",
    create: "Create",
    close: "Close",
    confirm: "Confirm",
    search: "Search",
    filter: "Filter",
    all: "All",
    loading: "Loading…",
    saving: "Saving…",
    noData: "No data found.",
    error: "An error occurred.",
    success: "Operation successful.",
    add: "Add",
    remove: "Remove",
    view: "View",
    back: "Back",
    next: "Next",
    previous: "Previous",
    submit: "Submit",
    reset: "Reset",
    upload: "Upload",
    download: "Download",
    export: "Export",
    import: "Import",
    refresh: "Refresh",
    settings: "Settings",
    help: "Help",
    logout: "Log Out",
    login: "Log In",
    language: "Language",
    status: "Status",
    actions: "Actions",
    name: "Name",
    description: "Description",
    createdAt: "Created At",
    updatedAt: "Updated At",
    optional: "optional",
    required: "required",
    total: "Total",
    yes: "Yes",
    no: "No",
    unknown: "Unknown",
  },

  // ── Navigation ────────────────────────────────────────────────────────────
  nav: {
    dashboard: "Dashboard",
    projects: "Projects",
    automation: "Automation",
    management: "Test Management",
    settings: "Settings",
    profile: "Profile",
  },

  // ── Auth ──────────────────────────────────────────────────────────────────
  auth: {
    email: "Email",
    password: "Password",
    forgotPassword: "Forgot password",
    signIn: "Sign In",
    signOut: "Sign Out",
    invalidCredentials: "Invalid email or password.",
    sessionExpired: "Your session has expired. Please sign in again.",
  },

  // ── Test Management ───────────────────────────────────────────────────────
  management: {
    title: "Test Management",
    projects: "Projects",
    caseList: "Test Cases",
    suites: "Test Suites",
    runList: "Test Runs",
    plans: "Test Plans",
    requirementList: "Requirements",
    defects: "Defects",
    importExport: "Import / Export",

    // Dashboard
    dashboard: {
      title: "Management Dashboard",
      totalCases: "Total Cases",
      activeCases: "Active",
      passRate: "Pass Rate",
      blocked: "Blocked",
      releaseReadiness: "Release Readiness",
      runBreakdown: "Run Breakdown",
    },

    // Status labels
    status: {
      draft: "Draft",
      active: "Active",
      archived: "Archived",
      not_run: "Not Run",
      running: "Running",
      passed: "Passed",
      failed: "Failed",
      blocked: "Blocked",
      skipped: "Skipped",
      not_covered: "Not Covered",
      covered: "Covered",
      partial: "Partial",
      stale: "Stale",
    },

    // Cases
    cases: {
      create: "Create Case",
      title: "Title",
      key: "Key",
      priority: "Priority",
      type: "Type",
      automationStatus: "Automation Status",
      steps: "Steps",
      preconditions: "Preconditions",
      objective: "Objective",
      tags: "Tags",
      archive: "Archive",
      archived: "Archived",
    },

    // Runs
    runs: {
      execute: "Execute",
      stepResult: "Step Result",
      actualResult: "Actual Result",
      executionNotes: "Notes",
      evidence: "Upload Evidence",
      start: "Start Run",
      complete: "Complete Run",
    },

    // Requirements
    requirements: {
      matrix: "Traceability Matrix",
      key: "Requirement Key",
      source: "Source",
      coverage: "Coverage",
      cases: "Cases",
      linkRequirement: "Link Requirement",
      externalKey: "External Key",
      titleSnapshot: "Requirement Title",
      url: "URL",
      externalSource: "Source",
      noLinked: "No test cases linked to this requirement.",
      noRequirements: "No requirement links yet.",
      noResults: "No requirements match the current filter.",
    },

    // Import
    import: {
      dropzone: "Drag a CSV or JSON file here",
      orClick: "or click",
      fileAccepted: "File accepted",
      stagingPreview: "Staging Preview",
      commit: "Commit",
      committing: "Committing…",
      conflict: "Conflict",
      ready: "Ready",
      invalid: "Invalid",
      duplicate: "Possible Duplicate",
    },
  },

  // ── Automation ────────────────────────────────────────────────────────────
  automation: {
    monkey: "Monkey Test",
    mobile: "Mobile Automation",
    apiTesting: "API Testing",
    playwright: "Playwright Console",
    locators: "Locator Lab",
    recorder: "Recorder",
  },

  // ── Errors ────────────────────────────────────────────────────────────────
  errors: {
    notFound: "Page not found.",
    forbidden: "You do not have permission to access this page.",
    serverError: "Server error. Please try again later.",
    networkError: "Network error. Please check your connection.",
    validationError: "Please fill in all required fields.",
    uploadFailed: "File upload failed.",
    saveFailed: "Save failed.",
  },
};
