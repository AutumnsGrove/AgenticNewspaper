/**
 * Email Delivery Service.
 *
 * Sends digest emails via Resend API.
 */

import type { Env, Digest, DigestSection, Article } from '../types';

interface EmailOptions {
  to: string;
  subject: string;
  html: string;
  text: string;
  from?: string;
  replyTo?: string;
  tags?: Array<{ name: string; value: string }>;
}

interface ResendResponse {
  id: string;
}

/**
 * Send email via Resend API.
 */
export async function sendEmail(
  env: Env,
  options: EmailOptions
): Promise<{ success: boolean; id?: string; error?: string }> {
  const apiKey = env.RESEND_API_KEY;

  if (!apiKey) {
    return { success: false, error: 'RESEND_API_KEY not configured' };
  }

  try {
    const response = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: options.from || 'The Daily Clearing <digest@clearing.autumnsgrove.com>',
        to: [options.to],
        subject: options.subject,
        html: options.html,
        text: options.text,
        reply_to: options.replyTo,
        tags: options.tags,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      return { success: false, error: `Resend API error: ${error}` };
    }

    const result = (await response.json()) as ResendResponse;
    return { success: true, id: result.id };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error sending email',
    };
  }
}

/**
 * Send digest email to user.
 */
export async function sendDigestEmail(
  env: Env,
  options: {
    to: string;
    userId: string;
    digestId: string;
    digest: Digest;
    unsubscribeUrl: string;
    webUrl: string;
  }
): Promise<{ success: boolean; id?: string; error?: string }> {
  const { to, userId, digestId, digest, unsubscribeUrl, webUrl } = options;

  const subject = formatEmailSubject(digest);
  const html = buildEmailHtml(digest, { unsubscribeUrl, webUrl, digestId });
  const text = buildEmailText(digest);

  return sendEmail(env, {
    to,
    subject,
    html,
    text,
    tags: [
      { name: 'user_id', value: userId },
      { name: 'digest_id', value: digestId },
      { name: 'type', value: 'digest' },
    ],
  });
}

/**
 * Format email subject line.
 */
function formatEmailSubject(digest: Digest): string {
  const date = new Date(digest.metadata.generatedAt);
  const dateStr = date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });

  const topicCount = digest.sections.length;
  const articleCount = digest.metadata.totalArticlesIncluded;

  return `The Daily Clearing - ${dateStr} (${articleCount} articles across ${topicCount} topics)`;
}

/**
 * Build HTML email content.
 */
