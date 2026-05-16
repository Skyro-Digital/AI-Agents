import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const TOKEN = process.env.DISCORD_TOKEN!;
const BASE = "https://discord.com/api/v10";
const UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36";

const server = new McpServer({ name: "discord", version: "1.0.0" });

async function discordGet(path: string) {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { Authorization: TOKEN, "User-Agent": UA },
  });
  if (!resp.ok) throw new Error(`Discord API ${resp.status}: ${await resp.text()}`);
  return resp.json();
}

// Tool 1: List channels in a server
server.tool(
  "list_discord_channels",
  "List all text channels in a Discord server",
  {
    server_id: z.string().describe("Discord server (guild) ID"),
  },
  async ({ server_id }) => {
    try {
      const channels: any[] = await discordGet(`/guilds/${server_id}/channels`);
      const text = channels
        .filter((c) => c.type === 0)
        .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
        .map((c) => ({ id: c.id, name: c.name, topic: c.topic || "" }));

      return {
        content: [{ type: "text" as const, text: JSON.stringify({ server_id, channels: text }, null, 2) }],
      };
    } catch (error: any) {
      return { content: [{ type: "text" as const, text: `Error: ${error.message}` }], isError: true };
    }
  }
);

// Tool 2: Fetch recent messages from a channel
server.tool(
  "get_discord_messages",
  "Fetch recent messages from a Discord channel",
  {
    channel_id: z.string().describe("Discord channel ID"),
    limit: z.coerce.number().optional().default(50).describe("Number of messages to fetch (max 100, default 50)"),
    hours_ago: z.coerce.number().optional().default(168).describe("Only return messages from the last N hours (default 168 = 7 days)"),
  },
  async ({ channel_id, limit, hours_ago }) => {
    try {
      const messages: any[] = await discordGet(`/channels/${channel_id}/messages?limit=${Math.min(limit ?? 50, 100)}`);
      const cutoff = new Date(Date.now() - (hours_ago ?? 168) * 3600000);

      const filtered = messages
        .filter((m) => new Date(m.timestamp) >= cutoff && m.type === 0)
        .map((m) => ({
          id: m.id,
          author: m.author?.username ?? "unknown",
          timestamp: m.timestamp,
          content: m.content,
          attachments: m.attachments?.map((a: any) => a.url) ?? [],
          embeds: m.embeds?.map((e: any) => e.description || e.title || "").filter(Boolean) ?? [],
        }));

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              { channel_id, message_count: filtered.length, period: `Last ${hours_ago} hours`, messages: filtered },
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
