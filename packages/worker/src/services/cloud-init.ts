/**
 * Cloud-init script generation for digest generation servers
 *
 * This script runs when the Hetzner VPS boots:
 * 1. Install UV + Python
 * 2. Clone Daily Clearing repo
 * 3. Install dependencies
 * 4. Generate digest
 * 5. Upload results to R2
 * 6. Trigger self-destruct
 */

import type { Env } from '../types';

export interface CloudInitConfig {
  jobId: string;
  userId: string;
  workerUrl: string;
  githubRepo: string;
  githubBranch: string;
}

/**
 * Generate cloud-init YAML for digest generation
 */
export function generateCloudInit(config: CloudInitConfig, env: Env): string {
  const {
    jobId,
    userId,
    workerUrl,
    githubRepo,
    githubBranch,
  } = config;

  return `#cloud-config

# The Daily Clearing - Ephemeral Digest Generation Server
# Job ID: ${jobId}
# User ID: ${userId}

package_update: true
package_upgrade: true

packages:
  - git
  - curl
  - python3.11
  - python3.11-venv
  - python3-pip

write_files:
  - path: /opt/clearing/secrets.json
    permissions: '0600'
    content: |
      {
        "openrouter_api_key": "${env.OPENROUTER_API_KEY}",
        "tavily_api_key": "${env.TAVILY_API_KEY}",
        "anthropic_api_key": "${env.ANTHROPIC_API_KEY || ''}"
      }

  - path: /opt/clearing/run-digest.py
    permissions: '0755'
    content: |
      #!/usr/bin/env python3
      """
      Digest generation runner - executed on ephemeral Hetzner VPS
      """
      import asyncio
      import json
      import sys
      import traceback
      from pathlib import Path

      # Add package to Python path
      sys.path.insert(0, '/opt/clearing/AgenticNewspaper/packages/core/src')

      async def main():
          import httpx
          from orchestrator.main_orchestrator import generate_digest_for_user

          job_id = "${jobId}"
          user_id = "${userId}"
          webhook_url = "${workerUrl}/api/webhooks/job-status"

          print(f"Starting digest generation for job {job_id}")
          print(f"User: {user_id}")

          try:
              # Generate digest
              print("Running orchestrator...")
              digest = await generate_digest_for_user(user_id)

              print(f"Digest generated successfully!")
              print(f"Topics: {len(digest.sections)}")
              print(f"Articles: {digest.metadata.total_articles_included}")
              print(f"Cost: \\${digest.metadata.total_cost_usd:.4f}")

              # Upload to Cloudflare
              async with httpx.AsyncClient(timeout=30.0) as client:
                  await client.post(
                      webhook_url,
                      json={
                          'job_id': job_id,
                          'status': 'completed',
                          'digest': {
                              'markdown': digest.to_markdown(),
                              'metadata': {
                                  'topics_covered': digest.metadata.topics_covered,
                                  'articles_found': digest.metadata.total_articles_found,
                                  'articles_included': digest.metadata.total_articles_included,
                                  'tokens_used': digest.metadata.total_tokens_used,
                                  'cost_usd': digest.metadata.total_cost_usd,
                              }
                          }
                      }
                  )
                  print("Results uploaded to Cloudflare")

          except Exception as e:
              error_msg = f"{type(e).__name__}: {str(e)}"
              print(f"Error: {error_msg}", file=sys.stderr)
              traceback.print_exc()

              # Report error
              async with httpx.AsyncClient(timeout=10.0) as client:
                  await client.post(
                      webhook_url,
                      json={
                          'job_id': job_id,
                          'status': 'failed',
                          'error': error_msg,
                      }
                  )

          finally:
              # Trigger self-destruct
              print("Triggering server deletion...")
              async with httpx.AsyncClient(timeout=10.0) as client:
                  await client.post(
                      webhook_url,
                      json={
                          'job_id': job_id,
                          'action': 'destroy',
                      }
                  )

      if __name__ == '__main__':
          asyncio.run(main())

runcmd:
  # Install UV (fast Python package manager)
  - curl -LsSf https://astral.sh/uv/install.sh | sh
  - export PATH="/root/.cargo/bin:$PATH"

  # Clone repository
  - mkdir -p /opt/clearing
  - cd /opt/clearing
  - git clone --depth 1 --branch ${githubBranch} ${githubRepo} AgenticNewspaper

  # Install Python dependencies
  - cd /opt/clearing/AgenticNewspaper/packages/core
  - /root/.cargo/bin/uv sync

  # Run digest generation
  - cd /opt/clearing
  - /root/.cargo/bin/uv run python run-digest.py

final_message: "The Daily Clearing digest generation completed for job ${jobId}"
`;
}

/**
 * Generate a minimal cloud-init for testing server provisioning
 */
export function generateTestCloudInit(jobId: string, workerUrl: string): string {
  return `#cloud-config

# Test server for job ${jobId}

package_update: true

packages:
  - curl

runcmd:
  - echo "Server started for job ${jobId}" > /tmp/job-status.txt
  - |
    curl -X POST ${workerUrl}/api/webhooks/job-status \
      -H "Content-Type: application/json" \
      -d '{"job_id": "${jobId}", "status": "test_completed", "action": "destroy"}'

final_message: "Test server ready for job ${jobId}"
`;
}
