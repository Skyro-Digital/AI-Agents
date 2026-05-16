import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const TOKEN = process.env.FATHOM_API_KEY!;
// NOTE: Verify exact base URL in Fathom account → Settings → API
const BASE = "https://api.fathom.video/v1";

const server = new McpServer({ name: "fathom", version: "1.0.0" });

async function fathomGet(path: string) {
  const resp = await fetch(`${BASE}${path}`, {
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      "Content-Type": "application/json",
    },
  });
  if (!resp.ok) throw new Error(`Fathom API ${resp.status}: ${await resp.text()}`);
  return resp.json();
}

// Tool 1: List recent calls, optionally filtered by date range and attendee name
server.tool(
  "get_fathom_calls",
  "List recent Fathom call recordings, optionally filtered by attendee name or date range",
  {
    days_ago: z.coerce.number().optional().default(7).describe("Only return calls from the last N days (default 7)"),
    limit: z.coerce.number().optional().default(50).describe("Max number of calls to return (default 50)"),
    attendee_name: z.string().optional().describe("Filter calls where this name appears as a participant (partial match, case-insensitive)"),
  },
  async ({ days_ago, limit, attendee_name }) => {
    try {
      const data: any = await fathomGet(`/calls?limit=${limit ?? 50}`);
      const cutoff = new Date(Date.now() - (days_ago ?? 7) * 86400000);

      // Normalize different possible response shapes from the API
      const items: any[] = data.calls ?? data.items ?? data.data ?? [];

      const filtered = items
        .filter((c) => {
          const callDate = new Date(c.created_at ?? c.date ?? c.started_at ?? 0);
          const dateMatch = callDate >= cutoff;
          const nameMatch =
            !attendee_name ||
            JSON.stringify(c.attendees ?? c.participants ?? [])
              .toLowerCase()
              .includes(attendee_name.toLowerCase());
          return dateMatch && nameMatch;
        })
        .slice(0, limit ?? 50)
        .map((c) => ({
          id: c.id,
          title: c.title ?? c.name ?? "(Untitled)",
          date: c.created_at ?? c.date ?? c.started_at,
          duration_minutes: c.duration ? Math.round(c.duration / 60) : null,
          attendees: c.attendees ?? c.participants ?? [],
          has_transcript: !!(c.transcript_id || c.has_transcript),
        }));

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              { call_count: filtered.length, period: `Last ${days_ago ?? 7} days`, calls: filtered },
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
            text: `Error fetching Fathom calls: ${error.message}\n\nTroubleshooting:\n- Verify FATHOM_API_KEY is set in .mcp.json\n- Check your Fathom account Settings → API for the correct API key\n- Confirm Fathom exposes an API at ${BASE}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// Tool 2: Fetch the full transcript of a specific call by ID
server.tool(
  "get_fathom_transcript",
  "Fetch the full transcript of a Fathom call recording by call ID",
  {
    call_id: z.string().describe("Fathom call ID (from get_fathom_calls)"),
  },
  async ({ call_id }) => {
    try {
      const data: any = await fathomGet(`/calls/${call_id}/transcript`);

      // Normalize different possible transcript response shapes
      const segments: any[] = data.segments ?? data.utterances ?? data.transcript ?? [];

      let text: string;
      if (segments.length > 0) {
        text = segments
          .map((s) => `[${s.speaker ?? s.name ?? s.speaker_name ?? "Unknown"}]: ${s.text ?? s.content ?? ""}`)
          .join("\n");
      } else {
        text = data.text ?? data.content ?? JSON.stringify(data);
      }

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              { call_id, segment_count: segments.length, transcript: text },
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
            text: `Error fetching transcript for call ${call_id}: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);
