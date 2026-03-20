/**
 * HTTP client for the Grounded preflight API.
 */

import type {
  PreflightJob,
  PreflightJobList,
  VoyagePlanList,
  UsageInfo,
  PluginConfig,
} from "./types";

export class GroundedClient {
  private baseUrl: string;
  private apiKey: string | undefined;

  constructor(config: PluginConfig) {
    this.baseUrl = config.apiUrl.replace(/\/$/, "");
    this.apiKey = config.apiKey;
  }

  private headers(): Record<string, string> {
    const hdrs: Record<string, string> = { "Content-Type": "application/json" };
    if (this.apiKey) hdrs["Authorization"] = `Bearer ${this.apiKey}`;
    return hdrs;
  }

  private static async request(
    url: string,
    init?: RequestInit,
  ): Promise<Response> {
    let resp: Response;
    try {
      resp = await fetch(url, init);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      throw new Error(`Grounded API network error: ${message}`);
    }
    if (!resp.ok) {
      const detail = resp.statusText ? ` ${resp.statusText}` : "";
      throw new Error(`Grounded API: ${resp.status}${detail}`);
    }
    return resp;
  }

  async getJob(jobId: string): Promise<PreflightJob> {
    const resp = await GroundedClient.request(
      `${this.baseUrl}/api/v1/jobs/${jobId}`,
      {
        headers: this.headers(),
      },
    );
    return resp.json() as Promise<PreflightJob>;
  }

  async listJobs(page = 1, pageSize = 20): Promise<PreflightJobList> {
    const resp = await GroundedClient.request(
      `${this.baseUrl}/api/v1/jobs?page=${page}&page_size=${pageSize}`,
      { headers: this.headers() },
    );
    return resp.json() as Promise<PreflightJobList>;
  }

  async deleteJob(jobId: string): Promise<void> {
    await GroundedClient.request(`${this.baseUrl}/api/v1/jobs/${jobId}`, {
      method: "DELETE",
      headers: this.headers(),
    });
  }

  async listProfiles(): Promise<VoyagePlanList> {
    const resp = await GroundedClient.request(
      `${this.baseUrl}/api/v1/profiles`,
      {
        headers: this.headers(),
      },
    );
    return resp.json() as Promise<VoyagePlanList>;
  }

  async getUsage(): Promise<UsageInfo> {
    const resp = await GroundedClient.request(`${this.baseUrl}/api/v1/usage`, {
      headers: this.headers(),
    });
    return resp.json() as Promise<UsageInfo>;
  }
}
