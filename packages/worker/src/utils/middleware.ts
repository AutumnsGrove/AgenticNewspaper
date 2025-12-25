/**
 * Middleware utilities for the worker.
 */

import type { Context, Next } from 'hono';
import type { Env } from '../types';
import { verifyJwt } from '../api/auth';

/**
 * CORS middleware.
 */
export function cors() {
  return async (c: Context<{ Bindings: Env }>, next: Next) => {
    const origin = c.req.header('Origin') || '*';
    const allowedOrigins = [
      'https://clearing.autumnsgrove.com',
      'http://localhost:5173',
      'http://localhost:4173',
    ];

    const corsOrigin = allowedOrigins.includes(origin) ? origin : allowedOrigins[0];

    c.header('Access-Control-Allow-Origin', corsOrigin);
    c.header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS');
    c.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    c.header('Access-Control-Max-Age', '86400');

    if (c.req.method === 'OPTIONS') {
      return new Response(null, { status: 204 });
    }

    await next();
  };
}

/**
 * Rate limiting middleware.
 */
export function rateLimit(config: { windowMs: number; maxRequests: number }) {
  return async (c: Context<{ Bindings: Env }>, next: Next) => {
    const ip = c.req.header('CF-Connecting-IP') || 'unknown';
    const key = `rate:${ip}:${Math.floor(Date.now() / config.windowMs)}`;

    try {
      const current = await c.env.RATE_LIMIT.get(key);
      const count = current ? parseInt(current, 10) : 0;

      if (count >= config.maxRequests) {
        const resetTime = Math.ceil(Date.now() / config.windowMs) * config.windowMs;
        c.header('X-RateLimit-Limit', String(config.maxRequests));
        c.header('X-RateLimit-Remaining', '0');
        c.header('X-RateLimit-Reset', String(resetTime));

        return c.json(
          {
            success: false,
            error: {
              code: 'RATE_LIMITED',
              message: 'Too many requests. Please try again later.',
            },
          },
          429
        );
      }

      // Increment counter
      await c.env.RATE_LIMIT.put(key, String(count + 1), {
        expirationTtl: Math.ceil(config.windowMs / 1000),
      });

      c.header('X-RateLimit-Limit', String(config.maxRequests));
      c.header('X-RateLimit-Remaining', String(config.maxRequests - count - 1));

      await next();
    } catch (error) {
      // If rate limiting fails, allow the request
      console.error('Rate limiting error:', error);
      await next();
    }
  };
}

/**
 * Authentication middleware.
 */
interface AuthVariables {
  userId: string;
  userEmail: string;
  userTier: string;
}

export function authenticate() {
  return async (c: Context<{ Bindings: Env; Variables: AuthVariables }>, next: Next) => {
    const authHeader = c.req.header('Authorization');

    if (!authHeader?.startsWith('Bearer ')) {
      return c.json(
        {
          success: false,
          error: { code: 'UNAUTHORIZED', message: 'No token provided' },
        },
        401
      );
    }

    const token = authHeader.slice(7);
    const jwtSecret = c.env.JWT_SECRET || 'development-secret';
    const payload = await verifyJwt(token, jwtSecret);

    if (!payload) {
      return c.json(
        {
          success: false,
          error: { code: 'UNAUTHORIZED', message: 'Invalid or expired token' },
        },
        401
      );
    }

    // Store user info in context
    c.set('userId', payload.userId);
    c.set('userEmail', payload.email);
    c.set('userTier', payload.tier);

    await next();
  };
}

/**
 * Request logging middleware.
 */
export function logger() {
  return async (c: Context<{ Bindings: Env }>, next: Next) => {
    const start = Date.now();
    const requestId = crypto.randomUUID().slice(0, 8);

    c.header('X-Request-ID', requestId);

    try {
      await next();
    } finally {
      const duration = Date.now() - start;
      const status = c.res.status;
      const method = c.req.method;
      const path = new URL(c.req.url).pathname;

      console.log(
        JSON.stringify({
          requestId,
          method,
          path,
          status,
          duration,
          timestamp: new Date().toISOString(),
        })
      );
    }
  };
}

/**
 * Error handling middleware.
 */
export function errorHandler() {
  return async (c: Context<{ Bindings: Env }>, next: Next) => {
    try {
      await next();
    } catch (error) {
      console.error('Unhandled error:', error);

      const message = error instanceof Error ? error.message : 'Unknown error';
      const status = error instanceof Error && 'status' in error ? (error as { status: number }).status : 500;

      return c.json(
        {
          success: false,
          error: {
            code: 'INTERNAL_ERROR',
            message: c.env.ENVIRONMENT === 'production' ? 'Internal server error' : message,
          },
        },
        status as 500 | 400 | 401 | 403 | 404
      );
    }
  };
}

/**
 * Request timeout middleware.
 */
export function timeout(ms: number = 25000) {
  return async (c: Context<{ Bindings: Env }>, next: Next) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), ms);

    try {
      await next();
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return c.json(
          {
            success: false,
            error: { code: 'TIMEOUT', message: 'Request timed out' },
          },
          504
        );
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  };
}

/**
 * Security headers middleware.
 */
export function securityHeaders() {
  return async (c: Context<{ Bindings: Env }>, next: Next) => {
    await next();

    c.header('X-Content-Type-Options', 'nosniff');
    c.header('X-Frame-Options', 'DENY');
    c.header('X-XSS-Protection', '1; mode=block');
    c.header('Referrer-Policy', 'strict-origin-when-cross-origin');

    if (c.env.ENVIRONMENT === 'production') {
      c.header('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
    }
  };
}
