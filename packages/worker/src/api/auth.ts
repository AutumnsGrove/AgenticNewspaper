/**
 * Authentication API Routes.
 *
 * Handles user authentication and session management.
 * Supports both local auth (for development) and GroveAuth/Heartwood (production).
 */

import { Hono } from 'hono';
import { z } from 'zod';
import type { Env, User, AuthToken } from '../types';
import { createUser, getUserByEmail, getUserById } from '../services/database';
import {
  generateCodeVerifier,
  generateCodeChallenge,
  getLoginUrl,
  exchangeCodeForTokens,
  verifyToken,
  getUserInfo,
  revokeTokens,
  storePKCEState,
  getPKCEState,
  createSession,
  getSession,
  deleteSession,
} from '../services/auth';

const auth = new Hono<{ Bindings: Env }>();

// ============================================================================
// Validation Schemas
// ============================================================================

const signupSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string(),
});

// ============================================================================
// JWT Helpers
// ============================================================================

async function createJwt(payload: AuthToken, secret: string): Promise<string> {
  const header = { alg: 'HS256', typ: 'JWT' };
  const encodedHeader = btoa(JSON.stringify(header));
  const encodedPayload = btoa(JSON.stringify(payload));
  const message = `${encodedHeader}.${encodedPayload}`;

  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(message));
  const encodedSignature = btoa(String.fromCharCode(...new Uint8Array(signature)));

  return `${message}.${encodedSignature}`;
}

async function verifyJwt(token: string, secret: string): Promise<AuthToken | null> {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    const [encodedHeader, encodedPayload, encodedSignature] = parts;
    const message = `${encodedHeader}.${encodedPayload}`;

    const key = await crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(secret),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['verify']
    );

    const signature = Uint8Array.from(atob(encodedSignature), (c) => c.charCodeAt(0));
    const valid = await crypto.subtle.verify('HMAC', key, signature, new TextEncoder().encode(message));

    if (!valid) return null;

    const payload = JSON.parse(atob(encodedPayload)) as AuthToken;

    // Check expiration
    if (payload.exp && payload.exp < Date.now() / 1000) {
      return null;
    }

    return payload;
  } catch {
    return null;
  }
}

async function hashPassword(password: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(password);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

// ============================================================================
// Routes
// ============================================================================

/**
 * POST /auth/signup - Create new user account.
 */
auth.post('/signup', async (c) => {
  try {
    const body = await c.req.json();
    const parsed = signupSchema.safeParse(body);

    if (!parsed.success) {
      return c.json(
        {
          success: false,
          error: { code: 'VALIDATION_ERROR', message: parsed.error.message },
        },
        400
      );
    }

    const { email, password } = parsed.data;

    // Check if user exists
    const existing = await getUserByEmail(c.env.DB, email);
    if (existing) {
      return c.json(
        {
          success: false,
          error: { code: 'USER_EXISTS', message: 'Email already registered' },
        },
        409
      );
    }

    // Hash password and create user
    const passwordHash = await hashPassword(password);
    const userId = crypto.randomUUID();

    const user = await createUser(c.env.DB, {
      id: userId,
      email,
    });

    // Store password hash in KV (separate from D1 for security)
    await c.env.SESSIONS.put(`password:${userId}`, passwordHash, {
      expirationTtl: 60 * 60 * 24 * 365, // 1 year
    });

    // Create JWT
    const jwtSecret = c.env.JWT_SECRET || 'development-secret';
    const token = await createJwt(
      {
        userId: user.id,
        email: user.email,
        tier: user.subscriptionTier,
        iat: Math.floor(Date.now() / 1000),
        exp: Math.floor(Date.now() / 1000) + 60 * 60 * 24 * 7, // 7 days
      },
      jwtSecret
    );

    // Store session
    await c.env.SESSIONS.put(
      `session:${token}`,
      JSON.stringify({
        userId: user.id,
        createdAt: new Date().toISOString(),
        expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      }),
      { expirationTtl: 60 * 60 * 24 * 7 }
    );

    return c.json(
      {
        success: true,
        data: {
          user: {
            id: user.id,
            email: user.email,
            subscriptionTier: user.subscriptionTier,
          },
          token,
        },
      },
      201
    );
  } catch (error) {
    console.error('Signup error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to create account' },
      },
      500
    );
  }
});

/**
 * POST /auth/login - Authenticate user.
 */
