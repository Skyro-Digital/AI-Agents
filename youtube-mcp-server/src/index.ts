import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { execFile } from "child_process";
import { promisify } from "util";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { z } from "zod";

const execFileAsync = promisify(execFile);
const PYTHON = "/Library/Developer/CommandLineTools/usr/bin/python3";
const __dirname = dirname(fileURLToPath(import.meta.url));
const TRANSCRIPT_SCRIPT = join(__dirname, "..", "get_transcript.py");

const API_KEY = process.env.YOUTUBE_API_KEY;
if (!API_KEY) {
  console.error("YOUTUBE_API_KEY environment variable is required");
  process.exit(1);
}

const YT_API_BASE = "https://www.googleapis.com/youtube/v3";

async function ytApiRequest(endpoint: string, params: Record<string, string>): Promise<any> {
  const url = new URL(`${YT_API_BASE}${endpoint}`);
  url.searchParams.set("key", API_KEY!);
  for (const [key, value] of Object.entries(params)) {
    url.searchParams.set(key, value);
  }

  const response = await fetch(url.toString());
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`YouTube API error ${response.status}: ${errorBody}`);
  }
  return response.json();
}

// Cache channel handle -> uploads playlist ID
const uploadsPlaylistCache = new Map<string, string>();

async function getUploadsPlaylistId(channelHandle: string): Promise<string> {
  const cleanHandle = channelHandle.replace(/^@/, "");
  const cached = uploadsPlaylistCache.get(cleanHandle);
  if (cached) return cached;

  const data = await ytApiRequest("/channels", {
    forHandle: cleanHandle,
    part: "contentDetails",
  });

  const playlistId = data.items?.[0]?.contentDetails?.relatedPlaylists?.uploads;
  if (!playlistId) {
    throw new Error(`Channel not found or no uploads playlist: @${cleanHandle}`);
  }

  uploadsPlaylistCache.set(cleanHandle, playlistId);
  return playlistId;
}

const server = new McpServer({
  name: "youtube",
  version: "1.0.0",
});

server.tool(
  "get_channel_recent_videos",
  "Get recent videos from a YouTube channel by handle",
  {
    channel_handle: z
      .string()
      .describe("YouTube channel handle (with or without @), e.g. 'ColdBloodedShiller'"),
    days_ago: z
      .coerce.number()
      .default(7)
      .describe("Only return videos published in the last N days (default 7)"),
    max_results: z
      .coerce.number()
      .min(1)
      .max(10)
      .default(5)
      .describe("Max number of videos to return (1-10, default 5)"),
  },
  async ({ channel_handle, days_ago, max_results }) => {
    try {
      const playlistId = await getUploadsPlaylistId(channel_handle);

      const data = await ytApiRequest("/playlistItems", {
        playlistId,
        part: "snippet",
        maxResults: "10",
      });

      if (!data.items || data.items.length === 0) {
        return {
          content: [{ type: "text" as const, text: `No videos found for @${channel_handle}` }],
        };
      }

      const cutoff = new Date(Date.now() - days_ago * 24 * 60 * 60 * 1000);

      const videos = data.items
        .filter((item: any) => {
          const published = new Date(item.snippet.publishedAt);
          return published >= cutoff;
        })
        .slice(0, max_results)
        .map((item: any) => ({
          video_id: item.snippet.resourceId.videoId,
          title: item.snippet.title,
          published_at: item.snippet.publishedAt,
          description: item.snippet.description?.slice(0, 300) ?? "",
          url: `https://www.youtube.com/watch?v=${item.snippet.resourceId.videoId}`,
        }));

      if (videos.length === 0) {
        return {
          content: [
            {
              type: "text" as const,
              text: `No videos found for @${channel_handle} in the last ${days_ago} days.`,
            },
          ],
        };
      }

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                channel: channel_handle,
                videos_found: videos.length,
                period: `Last ${days_ago} days`,
                videos,
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (error: any) {
      return {
        content: [{ type: "text" as const, text: `Error fetching videos for @${channel_handle}: ${error.message}` }],
        isError: true,
      };
    }
  }
);

server.tool(
  "get_video_transcript",
  "Fetch the auto-generated transcript of a YouTube video by video ID",
  {
    video_id: z.string().describe("YouTube video ID (the part after ?v= in the URL)"),
  },
  async ({ video_id }) => {
    try {
      const { stdout } = await execFileAsync(PYTHON, [TRANSCRIPT_SCRIPT, video_id], {
        timeout: 30000,
      });

      const result = JSON.parse(stdout.trim());

      if (result.error) {
        return {
          content: [{ type: "text" as const, text: `No transcript available for video ${video_id}: ${result.error}` }],
          isError: true,
        };
      }

      const fullText: string = result.transcript;
      const truncated = fullText.slice(0, 8000);
      const wasTruncated = fullText.length > 8000;

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                video_id,
                url: `https://www.youtube.com/watch?v=${video_id}`,
                word_count: result.word_count,
                truncated: wasTruncated,
                transcript: truncated + (wasTruncated ? "\n\n[Transcript truncated at 8000 chars]" : ""),
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (error: any) {
      return {
        content: [
          {
            type: "text" as const,
            text: `Error fetching transcript for video ${video_id}: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("YouTube MCP server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
