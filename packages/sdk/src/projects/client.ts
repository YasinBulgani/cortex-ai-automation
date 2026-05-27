/**
 * @cortex/sdk — Projects API client.
 */

import type { CortexClient } from "../common/client";
import type { Project, CreateProjectInput, ProjectStats } from "./types";

const BASE = "/api/v1/projects";

export class ProjectsClient {
  constructor(private readonly http: CortexClient) {}

  list(): Promise<Project[]> {
    return this.http.get(BASE);
  }

  get(projectId: string): Promise<Project> {
    return this.http.get(`${BASE}/${projectId}`);
  }

  create(input: CreateProjectInput): Promise<Project> {
    return this.http.post(BASE, { json: input });
  }

  stats(projectId: string): Promise<ProjectStats> {
    return this.http.get(`${BASE}/${projectId}/stats`);
  }
}