auth.post('/login', async (c) => {
  try {
    const body = await c.req.json();
    const parsed = loginSchema.safeParse(body);

    if (!parsed.success) {
      return c.json(
        {
          success: false,
          error: { code: 'VALIDATION_ERROR', message: parsed.error.message },
        },
        400
      );
    }

    const { email, password } = parsed.data;

    // Get user
    const user = await getUserByEmail(c.env.DB, email);
    if (!user) {
      return c.json(
        {
          success: false,
          error: { code: 'INVALID_CREDENTIALS', message: 'Invalid email or password' },
        },
        401
      );
    }

    // Verify password
    const storedHash = await c.env.SESSIONS.get(`password:${user.id}`);
    const providedHash = await hashPassword(password);

    if (!storedHash || storedHash !== providedHash) {
      return c.json(
        {
          success: false,
          error: { code: 'INVALID_CREDENTIALS', message: 'Invalid email or password' },
        },
        401
      );
    }

    // Create JWT
    const jwtSecret = c.env.JWT_SECRET || 'development-secret';
    const token = await createJwt(
      {
        userId: user.id,
        email: user.email,
        tier: user.subscriptionTier,
        iat: Math.floor(Date.now() / 1000),
        exp: Math.floor(Date.now() / 1000) + 60 * 60 * 24 * 7, // 7 days
      },
      jwtSecret
    );

    // Store session
    await c.env.SESSIONS.put(
      `session:${token}`,
      JSON.stringify({
        userId: user.id,
        createdAt: new Date().toISOString(),
        expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      }),
      { expirationTtl: 60 * 60 * 24 * 7 }
    );

    return c.json({
      success: true,
      data: {
        user: {
          id: user.id,
          email: user.email,
          subscriptionTier: user.subscriptionTier,
        },
        token,
      },
    });
  } catch (error) {
    console.error('Login error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Login failed' },
      },
      500
    );
  }
});

/**
 * POST /auth/logout - Invalidate session.
 */
auth.post('/logout', async (c) => {
  const authHeader = c.req.header('Authorization');
  if (authHeader?.startsWith('Bearer ')) {
    const token = authHeader.slice(7);
    await c.env.SESSIONS.delete(`session:${token}`);
  }

  return c.json({ success: true });
});

/**
 * GET /auth/me - Get current user.
 */
auth.get('/me', async (c) => {
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

  const user = await getUserById(c.env.DB, payload.userId);
  if (!user) {
    return c.json(
      {
        success: false,
        error: { code: 'NOT_FOUND', message: 'User not found' },
      },
      404
    );
  }

  return c.json({
    success: true,
    data: {
      id: user.id,
      email: user.email,
      subscriptionTier: user.subscriptionTier,
      preferences: user.preferences,
    },
  });
});

/**
 * Middleware to verify authentication.
 */
export async function requireAuth(
  c: { req: { header: (name: string) => string | undefined }; env: Env },
  next: () => Promise<void>
): Promise<Response | void> {
  const authHeader = c.req.header('Authorization');
  if (!authHeader?.startsWith('Bearer ')) {
    return new Response(
      JSON.stringify({
        success: false,
        error: { code: 'UNAUTHORIZED', message: 'No token provided' },
      }),
      { status: 401, headers: { 'Content-Type': 'application/json' } }
    );
  }

  const token = authHeader.slice(7);
  const jwtSecret = c.env.JWT_SECRET || 'development-secret';
  const payload = await verifyJwt(token, jwtSecret);

  if (!payload) {
    return new Response(
      JSON.stringify({
        success: false,
        error: { code: 'UNAUTHORIZED', message: 'Invalid or expired token' },
      }),
      { status: 401, headers: { 'Content-Type': 'application/json' } }
    );
  }

  // Store user info in request context
  (c as Record<string, unknown>).user = payload;
  await next();
}

// ============================================================================
// GroveAuth / Heartwood OAuth Routes
// ============================================================================

/**
 * GET /auth/heartwood/login - Initiate Heartwood OAuth flow.
 */
auth.get('/heartwood/login', async (c) => {
  const redirectUri = `${new URL(c.req.url).origin}/api/auth/heartwood/callback`;

  // Generate PKCE values
  const state = crypto.randomUUID();
  const codeVerifier = generateCodeVerifier();
  const codeChallenge = await generateCodeChallenge(codeVerifier);

  // Store PKCE state for callback verification
  await storePKCEState(c.env, state, codeVerifier, redirectUri);

  // Redirect to Heartwood login
  const loginUrl = getLoginUrl(redirectUri, state, codeChallenge);
  return c.redirect(loginUrl);
});

