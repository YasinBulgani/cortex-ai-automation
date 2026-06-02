"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  useArchiveManagementCase,
  useManagementCase,
  useManagementCaseVersions,
  useManagementRequirements,
  useUpdateManagementCase,
} from "@/lib/hooks/use-management";

import { ManagementPanel, ManagementShell, ManagementStat } from "../../_components/ManagementShell";
import { CommentThread } from "../../_components/CommentThread";
import { ParameterizedCasesPanel } from "../../_components/ParameterizedCasesPanel";
      </div>
    </ManagementShell>
  );
}
