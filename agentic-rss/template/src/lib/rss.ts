import type { Article, FeedMeta } from "../types";

function escapeXml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function rfc822(date: Date): string {
  return date.toUTCString();
}

export function renderRss(meta: FeedMeta, articles: Article[]): string {
  const items = articles
    .map((a) => {
      const lines: string[] = [
        `<title>${escapeXml(a.title)}</title>`,
        `<link>${escapeXml(a.link)}</link>`,
        `<guid isPermaLink="false">${escapeXml(a.id)}</guid>`,
      ];
      if (a.published) lines.push(`<pubDate>${rfc822(a.published)}</pubDate>`);
      if (a.author) lines.push(`<author>${escapeXml(a.author)}</author>`);
      if (a.summary) {
        lines.push(`<description>${escapeXml(a.summary)}</description>`);
      }
      return `<item>${lines.join("")}</item>`;
    })
    .join("");

  const lang = meta.language
    ? `<language>${escapeXml(meta.language)}</language>`
    : "";

  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>${escapeXml(meta.title)}</title>
<link>${escapeXml(meta.link)}</link>
<description>${escapeXml(meta.description ?? meta.title)}</description>
${lang}
<lastBuildDate>${rfc822(new Date())}</lastBuildDate>
${items}
</channel>
</rss>`;
}
