import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const TOKEN = process.env.BITCOIN_LIVE_TOKEN!;
const API = "https://api.bitcoin.live/api";
const HEADERS = { "Content-Type": "application/json", "X-Auth-Token": TOKEN };

const server = new McpServer({ name: "bitcoin-live", version: "1.0.0" });

function stripHtml(html: string): string {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

// Tool 1: List recent posts by a specific author
server.tool(
  "get_bitcoin_live_posts",
  "List recent posts from bitcoin.live for a specific author (e.g. Bob Loukas)",
  {
    author_name: z.string().describe("Author name to filter by (e.g. 'Bob Loukas')"),
    days_ago: z.coerce.number().optional().default(7).describe("Only return posts from last N days (default 7)"),
    limit: z.coerce.number().optional().default(20).describe("Max posts to scan from the feed (default 20)"),
  },
  async ({ author_name, days_ago, limit }) => {
    try {
      const resp = await fetch(`${API}/post/search/10/0`, {
        method: "POST",
        headers: HEADERS,
        body: JSON.stringify({}),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: any = await resp.json();

      const cutoff = new Date(Date.now() - (days_ago ?? 7) * 86400000);
      const items: any[] = data.items ?? [];

      const filtered = items
        .filter((p) => {
          const authorMatch = !author_name || p.author?.name?.toLowerCase().includes(author_name.toLowerCase());
          const dateMatch = new Date(p.publishedAt) >= cutoff;
          return authorMatch && dateMatch;
        })
        .slice(0, limit ?? 20)
        .map((p) => ({
          id: p.id,
          slug: p.slug,
          title: p.title,
          date: p.publishedAt?.slice(0, 10),
          author: p.author?.name,
          excerpt: stripHtml(p.excerpt || ""),
          has_video: !!p.embeddedVideo?.mediaId,
        }));

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({ author: author_name, post_count: filtered.length, posts: filtered }, null, 2),
          },
        ],
      };
    } catch (error: any) {
      return { content: [{ type: "text" as const, text: `Error: ${error.message}` }], isError: true };
    }
  }
);

// Tool 2: Fetch full content of a post by slug
server.tool(
  "get_bitcoin_live_post",
  "Fetch the full content of a bitcoin.live post by slug",
  {
    slug: z.string().describe("Post slug from get_bitcoin_live_posts"),
    max_chars: z.coerce.number().optional().default(10000).describe("Max characters to return (default 10000)"),
  },
  async ({ slug, max_chars }) => {
    try {
      const resp = await fetch(`${API}/post/by-slug/${slug}`, { headers: HEADERS });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const post: any = await resp.json();

      const fullText = stripHtml(post.content || "");
      const truncated = fullText.slice(0, max_chars ?? 10000);
      const wasTruncated = fullText.length > (max_chars ?? 10000);
      const hasVideo = !!post.embeddedVideo?.mediaId;

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                title: post.title,
                author: post.author?.name,
                date: post.publishedAt?.slice(0, 10),
                url: `https://bitcoin.live/post/${slug}`,
                word_count: fullText.split(" ").length,
                has_video: hasVideo,
                video_note: hasVideo ? `Embedded video (Wistia ID: ${post.embeddedVideo.mediaId}) — text content only` : undefined,
                truncated: wasTruncated,
                content: truncated + (wasTruncated ? "\n\n[Truncated]" : ""),
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (error: any) {
      return { content: [{ type: "text" as const, text: `Error: ${error.message}` }], isError: true };
    }
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);
