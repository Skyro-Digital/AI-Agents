import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const COOKIE = process.env.SUBSTACK_COOKIE!;
const UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36";

const server = new McpServer({
  name: "substack",
  version: "1.0.0",
});

/** Resolve a short handle like "citrini" → full API base URL, following redirects */
async function resolveBase(handle: string): Promise<string> {
  // Accept full domains or bare handles
  const base = handle.includes(".") ? handle : `${handle}.substack.com`;
  // Follow redirect to custom domain if present
  const resp = await fetch(`https://${base}/api/v1/posts?limit=1`, {
    headers: { Cookie: `substack.sid=${COOKIE}`, "User-Agent": UA },
    redirect: "follow",
  });
  // Get the resolved URL (after any redirects)
  const resolved = new URL(resp.url);
  return `${resolved.protocol}//${resolved.host}`;
}

/** Strip HTML tags and collapse whitespace */
function stripHtml(html: string): string {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// Tool 1: List recent posts
server.tool(
  "get_substack_posts",
  "List recent posts from a Substack publication (includes paid posts)",
  {
    handle: z.string().describe("Substack handle (e.g. 'citrini') or full domain (e.g. 'citriniresearch.com')"),
    limit: z.coerce.number().optional().default(10).describe("Number of posts to return (default 10)"),
    days_ago: z.coerce.number().optional().default(14).describe("Only return posts from the last N days (default 14)"),
  },
  async ({ handle, limit, days_ago }) => {
    try {
      const baseUrl = await resolveBase(handle);
      const resp = await fetch(`${baseUrl}/api/v1/posts?limit=${limit}`, {
        headers: { Cookie: `substack.sid=${COOKIE}`, "User-Agent": UA },
      });

      if (!resp.ok) {
        return { content: [{ type: "text" as const, text: `HTTP ${resp.status} fetching posts for ${handle}` }], isError: true };
      }

      const posts: any[] = await resp.json();
      const cutoff = new Date(Date.now() - days_ago * 86400000);

      const filtered = posts.filter((p: any) => new Date(p.post_date) >= cutoff);

      const results = filtered.map((p: any) => ({
        slug: p.slug,
        title: p.title,
        date: p.post_date?.slice(0, 10),
        audience: p.audience, // "everyone" or "only_paid"
        subtitle: p.subtitle || "",
        url: `${baseUrl}/p/${p.slug}`,
      }));

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({ handle, base_url: baseUrl, post_count: results.length, posts: results }, null, 2),
          },
        ],
      };
    } catch (error: any) {
      return { content: [{ type: "text" as const, text: `Error fetching posts for ${handle}: ${error.message}` }], isError: true };
    }
  }
);

// Tool 2: Fetch full article content
server.tool(
  "get_substack_article",
  "Fetch the full text of a Substack article (including paid content)",
  {
    handle: z.string().describe("Substack handle (e.g. 'citrini') or full domain"),
    slug: z.string().describe("Post slug from get_substack_posts"),
    max_chars: z.coerce.number().optional().default(12000).describe("Max characters to return (default 12000)"),
  },
  async ({ handle, slug, max_chars }) => {
    try {
      const baseUrl = await resolveBase(handle);
      const resp = await fetch(`${baseUrl}/api/v1/posts/${slug}`, {
        headers: { Cookie: `substack.sid=${COOKIE}`, "User-Agent": UA },
      });

      if (!resp.ok) {
        return { content: [{ type: "text" as const, text: `HTTP ${resp.status} fetching article ${slug}` }], isError: true };
      }

      const post: any = await resp.json();
      const bodyHtml: string = post.body_html || "";
      const fullText = stripHtml(bodyHtml);
      const truncated = fullText.slice(0, max_chars);
      const wasTruncated = fullText.length > max_chars;

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                title: post.title,
                date: post.post_date?.slice(0, 10),
                audience: post.audience,
                url: `${baseUrl}/p/${slug}`,
                word_count: fullText.split(" ").length,
                truncated: wasTruncated,
                body: truncated + (wasTruncated ? "\n\n[Article truncated]" : ""),
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (error: any) {
      return { content: [{ type: "text" as const, text: `Error fetching article ${slug}: ${error.message}` }], isError: true };
    }
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);
