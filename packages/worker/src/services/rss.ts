/**
 * RSS Feed Generation Service.
 *
 * Generates per-user RSS feeds for digest delivery.
 */

import type { Env, Digest, DigestSection, Article } from '../types';

interface RssFeedOptions {
  userId: string;
  userEmail: string;
  rssToken: string;
  baseUrl: string;
}

/**
 * Generate RSS feed XML for a list of digests.
 */
export function generateRssFeed(
  digests: Array<{ digest: Digest; digestId: string }>,
  options: RssFeedOptions
): string {
  const { userId, userEmail, rssToken, baseUrl } = options;

  const feedUrl = `${baseUrl}/rss/${userId}/${rssToken}`;
  const webUrl = `${baseUrl}/digest`;

  const items = digests.map(({ digest, digestId }) => generateRssItem(digest, digestId, webUrl));

  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:atom="http://www.w3.org/2005/Atom"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>The Daily Clearing - ${userEmail}</title>
    <link>${webUrl}</link>
    <description>Your personalized AI-curated news digest</description>
    <language>en-us</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    <atom:link href="${feedUrl}" rel="self" type="application/rss+xml"/>
    <generator>The Daily Clearing v1.0</generator>
    <ttl>60</ttl>
    ${items.join('\n    ')}
  </channel>
</rss>`;
}

/**
 * Generate a single RSS item for a digest.
 */
function generateRssItem(digest: Digest, digestId: string, webUrl: string): string {
  const { metadata, sections } = digest;
  const link = `${webUrl}/${digestId}`;
  const pubDate = new Date(metadata.generatedAt).toUTCString();

  // Build description from sections
  const description = buildDigestDescription(sections);

  // Build full content
  const content = buildDigestContent(digest);

  // Build categories from topics
  const categories = metadata.topicsCovered
    .map((topic) => `<category>${escapeXml(topic)}</category>`)
    .join('\n      ');

  return `<item>
      <title>${escapeXml(formatDigestTitle(metadata.generatedAt))}</title>
      <link>${link}</link>
      <guid isPermaLink="true">${link}</guid>
      <pubDate>${pubDate}</pubDate>
      <dc:creator>The Daily Clearing</dc:creator>
      ${categories}
      <description><![CDATA[${description}]]></description>
      <content:encoded><![CDATA[${content}]]></content:encoded>
    </item>`;
}

/**
 * Format digest title from date.
 */
function formatDigestTitle(generatedAt: string): string {
  const date = new Date(generatedAt);
  return `The Daily Clearing - ${date.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })}`;
}

/**
 * Build short description for RSS item.
 */
function buildDigestDescription(sections: DigestSection[]): string {
  const lines: string[] = [];

  for (const section of sections) {
    lines.push(`<h3>${escapeHtml(section.topic)}</h3>`);
    lines.push(`<p>${escapeHtml(section.sectionSummary)}</p>`);
    lines.push('<ul>');
    for (const article of section.articles.slice(0, 3)) {
      lines.push(`<li><a href="${escapeHtml(article.url)}">${escapeHtml(article.title)}</a></li>`);
    }
    if (section.articles.length > 3) {
      lines.push(`<li>...and ${section.articles.length - 3} more</li>`);
    }
    lines.push('</ul>');
  }

  return lines.join('\n');
}

/**
 * Build full HTML content for RSS item.
 */
function buildDigestContent(digest: Digest): string {
  const { sections, crossStoryConnections, skepticsSummary } = digest;
  const lines: string[] = [];

  // Header
  lines.push('<div style="font-family: Georgia, serif; max-width: 700px; margin: 0 auto;">');

  // Cross-story connections
  if (crossStoryConnections) {
    lines.push(`
      <div style="background: #f8f4ff; border-left: 4px solid #8b5cf6; padding: 16px; margin-bottom: 24px;">
        <h2 style="margin: 0 0 8px; font-size: 18px; color: #5b21b6;">Across the Stories</h2>
        <p style="margin: 0; color: #4c1d95;">${escapeHtml(crossStoryConnections)}</p>
      </div>
    `);
  }

  // Skeptic's summary
  if (skepticsSummary) {
    lines.push(`
      <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 16px; margin-bottom: 24px;">
        <h2 style="margin: 0 0 8px; font-size: 18px; color: #92400e;">Editor's Skeptic Note</h2>
        <p style="margin: 0; color: #78350f;">${escapeHtml(skepticsSummary)}</p>
      </div>
    `);
  }

  // Sections
  for (const section of sections) {
    lines.push(`
      <div style="margin-bottom: 32px;">
        <h2 style="font-size: 24px; margin: 0 0 8px; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px;">
          ${escapeHtml(section.topic)}
        </h2>
        <p style="color: #6b7280; margin: 0 0 16px; font-style: italic;">
          ${escapeHtml(section.sectionSummary)}
        </p>
    `);

    for (const article of section.articles) {
      lines.push(buildArticleHtml(article));
    }

    // Cross-story insights
    if (section.crossStoryInsights.length > 0) {
      lines.push(`
        <div style="background: #f3f4f6; padding: 12px; border-radius: 4px; margin-top: 16px;">
          <strong>Section Insights:</strong>
          <ul style="margin: 8px 0 0; padding-left: 20px;">
            ${section.crossStoryInsights.map((insight) => `<li>${escapeHtml(insight)}</li>`).join('')}
          </ul>
        </div>
      `);
    }

    lines.push('</div>');
  }

  // Footer
  lines.push(`
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 32px 0;">
    <p style="color: #9ca3af; font-size: 12px; text-align: center;">
      Generated by The Daily Clearing
    </p>
  `);

  lines.push('</div>');

  return lines.join('\n');
}

/**
 * Build HTML for a single article.
 */
function buildArticleHtml(article: Article): string {
  const lines: string[] = [];

  lines.push(`
    <div style="margin-bottom: 24px; padding: 16px; background: #fafafa; border-radius: 8px;">
      <h3 style="margin: 0 0 8px; font-size: 18px;">
        <a href="${escapeHtml(article.url)}" style="color: #1d4ed8; text-decoration: none;">
          ${escapeHtml(article.title)}
        </a>
      </h3>
      <p style="color: #6b7280; font-size: 12px; margin: 0 0 12px;">
        ${escapeHtml(article.source)}
        ${article.author ? ` · ${escapeHtml(article.author)}` : ''}
        ${article.publishedDate ? ` · ${escapeHtml(article.publishedDate)}` : ''}
        · ${article.readingTimeMinutes} min read
      </p>
      <p style="margin: 0 0 12px;">${escapeHtml(article.summary)}</p>
  `);

  // Key points
  if (article.keyPoints.length > 0) {
    lines.push(`
      <ul style="margin: 0 0 12px; padding-left: 20px;">
        ${article.keyPoints.map((point) => `<li>${escapeHtml(point)}</li>`).join('')}
      </ul>
    `);
  }

  // Why it matters
  if (article.whyMatters) {
    lines.push(`
      <div style="background: #ecfdf5; padding: 8px 12px; border-radius: 4px; margin-bottom: 8px;">
        <strong style="color: #065f46;">Why it matters:</strong>
        <span style="color: #047857;">${escapeHtml(article.whyMatters)}</span>
      </div>
    `);
  }

  // Skeptic's corner
  if (article.skepticsCorner) {
    lines.push(`
      <div style="background: #fef3c7; padding: 8px 12px; border-radius: 4px; margin-bottom: 8px;">
        <strong style="color: #92400e;">Skeptic's corner:</strong>
        <span style="color: #78350f;">${escapeHtml(article.skepticsCorner)}</span>
      </div>
    `);
  }

  // Red flags
  if (article.redFlags.length > 0) {
    lines.push(`
      <div style="background: #fef2f2; padding: 8px 12px; border-radius: 4px;">
        <strong style="color: #991b1b;">Red flags:</strong>
        <span style="color: #7f1d1d;">${article.redFlags.map(escapeHtml).join(', ')}</span>
      </div>
    `);
  }

  // Scores (subtle)
  lines.push(`
      <p style="color: #9ca3af; font-size: 11px; margin: 8px 0 0;">
        Relevance: ${Math.round(article.relevanceScore * 100)}%
        · Quality: ${Math.round(article.qualityScore * 100)}%
        · Tech level: ${article.technicalLevel}/5
      </p>
    </div>
  `);

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

/**
 * Escape HTML special characters.
 */
function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Parse RSS feed to extract items (for testing/validation).
 */
export function parseRssFeed(xml: string): Array<{ title: string; link: string; pubDate: string }> {
  const items: Array<{ title: string; link: string; pubDate: string }> = [];

  const itemRegex = /<item>([\s\S]*?)<\/item>/g;
  let match;

  while ((match = itemRegex.exec(xml)) !== null) {
    const itemXml = match[1];

    const titleMatch = itemXml.match(/<title>([^<]+)<\/title>/);
    const linkMatch = itemXml.match(/<link>([^<]+)<\/link>/);
    const pubDateMatch = itemXml.match(/<pubDate>([^<]+)<\/pubDate>/);

    if (titleMatch && linkMatch && pubDateMatch) {
      items.push({
        title: titleMatch[1],
        link: linkMatch[1],
        pubDate: pubDateMatch[1],
      });
    }
  }

  return items;
}
