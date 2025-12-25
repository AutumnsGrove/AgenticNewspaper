/**
 * Hetzner Cloud API Service for The Daily Clearing
 * Handles ephemeral VPS provisioning for digest generation
 *
 * Inspired by GroveMC's Hetzner service
 * Cost: CPX11 @ $0.01/hour (2 vCPU, 2GB RAM)
 */

import type { Env } from '../types';

const HETZNER_API_BASE = 'https://api.hetzner.cloud/v1';

// Server configuration - using CPX11 for cost efficiency
// CPX11: 2 vCPU (shared), 2GB RAM, 40GB SSD, $0.01/hour
// Using EU servers (nbg1) - more reliable than NA servers, minimal latency impact
export const HETZNER_CONFIG = {
  serverType: 'cpx11',
  location: 'nbg1',       // Nuremberg, Germany (most reliable availability)
  hourlyRate: 0.01,
  image: 'ubuntu-22.04',  // LTS version
} as const;

export interface HetznerServer {
  id: number;
  name: string;
  status: 'initializing' | 'starting' | 'running' | 'stopping' | 'off' | 'deleting' | 'rebuilding' | 'migrating' | 'unknown';
  public_net: {
    ipv4: {
      ip: string;
    };
    ipv6: {
      ip: string;
    };
  };
  server_type: {
    name: string;
    description: string;
  };
  datacenter: {
    name: string;
    location: {
      name: string;
      city: string;
      country: string;
    };
  };
  created: string;
}

export interface CreateServerResponse {
  server: HetznerServer;
  action: {
    id: number;
    status: string;
  };
  root_password: string | null;
}

export interface HetznerError {
  code: string;
  message: string;
}

/**
 * Generic Hetzner API request helper
 */
async function hetznerRequest<T>(
  env: Env,
  method: string,
  endpoint: string,
  body?: unknown
): Promise<T> {
  const url = `${HETZNER_API_BASE}${endpoint}`;

  const response = await fetch(url, {
    method,
    headers: {
      'Authorization': `Bearer ${env.HETZNER_API_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({})) as { error?: HetznerError };
    throw new Error(
      `Hetzner API error: ${response.status} ${error.error?.message || response.statusText}`
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}

/**
 * Create a new ephemeral server for digest generation
 */
export async function createServer(
  env: Env,
  jobId: string,
  cloudInitScript: string
): Promise<{ id: string; ip: string; serverType: string }> {
  const serverName = `clearing-${jobId}`;

  const response = await hetznerRequest<CreateServerResponse>(env, 'POST', '/servers', {
    name: serverName,
    server_type: HETZNER_CONFIG.serverType,
    location: HETZNER_CONFIG.location,
    image: HETZNER_CONFIG.image,
    user_data: cloudInitScript,
    labels: {
      project: 'daily-clearing',
      job_id: jobId,
      ephemeral: 'true',
    },
    start_after_create: true,
  });

  return {
    id: String(response.server.id),
    ip: response.server.public_net.ipv4.ip,
    serverType: HETZNER_CONFIG.serverType,
  };
}

/**
 * Delete a server (cleanup after digest generation)
 */
export async function deleteServer(env: Env, serverId: string): Promise<void> {
  await hetznerRequest(env, 'DELETE', `/servers/${serverId}`);
}

/**
 * Get server information
 */
export async function getServer(
  env: Env,
  serverId: string
): Promise<HetznerServer | null> {
  try {
    const response = await hetznerRequest<{ server: HetznerServer }>(
      env,
      'GET',
      `/servers/${serverId}`
    );
    return response.server;
  } catch (error) {
    // Server not found
    if (error instanceof Error && error.message.includes('404')) {
      return null;
    }
    throw error;
  }
}

/**
 * List all Daily Clearing servers
 */
export async function listServers(env: Env): Promise<HetznerServer[]> {
  const response = await hetznerRequest<{ servers: HetznerServer[] }>(
    env,
    'GET',
    '/servers?label_selector=project=daily-clearing'
  );
  return response.servers;
}

/**
 * Wait for server to reach running status
 */
export async function waitForServerRunning(
  env: Env,
  serverId: string,
  timeoutMs = 120000, // 2 minutes
  pollIntervalMs = 5000
): Promise<HetznerServer> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeoutMs) {
    const server = await getServer(env, serverId);

    if (!server) {
      throw new Error(`Server ${serverId} not found`);
    }

    if (server.status === 'running') {
      return server;
    }

    if (server.status === 'off' || server.status === 'deleting') {
      throw new Error(`Server ${serverId} is ${server.status}`);
    }

    await new Promise(resolve => setTimeout(resolve, pollIntervalMs));
  }

  throw new Error(`Timeout waiting for server ${serverId} to start`);
}

/**
 * Get hourly cost estimate
 */
export function getHourlyRate(): number {
  return HETZNER_CONFIG.hourlyRate;
}

/**
 * Calculate cost for a job
 */
export function calculateCost(durationMinutes: number): number {
  const hours = durationMinutes / 60;
  return hours * HETZNER_CONFIG.hourlyRate;
}