/**
 * GET /auth/heartwood/callback - Handle Heartwood OAuth callback.
 */
auth.get('/heartwood/callback', async (c) => {
  const url = new URL(c.req.url);
  const code = url.searchParams.get('code');
  const state = url.searchParams.get('state');
  const error = url.searchParams.get('error');

  // Handle error from Heartwood
  if (error) {
    return c.redirect(`/?auth_error=${encodeURIComponent(error)}`);
  }

  if (!code || !state) {
    return c.redirect('/?auth_error=missing_params');
  }

  // Retrieve PKCE state
  const pkceState = await getPKCEState(c.env, state);
  if (!pkceState) {
    return c.redirect('/?auth_error=invalid_state');
  }

  try {
    // Exchange code for tokens
    const clientSecret = c.env.HEARTWOOD_CLIENT_SECRET;
    if (!clientSecret) {
      throw new Error('HEARTWOOD_CLIENT_SECRET not configured');
    }

    const tokens = await exchangeCodeForTokens(
      code,
      pkceState.redirectUri,
      pkceState.codeVerifier,
      clientSecret
    );

    // Get user info from Heartwood
    const heartwoodUser = await getUserInfo(tokens.access_token);
    if (!heartwoodUser) {
      throw new Error('Failed to get user info');
    }

    // Check if user exists in our DB, create if not
    let user = await getUserByEmail(c.env.DB, heartwoodUser.email);
    if (!user) {
      user = await createUser(c.env.DB, {
        id: heartwoodUser.id, // Use Heartwood user ID
        email: heartwoodUser.email,
      });
    }

    // Create local session
    const sessionId = await createSession(
      c.env,
      user.id,
      tokens.access_token,
      tokens.refresh_token,
      tokens.expires_in
    );

    // Set session cookie and redirect to app
    const headers = new Headers();
    headers.set('Location', '/');
    headers.set(
      'Set-Cookie',
      `session=${sessionId}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${tokens.expires_in}`
    );

    return new Response(null, { status: 302, headers });
  } catch (err) {
    console.error('OAuth callback error:', err);
    return c.redirect('/?auth_error=callback_failed');
  }
});

/**
 * POST /auth/heartwood/logout - Logout from Heartwood and clear session.
 */
auth.post('/heartwood/logout', async (c) => {
  // Get session from cookie
  const cookie = c.req.header('Cookie');
  const sessionMatch = cookie?.match(/session=([^;]+)/);

  if (sessionMatch) {
    const sessionId = sessionMatch[1];
    const session = await getSession(c.env, sessionId);

    if (session) {
      // Revoke tokens with Heartwood
      try {
        await revokeTokens(session.accessToken);
      } catch {
        // Ignore errors revoking tokens
      }

      // Delete local session
      await deleteSession(c.env, sessionId);
    }
  }

  // Clear cookie
  const headers = new Headers();
  headers.set('Content-Type', 'application/json');
  headers.set('Set-Cookie', 'session=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0');

  return new Response(JSON.stringify({ success: true }), { headers });
});

/**
 * GET /auth/heartwood/me - Get current user from Heartwood session.
 */
auth.get('/heartwood/me', async (c) => {
  const cookie = c.req.header('Cookie');
  const sessionMatch = cookie?.match(/session=([^;]+)/);

  if (!sessionMatch) {
    return c.json(
      { success: false, error: { code: 'UNAUTHORIZED', message: 'Not logged in' } },
      401
    );
  }

  const sessionId = sessionMatch[1];
  const session = await getSession(c.env, sessionId);

  if (!session) {
    return c.json(
      { success: false, error: { code: 'UNAUTHORIZED', message: 'Session expired' } },
      401
    );
  }

  // Get user from our DB
  const user = await getUserById(c.env.DB, session.userId);
  if (!user) {
    return c.json(
      { success: false, error: { code: 'NOT_FOUND', message: 'User not found' } },
      404
    );
  }

  // Optionally verify with Heartwood (for fresh data)
  const heartwoodUser = await verifyToken(session.accessToken);

  return c.json({
    success: true,
    data: {
      id: user.id,
      email: user.email,
      name: heartwoodUser?.name || null,
      picture: heartwoodUser?.picture || null,
      subscriptionTier: user.subscriptionTier,
      preferences: user.preferences,
    },
  });
});

export { auth, verifyJwt, createJwt };
