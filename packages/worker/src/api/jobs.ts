/**
 * Jobs API - Manage digest generation jobs and ephemeral servers
 */

import { Hono } from 'hono';
import type { Env } from '../types';
import { createServer, deleteServer, getServer } from '../services/hetzner';
import { generateCloudInit, generateTestCloudInit } from '../services/cloud-init';

const jobs = new Hono<{ Bindings: Env }>();

/**
 * POST /api/jobs/generate
 * Start a new digest generation job (provisions ephemeral server)
 */
jobs.post('/generate', async (c) => {
  const { userId, test = false } = await c.req.json();

  if (!userId || typeof userId !== 'string') {
    return c.json(
      {
        success: false,
        error: { code: 'INVALID_REQUEST', message: 'userId is required' },
      },
      400
    );
  }

  const jobId = crypto.randomUUID();

  try {
    // Create job record in D1
    await c.env.DB.prepare(`
      INSERT INTO jobs (id, user_id, status, started_at)
      VALUES (?, ?, 'pending', ?)
    `).bind(jobId, userId, new Date().toISOString()).run();

    // Log job start
    await c.env.DB.prepare(`
      INSERT INTO server_logs (job_id, level, message)
      VALUES (?, 'info', 'Job created')
    `).bind(jobId).run();

    // Generate cloud-init script
    const workerUrl = new URL(c.req.url).origin;
    const cloudInit = test
      ? generateTestCloudInit(jobId, workerUrl)
      : generateCloudInit(
          {
            jobId,
            userId,
            workerUrl,
            githubRepo: 'https://github.com/AutumnsGrove/AgenticNewspaper.git',
            githubBranch: 'master',
          },
          c.env
        );

    // Provision Hetzner server
    const server = await createServer(c.env, jobId, cloudInit);

    // Update job with server info
    await c.env.DB.prepare(`
      UPDATE jobs
      SET status = 'provisioning', server_id = ?, server_ip = ?
      WHERE id = ?
    `).bind(server.id, server.ip, jobId).run();

    // Log provisioning
    await c.env.DB.prepare(`
      INSERT INTO server_logs (job_id, level, message, metadata)
      VALUES (?, 'info', 'Server provisioned', ?)
    `).bind(jobId, JSON.stringify({ server_id: server.id, ip: server.ip })).run();

    return c.json({
      success: true,
      data: {
        jobId,
        serverId: server.id,
        serverIp: server.ip,
        status: 'provisioning',
      },
    });
  } catch (error) {
    // Log error
    await c.env.DB.prepare(`
      INSERT INTO server_logs (job_id, level, message, metadata)
      VALUES (?, 'error', 'Failed to provision server', ?)
    `).bind(jobId, JSON.stringify({ error: String(error) })).run();

    // Update job status
    await c.env.DB.prepare(`
      UPDATE jobs
      SET status = 'failed', error = ?, completed_at = ?
      WHERE id = ?
    `).bind(String(error), new Date().toISOString(), jobId).run();

    return c.json(
      {
        success: false,
        error: {
          code: 'PROVISIONING_FAILED',
          message: error instanceof Error ? error.message : 'Failed to provision server',
        },
      },
      500
    );
  }
});

/**
 * GET /api/jobs/:jobId
 * Get job status and details
 */
jobs.get('/:jobId', async (c) => {
  const jobId = c.req.param('jobId');

  const job = await c.env.DB.prepare(`
    SELECT * FROM jobs WHERE id = ?
  `).bind(jobId).first();

  if (!job) {
    return c.json(
      {
        success: false,
        error: { code: 'NOT_FOUND', message: 'Job not found' },
      },
      404
    );
  }

  // Get server info if exists
  let server = null;
  if (job.server_id) {
    server = await getServer(c.env, String(job.server_id));
  }

  // Get recent logs
  const logsResult = await c.env.DB.prepare(`
    SELECT * FROM server_logs
    WHERE job_id = ?
    ORDER BY timestamp DESC
    LIMIT 20
  `).bind(jobId).all();

  return c.json({
    success: true,
    data: {
      job,
      server: server ? {
        id: server.id,
        status: server.status,
        ip: server.public_net.ipv4.ip,
        created: server.created,
      } : null,
      logs: logsResult.results,
    },
  });
});

/**
 * DELETE /api/jobs/:jobId
 * Cancel a job and destroy server
 */
jobs.delete('/:jobId', async (c) => {
  const jobId = c.req.param('jobId');

  const job = await c.env.DB.prepare(`
    SELECT * FROM jobs WHERE id = ?
  `).bind(jobId).first();

  if (!job) {
    return c.json(
      {
        success: false,
        error: { code: 'NOT_FOUND', message: 'Job not found' },
      },
      404
    );
  }

  // Delete server if exists
  if (job.server_id) {
    try {
      await deleteServer(c.env, String(job.server_id));

      await c.env.DB.prepare(`
        INSERT INTO server_logs (job_id, level, message)
        VALUES (?, 'info', 'Server deleted manually')
      `).bind(jobId).run();
    } catch (error) {
      console.error('Failed to delete server:', error);
    }
  }

  // Update job status
  await c.env.DB.prepare(`
    UPDATE jobs
    SET status = 'failed', error = 'Cancelled by user', completed_at = ?
    WHERE id = ?
  `).bind(new Date().toISOString(), jobId).run();

  return c.json({ success: true });
});

export default jobs;
