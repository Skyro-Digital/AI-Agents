import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const BEARER_TOKEN = process.env.X_BEARER_TOKEN;
if (!BEARER_TOKEN) {
  console.error("X_BEARER_TOKEN environment variable is required");
  process.exit(1);
}

const API_BASE = "https://api.x.com/2";

async function xApiRequest(endpoint: string, params?: Record<string, string>): Promise<any> {
  const url = new URL(`${API_BASE}${endpoint}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      url.searchParams.set(key, value);
    }
  }

  const response = await fetch(url.toString(), {
    headers: {
      Authorization: `Bearer ${BEARER_TOKEN}`,
    },
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`X API error ${response.status}: ${errorBody}`);
  }

  return response.json();
}

// Cache username -> user ID lookups to avoid repeated API calls
const userIdCache = new Map<string, string>();

async function getUserId(username: string): Promise<string> {
  const cleanUsername = username.replace(/^@/, "");
  const cached = userIdCache.get(cleanUsername);
  if (cached) return cached;

  const data = await xApiRequest(`/users/by/username/${cleanUsername}`);
  if (!data.data?.id) {
    throw new Error(`User not found: ${cleanUsername}`);
  }

  userIdCache.set(cleanUsername, data.data.id);
  return data.data.id;
}

const server = new McpServer({
  name: "x-twitter",
  version: "1.0.0",
});

server.tool(
  "get_user_tweets",
  "Fetch recent tweets from a specific X/Twitter user by username",
  {
    username: z.string().describe("X/Twitter username (with or without @)"),
    max_results: z
      .number()
      .min(5)
      .max(100)
      .default(10)
      .describe("Number of tweets to return (5-100, default 10)"),
    hours_ago: z
      .number()
      .default(168)
      .describe("Only return tweets from the last N hours (default 168 = 7 days)"),
  },
  async ({ username, max_results, hours_ago }) => {
    try {
      const userId = await getUserId(username);

      const startTime = new Date(Date.now() - hours_ago * 60 * 60 * 1000).toISOString();

      const data = await xApiRequest(`/users/${userId}/tweets`, {
        max_results: String(max_results),
        start_time: startTime,
        "tweet.fields": "created_at,text,public_metrics",
        exclude: "retweets,replies",
      });

      if (!data.data || data.data.length === 0) {
        return {
          content: [
            {
              type: "text" as const,
              text: `No tweets found for @${username.replace(/^@/, "")} in the last ${hours_ago} hours.`,
            },
          ],
        };
      }

      const tweets = data.data.map((tweet: any) => ({
        text: tweet.text,
        created_at: tweet.created_at,
        likes: tweet.public_metrics?.like_count ?? 0,
        retweets: tweet.public_metrics?.retweet_count ?? 0,
        replies: tweet.public_metrics?.reply_count ?? 0,
      }));

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                username: username.replace(/^@/, ""),
                tweet_count: tweets.length,
                period: `Last ${hours_ago} hours`,
                tweets,
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
            text: `Error fetching tweets for @${username.replace(/^@/, "")}: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }
);

server.tool(
  "search_recent_tweets",
  "Search for recent tweets matching a query across all of X/Twitter",
  {
    query: z
      .string()
      .describe(
        'Search query. Supports X search operators like "from:username", "BTC", etc.'
      ),
    max_results: z
      .number()
      .min(10)
      .max(100)
      .default(10)
      .describe("Number of tweets to return (10-100, default 10)"),
  },
  async ({ query, max_results }) => {
    try {
      const data = await xApiRequest("/tweets/search/recent", {
        query,
        max_results: String(max_results),
        "tweet.fields": "created_at,text,public_metrics,author_id",
      });

      if (!data.data || data.data.length === 0) {
        return {
          content: [
            {
              type: "text" as const,
              text: `No tweets found for query: "${query}"`,
            },
          ],
        };
      }

      const tweets = data.data.map((tweet: any) => ({
        text: tweet.text,
        created_at: tweet.created_at,
        author_id: tweet.author_id,
        likes: tweet.public_metrics?.like_count ?? 0,
        retweets: tweet.public_metrics?.retweet_count ?? 0,
      }));

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                query,
                result_count: tweets.length,
                tweets,
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
            text: `Error searching tweets: ${error.message}`,
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
  console.error("X Twitter MCP server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