function buildEmailHtml(
  digest: Digest,
  options: { unsubscribeUrl: string; webUrl: string; digestId: string }
): string {
  const { unsubscribeUrl, webUrl, digestId } = options;
  const { sections, crossStoryConnections, skepticsSummary, metadata } = digest;

  return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The Daily Clearing</title>
  <!--[if mso]>
  <noscript>
    <xml>
      <o:OfficeDocumentSettings>
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml>
  </noscript>
  <![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: Georgia, 'Times New Roman', serif;">
  <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f5f5f5;">
    <tr>
      <td style="padding: 20px 0;">
        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden;">

          <!-- Header -->
          <tr>
            <td style="background-color: #1a1a1a; padding: 32px 24px; text-align: center;">
              <h1 style="margin: 0; color: #ffffff; font-size: 32px; font-weight: normal; letter-spacing: 2px;">
                THE DAILY CLEARING
              </h1>
              <p style="margin: 8px 0 0; color: #9ca3af; font-size: 14px;">
                ${formatEmailDate(metadata.generatedAt)}
              </p>
            </td>
          </tr>

          <!-- View in Browser Link -->
          <tr>
            <td style="padding: 16px 24px; text-align: center; border-bottom: 1px solid #e5e7eb;">
              <a href="${webUrl}/digest/${digestId}" style="color: #3b82f6; font-size: 14px;">
                View in browser &rarr;
              </a>
            </td>
          </tr>

          ${crossStoryConnections ? buildCrossConnectionsHtml(crossStoryConnections) : ''}

          ${skepticsSummary ? buildSkepticSummaryHtml(skepticsSummary) : ''}

          ${sections.map((section) => buildSectionHtml(section)).join('')}

          <!-- Stats -->
          <tr>
            <td style="padding: 24px; background-color: #f9fafb; border-top: 1px solid #e5e7eb;">
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                <tr>
                  <td style="text-align: center; padding: 8px;">
                    <span style="color: #6b7280; font-size: 12px;">Articles scanned</span><br>
                    <span style="color: #1f2937; font-size: 18px; font-weight: bold;">${metadata.totalArticlesFound}</span>
                  </td>
                  <td style="text-align: center; padding: 8px;">
                    <span style="color: #6b7280; font-size: 12px;">Included</span><br>
                    <span style="color: #1f2937; font-size: 18px; font-weight: bold;">${metadata.totalArticlesIncluded}</span>
                  </td>
                  <td style="text-align: center; padding: 8px;">
                    <span style="color: #6b7280; font-size: 12px;">Topics</span><br>
                    <span style="color: #1f2937; font-size: 18px; font-weight: bold;">${metadata.topicsCovered.length}</span>
                  </td>
                  <td style="text-align: center; padding: 8px;">
                    <span style="color: #6b7280; font-size: 12px;">Cost</span><br>
                    <span style="color: #1f2937; font-size: 18px; font-weight: bold;">$${metadata.totalCostUsd.toFixed(3)}</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 24px; background-color: #1a1a1a; text-align: center;">
              <p style="margin: 0 0 16px; color: #9ca3af; font-size: 12px;">
                You're receiving this because you subscribed to The Daily Clearing.
              </p>
              <p style="margin: 0;">
                <a href="${unsubscribeUrl}" style="color: #6b7280; font-size: 12px; text-decoration: underline;">
                  Unsubscribe
                </a>
                &nbsp;&nbsp;|&nbsp;&nbsp;
                <a href="${webUrl}/settings" style="color: #6b7280; font-size: 12px; text-decoration: underline;">
                  Manage preferences
                </a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
  `.trim();
}

/**
 * Build cross-connections HTML section.
 */
function buildCrossConnectionsHtml(connections: string): string {
  return `
    <tr>
      <td style="padding: 24px; background-color: #f5f3ff; border-bottom: 1px solid #e5e7eb;">
        <h2 style="margin: 0 0 8px; font-size: 16px; color: #5b21b6;">Across the Stories</h2>
        <p style="margin: 0; color: #4c1d95; font-size: 14px; line-height: 1.6;">${escapeHtml(connections)}</p>
      </td>
    </tr>
  `;
}

/**
 * Build skeptic summary HTML section.
 */
function buildSkepticSummaryHtml(summary: string): string {
  return `
    <tr>
      <td style="padding: 24px; background-color: #fffbeb; border-bottom: 1px solid #e5e7eb;">
        <h2 style="margin: 0 0 8px; font-size: 16px; color: #92400e;">Editor's Skeptic Note</h2>
        <p style="margin: 0; color: #78350f; font-size: 14px; line-height: 1.6;">${escapeHtml(summary)}</p>
      </td>
    </tr>
  `;
}

/**
 * Build section HTML.
 */
function buildSectionHtml(section: DigestSection): string {
  const articlesHtml = section.articles.map((article) => buildArticleEmailHtml(article)).join('');

  return `
    <tr>
      <td style="padding: 24px; border-bottom: 1px solid #e5e7eb;">
        <h2 style="margin: 0 0 8px; font-size: 20px; color: #1f2937; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px;">
          ${escapeHtml(section.topic)}
        </h2>
        <p style="margin: 0 0 16px; color: #6b7280; font-size: 14px; font-style: italic;">
          ${escapeHtml(section.sectionSummary)}
        </p>
        ${articlesHtml}
        ${section.crossStoryInsights.length > 0 ? buildInsightsHtml(section.crossStoryInsights) : ''}
      </td>
    </tr>
  `;
}

/**
 * Build article HTML for email.
 */
function buildArticleEmailHtml(article: Article): string {
  return `
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 16px;">
      <tr>
        <td style="background-color: #f9fafb; padding: 16px; border-radius: 8px;">
          <h3 style="margin: 0 0 8px; font-size: 16px;">
            <a href="${escapeHtml(article.url)}" style="color: #1d4ed8; text-decoration: none;">
              ${escapeHtml(article.title)}
            </a>
          </h3>
          <p style="margin: 0 0 12px; color: #6b7280; font-size: 12px;">
            ${escapeHtml(article.source)}
            ${article.author ? ` · ${escapeHtml(article.author)}` : ''}
            · ${article.readingTimeMinutes} min read
          </p>
          <p style="margin: 0 0 12px; color: #374151; font-size: 14px; line-height: 1.6;">
            ${escapeHtml(article.summary)}
          </p>
          ${article.keyPoints.length > 0 ? buildKeyPointsHtml(article.keyPoints) : ''}
          ${article.whyMatters ? buildWhyMattersHtml(article.whyMatters) : ''}
          ${article.skepticsCorner ? buildSkepticsCornerHtml(article.skepticsCorner) : ''}
        </td>
      </tr>
    </table>
  `;
}

/**
 * Build key points HTML.
 */
function buildKeyPointsHtml(points: string[]): string {
  return `
    <ul style="margin: 0 0 12px; padding-left: 20px; color: #374151; font-size: 14px;">
      ${points.map((point) => `<li style="margin-bottom: 4px;">${escapeHtml(point)}</li>`).join('')}
    </ul>
  `;
}

/**
 * Build why matters HTML.
 */
function buildWhyMattersHtml(text: string): string {
  return `
    <p style="margin: 0 0 8px; padding: 8px 12px; background-color: #ecfdf5; border-radius: 4px; font-size: 13px;">
      <strong style="color: #065f46;">Why it matters:</strong>
      <span style="color: #047857;">${escapeHtml(text)}</span>
    </p>
  `;
}

/**
 * Build skeptic's corner HTML.
 */
function buildSkepticsCornerHtml(text: string): string {
  return `
    <p style="margin: 0; padding: 8px 12px; background-color: #fef3c7; border-radius: 4px; font-size: 13px;">
      <strong style="color: #92400e;">Skeptic's corner:</strong>
      <span style="color: #78350f;">${escapeHtml(text)}</span>
    </p>
  `;
}

/**
 * Build insights HTML.
 */
function buildInsightsHtml(insights: string[]): string {
  return `
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-top: 12px;">
      <tr>
        <td style="background-color: #f3f4f6; padding: 12px; border-radius: 4px;">
          <strong style="font-size: 13px; color: #374151;">Section Insights:</strong>
          <ul style="margin: 8px 0 0; padding-left: 20px; color: #4b5563; font-size: 13px;">
            ${insights.map((insight) => `<li style="margin-bottom: 4px;">${escapeHtml(insight)}</li>`).join('')}
          </ul>
        </td>
      </tr>
    </table>
  `;
}

/**
 * Format date for email header.
 */
function formatEmailDate(isoDate: string): string {
  const date = new Date(isoDate);
  return date.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

/**
 * Build plain text email content.
 */
function buildEmailText(digest: Digest): string {
  const lines: string[] = [];
  const { sections, crossStoryConnections, skepticsSummary, metadata } = digest;

  lines.push('THE DAILY CLEARING');
  lines.push('='.repeat(50));
  lines.push(formatEmailDate(metadata.generatedAt));
  lines.push('');

  if (crossStoryConnections) {
    lines.push('ACROSS THE STORIES');
    lines.push('-'.repeat(30));
    lines.push(crossStoryConnections);
    lines.push('');
  }

  if (skepticsSummary) {
    lines.push("EDITOR'S SKEPTIC NOTE");
    lines.push('-'.repeat(30));
    lines.push(skepticsSummary);
    lines.push('');
  }

  for (const section of sections) {
    lines.push('');
    lines.push(section.topic.toUpperCase());
    lines.push('='.repeat(section.topic.length));
    lines.push(section.sectionSummary);
    lines.push('');

    for (const article of section.articles) {
      lines.push(`* ${article.title}`);
      lines.push(`  ${article.source}${article.author ? ` · ${article.author}` : ''}`);
      lines.push(`  ${article.url}`);
      lines.push('');
      lines.push(`  ${article.summary}`);
      lines.push('');

      if (article.keyPoints.length > 0) {
        lines.push('  Key points:');
        for (const point of article.keyPoints) {
          lines.push(`    - ${point}`);
        }
        lines.push('');
      }

      if (article.whyMatters) {
        lines.push(`  Why it matters: ${article.whyMatters}`);
        lines.push('');
      }

      if (article.skepticsCorner) {
        lines.push(`  Skeptic's corner: ${article.skepticsCorner}`);
        lines.push('');
      }

      lines.push('-'.repeat(40));
    }

    if (section.crossStoryInsights.length > 0) {
      lines.push('');
      lines.push('Section insights:');
      for (const insight of section.crossStoryInsights) {
        lines.push(`  * ${insight}`);
      }
    }
  }

  lines.push('');
  lines.push('='.repeat(50));
  lines.push('DIGEST STATS');
  lines.push(`Articles scanned: ${metadata.totalArticlesFound}`);
  lines.push(`Articles included: ${metadata.totalArticlesIncluded}`);
  lines.push(`Topics covered: ${metadata.topicsCovered.length}`);
  lines.push(`Cost: $${metadata.totalCostUsd.toFixed(3)}`);
  lines.push('');

  return lines.join('\n');
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
