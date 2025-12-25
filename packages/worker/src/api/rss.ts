/**
 * RSS Feed API Routes.
 *
 * Handles RSS feed generation and delivery.
 */

import { Hono } from 'hono';
import type { Env, Digest } from '../types';
import { getUserByRssToken, listUserDigestRecords } from '../services/database';
import { getDigest } from '../services/storage';
import { generateRssFeed } from '../services/rss';

const rss = new Hono<{ Bindings: Env }>();

/**
 * GET /rss/:userId/:token - Get user's RSS feed.
 */
rss.get('/:userId/:token', async (c) => {
  const userId = c.req.param('userId');
  const token = c.req.param('token');

  try {
    // Verify token
    const user = await getUserByRssToken(c.env.DB, token);
    if (!user || user.id !== userId) {
      return c.text('Unauthorized', 401);
    }

    // Get recent digests
    const { records } = await listUserDigestRecords(c.env.DB, userId, { limit: 20 });

    // Fetch full digests from R2
    const digestsWithContent: Array<{ digest: Digest; digestId: string }> = [];

    for (const record of records) {
      const stored = await getDigest(c.env, userId, record.id);
      if (stored) {
        digestsWithContent.push({
          digest: stored.digest,
          digestId: record.id,
        });
      }
    }

    // Generate RSS feed
    const feedXml = generateRssFeed(digestsWithContent, {
      userId,
      userEmail: user.email,
      rssToken: token,
      baseUrl: 'https://clearing.autumnsgrove.com',
    });

    return new Response(feedXml, {
      headers: {
        'Content-Type': 'application/rss+xml; charset=utf-8',
        'Cache-Control': 'public, max-age=900', // 15 minutes
      },
    });
  } catch (error) {
    console.error('RSS feed error:', error);
    return c.text('Internal Server Error', 500);
  }
});

/**
 * GET /rss/:userId/:token/atom - Get user's Atom feed.
 */
rss.get('/:userId/:token/atom', async (c) => {
  const userId = c.req.param('userId');
  const token = c.req.param('token');

  try {
    // Verify token
    const user = await getUserByRssToken(c.env.DB, token);
    if (!user || user.id !== userId) {
      return c.text('Unauthorized', 401);
    }

    // Get recent digests
    const { records } = await listUserDigestRecords(c.env.DB, userId, { limit: 20 });

    // Fetch full digests from R2
    const digestsWithContent: Array<{ digest: Digest; digestId: string }> = [];

    for (const record of records) {
      const stored = await getDigest(c.env, userId, record.id);
      if (stored) {
        digestsWithContent.push({
          digest: stored.digest,
          digestId: record.id,
        });
      }
    }

    // Generate Atom feed
    const atomXml = generateAtomFeed(digestsWithContent, {
      userId,
      userEmail: user.email,
      rssToken: token,
      baseUrl: 'https://clearing.autumnsgrove.com',
    });

    return new Response(atomXml, {
      headers: {
        'Content-Type': 'application/atom+xml; charset=utf-8',
        'Cache-Control': 'public, max-age=900', // 15 minutes
      },
    });
  } catch (error) {
    console.error('Atom feed error:', error);
    return c.text('Internal Server Error', 500);
  }
});

/**
 * Generate Atom feed XML.
 */
function generateAtomFeed(
  digests: Array<{ digest: Digest; digestId: string }>,
  options: {
    userId: string;
    userEmail: string;
    rssToken: string;
    baseUrl: string;
  }
): string {
  const { userId, userEmail, rssToken, baseUrl } = options;
  const feedUrl = `${baseUrl}/rss/${userId}/${rssToken}/atom`;
  const webUrl = `${baseUrl}/digest`;

  const entries = digests.map(({ digest, digestId }) => {
    const date = new Date(digest.metadata.generatedAt);
    const link = `${webUrl}/${digestId}`;

    return `
    <entry>
      <title>${escapeXml(formatTitle(digest.metadata.generatedAt))}</title>
      <link href="${link}" rel="alternate" type="text/html"/>
      <id>${link}</id>
      <updated>${date.toISOString()}</updated>
      <author>
        <name>The Daily Clearing</name>
      </author>
      <summary type="html">${escapeXml(buildSummary(digest))}</summary>
    </entry>`;
  });

  const lastUpdated =
    digests.length > 0 ? new Date(digests[0].digest.metadata.generatedAt).toISOString() : new Date().toISOString();

  return `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>The Daily Clearing - ${userEmail}</title>
  <subtitle>Your personalized AI-curated news digest</subtitle>
  <link href="${feedUrl}" rel="self" type="application/atom+xml"/>
  <link href="${webUrl}" rel="alternate" type="text/html"/>
  <id>${feedUrl}</id>
  <updated>${lastUpdated}</updated>
  <generator>The Daily Clearing v1.0</generator>
  ${entries.join('\n')}
</feed>`;
}

/**
 * Format digest title.
 */
function formatTitle(generatedAt: string): string {
  const date = new Date(generatedAt);
  return `The Daily Clearing - ${date.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })}`;
}

/**
 * Build summary for Atom entry.
 */
function buildSummary(digest: Digest): string {
  const lines: string[] = [];

  for (const section of digest.sections) {
    lines.push(`<h3>${section.topic}</h3>`);
    lines.push(`<p>${section.sectionSummary}</p>`);
    lines.push('<ul>');
    for (const article of section.articles.slice(0, 3)) {
      lines.push(`<li><a href="${article.url}">${article.title}</a></li>`);
    }
    lines.push('</ul>');
  }

  return lines.join('');
}

/**
 * Escape XML special characters.
 */
function escapeXml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

export { rss };
