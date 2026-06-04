# YouTube Benchmark Planner MVP Implementation Plan

> **For agentic workers:** Use `subagent-driven-development` only when sub-agent delegation is explicitly authorized; otherwise use `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Next.js web app that analyzes one benchmark YouTube channel's latest 50 videos and generates five reverse-planned video ideas with title, thumbnail, and hook structure.

**Architecture:** Create a new project at `/Users/gimseung-an/youtube-benchmark-planner` instead of adding code to the existing Premiere relink repo. Keep the app small: one API route orchestrates YouTube collection, optional transcript enrichment, deterministic analysis, OpenAI structured plan generation, and Markdown export helpers. UI is a single-page workflow with API-key/channel inputs, optional profile inputs, analysis progress, dashboard results, and plan cards.

**Tech Stack:** Next.js App Router, TypeScript, Tailwind CSS, Vitest, Zod, OpenAI Responses API structured outputs, YouTube Data API REST endpoints, `youtube-transcript` as optional best-effort transcript enrichment.

Spec: `docs/superpowers/specs/2026-06-04-youtube-channel-benchmark-planner-design.md`

OpenAI reference checked: Structured Outputs guide and Responses API reference recommend schema-backed structured output over JSON mode for supported models. The model guide lists `gpt-5.2` as the current most capable model family and `gpt-5-mini` as the cost-optimized smaller option; this MVP defaults to `gpt-5-mini` via `OPENAI_MODEL` so cost stays sane while remaining configurable.

---

## File Structure

Create this new project:

```text
/Users/gimseung-an/youtube-benchmark-planner/
├── .env.example                         # Required server-side env vars, no secrets
├── package.json                         # Scripts and dependencies
├── src/
│   ├── app/
│   │   ├── api/analyze/route.ts          # POST endpoint: collect → analyze → generate
│   │   ├── globals.css                   # Tailwind base plus app-level polish
│   │   ├── layout.tsx                    # App shell metadata
│   │   └── page.tsx                      # Single-screen MVP UI
│   └── lib/
│       ├── analysis.ts                   # Metrics, top videos, hook tags, insight summary
│       ├── analysis.test.ts
│       ├── hook-framework.ts             # Built-in compressed hook framework
│       ├── markdown.ts                   # Markdown report generation
│       ├── markdown.test.ts
│       ├── planner.ts                    # OpenAI structured plan generation
│       ├── planner.test.ts
│       ├── schemas.ts                    # Zod schemas and exported TS types
│       ├── transcript.ts                 # Best-effort transcript wrapper
│       ├── transcript.test.ts
│       ├── youtube.ts                    # URL parsing + YouTube Data API REST client
│       └── youtube.test.ts
└── vitest.config.ts
```

Boundary rules:

- `youtube.ts` does network collection only. It returns normalized internal types.
- `transcript.ts` may fail per video and returns status objects, never throws for ordinary missing transcripts.
- `analysis.ts` is deterministic and test-heavy.
- `planner.ts` is the only OpenAI client boundary. Tests mock the OpenAI call.
- `route.ts` validates input, orchestrates modules, and maps errors to user-facing messages.
- `page.tsx` owns UI state only; it does not calculate analysis logic.

---

## Task 0: Scaffold The New Next.js Project

**Files:**
- Create project directory: `/Users/gimseung-an/youtube-benchmark-planner`
- Modify: `/Users/gimseung-an/youtube-benchmark-planner/package.json`
- Create: `/Users/gimseung-an/youtube-benchmark-planner/.env.example`
- Create: `/Users/gimseung-an/youtube-benchmark-planner/vitest.config.ts`

- [ ] **Step 1: Create the app**

Run:

```bash
cd /Users/gimseung-an
npx create-next-app@latest youtube-benchmark-planner --typescript --eslint --tailwind --app --src-dir --import-alias "@/*" --use-npm
```

Expected: a new Next.js app exists at `/Users/gimseung-an/youtube-benchmark-planner`.

- [ ] **Step 2: Install runtime and test dependencies**

Run:

```bash
cd /Users/gimseung-an/youtube-benchmark-planner
npm install openai@^6.42.0 zod@^4.4.3 youtube-transcript@^1.3.1
npm install -D vitest@latest jsdom@latest @testing-library/react@latest @testing-library/jest-dom@latest
```

Expected: `package-lock.json` updates and install exits with code 0.

- [ ] **Step 3: Update scripts in `package.json`**

Modify `package.json` so the `scripts` object is exactly:

```json
{
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "eslint",
  "typecheck": "tsc --noEmit",
  "test": "vitest run --passWithNoTests",
  "test:watch": "vitest"
}
```

- [ ] **Step 4: Add `.env.example`**

```bash
# /Users/gimseung-an/youtube-benchmark-planner/.env.example
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
```

Do not put YouTube API keys here. The MVP accepts a YouTube API key in the local web UI and sends it only to the local API route for the current request.

- [ ] **Step 5: Add `vitest.config.ts`**

```ts
// /Users/gimseung-an/youtube-benchmark-planner/vitest.config.ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});
```

- [ ] **Step 6: Run baseline checks**

Run:

```bash
cd /Users/gimseung-an/youtube-benchmark-planner
npm run typecheck
npm run test
```

Expected: typecheck passes; tests report no test files or pass if the scaffold generated any.

- [ ] **Step 7: Commit**

Run:

```bash
cd /Users/gimseung-an/youtube-benchmark-planner
git add .
git commit -m "chore: scaffold youtube benchmark planner"
```

---

## Task 1: Define Shared Schemas And Types

**Files:**
- Create: `src/lib/schemas.ts`

- [ ] **Step 1: Create `src/lib/schemas.ts`**

```ts
// src/lib/schemas.ts
import { z } from "zod";

export const UserProfileSchema = z.object({
  topic: z.string().trim().optional().default(""),
  audience: z.string().trim().optional().default(""),
  tone: z.string().trim().optional().default(""),
  avoidStyle: z.string().trim().optional().default(""),
  preferredLength: z.string().trim().optional().default(""),
  currentProblem: z.string().trim().optional().default(""),
});

export const AnalyzeRequestSchema = z.object({
  youtubeApiKey: z.string().trim().min(1, "YouTube API key is required"),
  channelUrl: z.string().trim().url("Enter a valid YouTube channel URL"),
  profile: UserProfileSchema.optional().default({}),
});

export const ChannelSummarySchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  subscriberCount: z.number().nullable(),
  viewCount: z.number(),
  videoCount: z.number(),
  uploadsPlaylistId: z.string(),
});

export const TranscriptStatusSchema = z.enum([
  "available",
  "missing",
  "failed",
  "not_requested",
]);

export const VideoSummarySchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  thumbnailUrl: z.string(),
  publishedAt: z.string(),
  durationSeconds: z.number(),
  viewCount: z.number(),
  likeCount: z.number().nullable(),
  commentCount: z.number().nullable(),
  tags: z.array(z.string()),
  categoryId: z.string().optional(),
  transcriptStatus: TranscriptStatusSchema.default("not_requested"),
  transcriptPreview: z.string().optional(),
});

export const PerformanceVideoSchema = VideoSummarySchema.extend({
  performanceRatio: z.number(),
  performanceLabel: z.enum(["breakout", "strong", "normal", "weak"]),
  hookTags: z.array(z.string()),
  inferredFormat: z.string(),
});

export const AnalysisSummarySchema = z.object({
  averageViews: z.number(),
  medianViews: z.number(),
  topVideos: z.array(PerformanceVideoSchema),
  titlePatterns: z.array(z.string()),
  hookPatterns: z.array(z.string()),
  contentClusters: z.array(z.string()),
  uploadPattern: z.string(),
  lengthPattern: z.string(),
  warnings: z.array(z.string()),
});

export const ThumbnailPlanSchema = z.object({
  copy: z.string(),
  layout: z.string(),
  visual_emotion: z.string(),
});

export const TimelineSchema = z.object({
  "0_3": z.string(),
  "3_15": z.string(),
  "15_30": z.string(),
  "30_90": z.string(),
  ending: z.string(),
});

export const VideoPlanSchema = z.object({
  concept: z.string(),
  titles: z.array(z.string()).length(3),
  thumbnails: z.array(ThumbnailPlanSchema).length(3),
  hook_5s: z.string(),
  hook_30s: z.string(),
  timeline: TimelineSchema,
  body_outline: z.array(z.string()).min(3).max(7),
  mechanisms: z.array(z.string()).min(1),
  benchmark_basis: z.string(),
  customization: z.string(),
  risk_notes: z.string(),
});

export const GeneratedPlansSchema = z.object({
  plans: z.array(VideoPlanSchema).length(5),
});

export const AnalyzeResponseSchema = z.object({
  channel: ChannelSummarySchema,
  videos: z.array(PerformanceVideoSchema),
  analysis: AnalysisSummarySchema,
  plans: z.array(VideoPlanSchema),
  warnings: z.array(z.string()),
});

export type UserProfile = z.infer<typeof UserProfileSchema>;
export type AnalyzeRequest = z.infer<typeof AnalyzeRequestSchema>;
export type ChannelSummary = z.infer<typeof ChannelSummarySchema>;
export type TranscriptStatus = z.infer<typeof TranscriptStatusSchema>;
export type VideoSummary = z.infer<typeof VideoSummarySchema>;
export type PerformanceVideo = z.infer<typeof PerformanceVideoSchema>;
export type AnalysisSummary = z.infer<typeof AnalysisSummarySchema>;
export type VideoPlan = z.infer<typeof VideoPlanSchema>;
export type AnalyzeResponse = z.infer<typeof AnalyzeResponseSchema>;
```

- [ ] **Step 2: Run checks**

Run:

```bash
npm run typecheck
```

Expected: PASS.

- [ ] **Step 3: Commit**

Run:

```bash
git add src/lib/schemas.ts
git commit -m "feat: define planner schemas"
```

---

## Task 2: Parse Channel URLs And Collect YouTube Data

**Files:**
- Create: `src/lib/youtube.ts`
- Create: `src/lib/youtube.test.ts`

- [ ] **Step 1: Write failing URL parser tests**

```ts
// src/lib/youtube.test.ts
import { describe, expect, it, vi } from "vitest";
import { parseYouTubeChannelUrl, parseIsoDuration, getYouTubeChannelSnapshot } from "./youtube";

describe("parseYouTubeChannelUrl", () => {
  it("parses handle URLs", () => {
    expect(parseYouTubeChannelUrl("https://www.youtube.com/@somehandle")).toEqual({
      kind: "handle",
      value: "somehandle",
    });
  });

  it("parses channel id URLs", () => {
    expect(parseYouTubeChannelUrl("https://www.youtube.com/channel/UCabc123")).toEqual({
      kind: "channelId",
      value: "UCabc123",
    });
  });

  it("marks custom URLs as unsupported for MVP", () => {
    expect(parseYouTubeChannelUrl("https://www.youtube.com/c/customname")).toEqual({
      kind: "unsupported",
      value: "customname",
    });
  });
});

describe("parseIsoDuration", () => {
  it("converts YouTube ISO durations to seconds", () => {
    expect(parseIsoDuration("PT1H2M3S")).toBe(3723);
    expect(parseIsoDuration("PT12M")).toBe(720);
    expect(parseIsoDuration("PT45S")).toBe(45);
  });
});

describe("getYouTubeChannelSnapshot", () => {
  it("fetches channel, latest upload ids, and video stats", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url.includes("/channels?")) {
        return jsonResponse({
          items: [
            {
              id: "UC1",
              snippet: { title: "Bench", description: "About" },
              statistics: {
                subscriberCount: "1000",
                viewCount: "50000",
                videoCount: "80",
              },
              contentDetails: {
                relatedPlaylists: { uploads: "UU1" },
              },
            },
          ],
        });
      }

      if (url.includes("/playlistItems?")) {
        return jsonResponse({
          items: [
            { contentDetails: { videoId: "v1" } },
            { contentDetails: { videoId: "v2" } },
          ],
        });
      }

      if (url.includes("/videos?")) {
        return jsonResponse({
          items: [
            videoItem("v1", "Bad title", "PT1M10S", "1000"),
            videoItem("v2", "Good title", "PT2M", "2000"),
          ],
        });
      }

      throw new Error(`Unexpected URL ${url}`);
    });

    const result = await getYouTubeChannelSnapshot({
      apiKey: "key",
      channelUrl: "https://www.youtube.com/@bench",
      fetchImpl: fetchMock as typeof fetch,
    });

    expect(result.channel.title).toBe("Bench");
    expect(result.videos).toHaveLength(2);
    expect(result.videos[0].durationSeconds).toBe(70);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

function videoItem(id: string, title: string, duration: string, views: string) {
  return {
    id,
    snippet: {
      title,
      description: `${title} description`,
      publishedAt: "2026-06-01T00:00:00Z",
      thumbnails: { high: { url: `https://img.youtube.com/${id}.jpg` } },
      tags: ["ai", "youtube"],
      categoryId: "27",
    },
    contentDetails: { duration },
    statistics: {
      viewCount: views,
      likeCount: "10",
      commentCount: "2",
    },
  };
}
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
npm run test -- src/lib/youtube.test.ts
```

Expected: FAIL because `src/lib/youtube.ts` does not exist.

- [ ] **Step 3: Implement `src/lib/youtube.ts`**

```ts
// src/lib/youtube.ts
import type { ChannelSummary, VideoSummary } from "./schemas";

type ParsedChannelUrl =
  | { kind: "handle"; value: string }
  | { kind: "channelId"; value: string }
  | { kind: "unsupported"; value: string };

type FetchOptions = {
  apiKey: string;
  channelUrl: string;
  fetchImpl?: typeof fetch;
};

type YouTubeListResponse<T> = {
  items?: T[];
  nextPageToken?: string;
  error?: { message?: string };
};

type ChannelItem = {
  id: string;
  snippet: { title: string; description?: string };
  statistics: {
    subscriberCount?: string;
    hiddenSubscriberCount?: boolean;
    viewCount?: string;
    videoCount?: string;
  };
  contentDetails: { relatedPlaylists: { uploads: string } };
};

type PlaylistItem = {
  contentDetails: { videoId: string };
};

type VideoItem = {
  id: string;
  snippet: {
    title: string;
    description?: string;
    publishedAt: string;
    thumbnails?: Record<string, { url: string }>;
    tags?: string[];
    categoryId?: string;
  };
  contentDetails: { duration: string };
  statistics?: {
    viewCount?: string;
    likeCount?: string;
    commentCount?: string;
  };
};

export function parseYouTubeChannelUrl(rawUrl: string): ParsedChannelUrl {
  const url = new URL(rawUrl);
  const parts = url.pathname.split("/").filter(Boolean);

  if (parts[0]?.startsWith("@")) {
    return { kind: "handle", value: parts[0].slice(1) };
  }

  if (parts[0] === "channel" && parts[1]) {
    return { kind: "channelId", value: parts[1] };
  }

  if ((parts[0] === "c" || parts[0] === "user") && parts[1]) {
    return { kind: "unsupported", value: parts[1] };
  }

  throw new Error("지원하지 않는 YouTube 채널 URL입니다. @handle 또는 /channel/UC... URL을 입력해주세요.");
}

export function parseIsoDuration(duration: string): number {
  const match = duration.match(/^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$/);
  if (!match) return 0;
  const hours = Number(match[1] ?? 0);
  const minutes = Number(match[2] ?? 0);
  const seconds = Number(match[3] ?? 0);
  return hours * 3600 + minutes * 60 + seconds;
}

export async function getYouTubeChannelSnapshot({
  apiKey,
  channelUrl,
  fetchImpl = fetch,
}: FetchOptions): Promise<{ channel: ChannelSummary; videos: VideoSummary[] }> {
  const parsed = parseYouTubeChannelUrl(channelUrl);
  if (parsed.kind === "unsupported") {
    throw new Error("MVP에서는 @handle 또는 /channel/UC... URL을 우선 지원합니다. 채널 페이지의 @handle URL을 복사해주세요.");
  }

  const channelParams = new URLSearchParams({
    part: "snippet,statistics,contentDetails",
    key: apiKey,
  });

  if (parsed.kind === "handle") channelParams.set("forHandle", parsed.value);
  if (parsed.kind === "channelId") channelParams.set("id", parsed.value);

  const channelData = await getJson<YouTubeListResponse<ChannelItem>>(
    `https://www.googleapis.com/youtube/v3/channels?${channelParams}`,
    fetchImpl,
  );
  const channelItem = channelData.items?.[0];
  if (!channelItem) {
    throw new Error("채널을 찾을 수 없습니다. URL과 YouTube API 키를 확인해주세요.");
  }

  const channel: ChannelSummary = {
    id: channelItem.id,
    title: channelItem.snippet.title,
    description: channelItem.snippet.description ?? "",
    subscriberCount: channelItem.statistics.hiddenSubscriberCount
      ? null
      : toNumber(channelItem.statistics.subscriberCount),
    viewCount: toNumber(channelItem.statistics.viewCount) ?? 0,
    videoCount: toNumber(channelItem.statistics.videoCount) ?? 0,
    uploadsPlaylistId: channelItem.contentDetails.relatedPlaylists.uploads,
  };

  const uploadIds = await getLatestUploadIds(channel.uploadsPlaylistId, apiKey, fetchImpl);
  const videos = await getVideos(uploadIds, apiKey, fetchImpl);
  return { channel, videos };
}

async function getLatestUploadIds(playlistId: string, apiKey: string, fetchImpl: typeof fetch): Promise<string[]> {
  const params = new URLSearchParams({
    part: "contentDetails",
    playlistId,
    maxResults: "50",
    key: apiKey,
  });
  const data = await getJson<YouTubeListResponse<PlaylistItem>>(
    `https://www.googleapis.com/youtube/v3/playlistItems?${params}`,
    fetchImpl,
  );
  return (data.items ?? []).map((item) => item.contentDetails.videoId);
}

async function getVideos(ids: string[], apiKey: string, fetchImpl: typeof fetch): Promise<VideoSummary[]> {
  if (ids.length === 0) return [];
  const params = new URLSearchParams({
    part: "snippet,contentDetails,statistics",
    id: ids.join(","),
    maxResults: "50",
    key: apiKey,
  });
  const data = await getJson<YouTubeListResponse<VideoItem>>(
    `https://www.googleapis.com/youtube/v3/videos?${params}`,
    fetchImpl,
  );
  return (data.items ?? []).map(toVideoSummary);
}

async function getJson<T>(url: string, fetchImpl: typeof fetch): Promise<T> {
  const res = await fetchImpl(url);
  const body = (await res.json()) as YouTubeListResponse<unknown>;
  if (!res.ok) {
    throw new Error(body.error?.message ?? `YouTube API request failed with ${res.status}`);
  }
  return body as T;
}

function toVideoSummary(item: VideoItem): VideoSummary {
  return {
    id: item.id,
    title: item.snippet.title,
    description: item.snippet.description ?? "",
    thumbnailUrl:
      item.snippet.thumbnails?.maxres?.url ??
      item.snippet.thumbnails?.standard?.url ??
      item.snippet.thumbnails?.high?.url ??
      item.snippet.thumbnails?.medium?.url ??
      item.snippet.thumbnails?.default?.url ??
      "",
    publishedAt: item.snippet.publishedAt,
    durationSeconds: parseIsoDuration(item.contentDetails.duration),
    viewCount: toNumber(item.statistics?.viewCount) ?? 0,
    likeCount: toNumber(item.statistics?.likeCount),
    commentCount: toNumber(item.statistics?.commentCount),
    tags: item.snippet.tags ?? [],
    categoryId: item.snippet.categoryId,
    transcriptStatus: "not_requested",
  };
}

function toNumber(value: string | undefined): number | null {
  if (value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
```

- [ ] **Step 4: Run tests**

Run:

```bash
npm run test -- src/lib/youtube.test.ts
npm run typecheck
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/lib/youtube.ts src/lib/youtube.test.ts
git commit -m "feat: collect youtube channel data"
```

---

## Task 3: Add Best-Effort Transcript Enrichment

**Files:**
- Create: `src/lib/transcript.ts`
- Create: `src/lib/transcript.test.ts`

- [ ] **Step 1: Write failing transcript tests**

```ts
// src/lib/transcript.test.ts
import { describe, expect, it, vi } from "vitest";
import { enrichVideosWithTranscripts } from "./transcript";
import type { VideoSummary } from "./schemas";

vi.mock("youtube-transcript", () => ({
  fetchTranscript: vi.fn(async (videoId: string) => {
    if (videoId === "with-transcript") {
      return [
        { text: "첫 문장입니다", duration: 3, offset: 0 },
        { text: "두 번째 문장입니다", duration: 4, offset: 4000 },
        { text: "삼십초 이후 문장입니다", duration: 5, offset: 35000 },
      ];
    }
    throw new Error("Transcript disabled");
  }),
}));

describe("enrichVideosWithTranscripts", () => {
  it("adds first 30 seconds transcript preview when available", async () => {
    const result = await enrichVideosWithTranscripts([video("with-transcript")]);
    expect(result[0].transcriptStatus).toBe("available");
    expect(result[0].transcriptPreview).toContain("첫 문장입니다");
    expect(result[0].transcriptPreview).not.toContain("삼십초 이후");
  });

  it("marks missing transcript without throwing", async () => {
    const result = await enrichVideosWithTranscripts([video("missing")]);
    expect(result[0].transcriptStatus).toBe("missing");
    expect(result[0].transcriptPreview).toBeUndefined();
  });
});

function video(id: string): VideoSummary {
  return {
    id,
    title: "title",
    description: "",
    thumbnailUrl: "",
    publishedAt: "2026-06-01T00:00:00Z",
    durationSeconds: 60,
    viewCount: 100,
    likeCount: null,
    commentCount: null,
    tags: [],
    transcriptStatus: "not_requested",
  };
}
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
npm run test -- src/lib/transcript.test.ts
```

Expected: FAIL because `src/lib/transcript.ts` does not exist.

- [ ] **Step 3: Implement `src/lib/transcript.ts`**

```ts
// src/lib/transcript.ts
import { fetchTranscript } from "youtube-transcript";
import type { VideoSummary } from "./schemas";

type TranscriptLine = {
  text: string;
  duration: number;
  offset: number;
};

export async function enrichVideosWithTranscripts(videos: VideoSummary[]): Promise<VideoSummary[]> {
  return Promise.all(videos.map(enrichOneVideo));
}

async function enrichOneVideo(video: VideoSummary): Promise<VideoSummary> {
  try {
    const lines = (await fetchTranscript(video.id)) as TranscriptLine[];
    const firstThirtySeconds = lines
      .filter((line) => offsetToSeconds(line.offset) < 30)
      .map((line) => line.text.replace(/\s+/g, " ").trim())
      .filter(Boolean)
      .join(" ");

    if (!firstThirtySeconds) {
      return { ...video, transcriptStatus: "missing" };
    }

    return {
      ...video,
      transcriptStatus: "available",
      transcriptPreview: firstThirtySeconds.slice(0, 1200),
    };
  } catch {
    return { ...video, transcriptStatus: "missing" };
  }
}

function offsetToSeconds(offset: number): number {
  return offset > 1000 ? offset / 1000 : offset;
}
```

- [ ] **Step 4: Run tests**

Run:

```bash
npm run test -- src/lib/transcript.test.ts
npm run typecheck
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/lib/transcript.ts src/lib/transcript.test.ts
git commit -m "feat: add optional transcript enrichment"
```

---

## Task 4: Add Built-In Hook Framework And Deterministic Analysis

**Files:**
- Create: `src/lib/hook-framework.ts`
- Create: `src/lib/analysis.ts`
- Create: `src/lib/analysis.test.ts`

- [ ] **Step 1: Add built-in framework data**

```ts
// src/lib/hook-framework.ts
export const HOOK_FRAMEWORK = {
  clickHooks: [
    { id: "loss_aversion", label: "손실 회피", cue: "잃고 있는 것/위험/망함을 전면에 둠" },
    { id: "curiosity_gap", label: "호기심 갭", cue: "알 듯 말 듯한 정보 격차를 만듦" },
    { id: "reactance", label: "반항 효과", cue: "보지 마세요/하지 마세요/자격 제한" },
    { id: "contrarian", label: "통념 부정", cue: "대부분 믿는 전제를 뒤집음" },
    { id: "specific_number", label: "구체적 숫자", cue: "기간/금액/개수/배수로 구체화" },
    { id: "insider", label: "인사이더 폭로", cue: "실제로 해본 사람만 아는 진실" },
  ],
  retentionHooks: [
    { id: "zeigarnik", label: "자이가르닉", cue: "뒤에서 풀릴 오픈 루프를 남김" },
    { id: "pas", label: "PAS", cue: "문제 제시, 고통 증폭, 해결 약속" },
    { id: "aida", label: "AIDA", cue: "주의, 흥미, 욕망, 행동" },
    { id: "bab", label: "BAB", cue: "Before, After, Bridge 변화 구조" },
    { id: "hook_story_offer", label: "Hook Story Offer", cue: "후킹, 이야기, 제안" },
    { id: "big_idea", label: "Big Idea", cue: "한 문장으로 뒤집히는 큰 아이디어" },
  ],
  koreanMarket: [
    "솔직함",
    "억울함",
    "또래감",
    "근거 의심 대응",
    "가성비 프레임",
    "과한 자기자랑 회피",
    "직설 명령형 CTA 완화",
  ],
  timeline: ["0_3", "3_15", "15_30", "30_90", "ending"],
} as const;
```

- [ ] **Step 2: Write failing analysis tests**

```ts
// src/lib/analysis.test.ts
import { describe, expect, it } from "vitest";
import { analyzeVideos } from "./analysis";
import type { VideoSummary } from "./schemas";

describe("analyzeVideos", () => {
  it("calculates median, performance ratio, hook tags, and top videos", () => {
    const result = analyzeVideos([
      video("v1", "이거 모르면 100% 손해입니다", 1000, 60),
      video("v2", "평범한 브이로그", 2000, 600),
      video("v3", "부업 하지 마세요: 진짜 이유", 9000, 300),
    ]);

    expect(result.analysis.medianViews).toBe(2000);
    expect(result.analysis.averageViews).toBe(4000);
    expect(result.videos[0].performanceRatio).toBe(0.5);
    expect(result.videos[2].performanceLabel).toBe("breakout");
    expect(result.videos[2].hookTags).toContain("reactance");
    expect(result.analysis.topVideos[0].id).toBe("v3");
  });

  it("adds a warning when no transcript was available", () => {
    const result = analyzeVideos([video("v1", "제목", 1000, 60)]);
    expect(result.analysis.warnings).toContain("자막 분석 가능한 영상이 없어 메타데이터 기반 추정만 사용했습니다.");
  });
});

function video(id: string, title: string, views: number, durationSeconds: number): VideoSummary {
  return {
    id,
    title,
    description: "AI와 유튜브 기획 이야기",
    thumbnailUrl: `https://img.youtube.com/${id}.jpg`,
    publishedAt: "2026-06-01T00:00:00Z",
    durationSeconds,
    viewCount: views,
    likeCount: 10,
    commentCount: 2,
    tags: ["AI", "기획"],
    categoryId: "27",
    transcriptStatus: "missing",
  };
}
```

- [ ] **Step 3: Implement `src/lib/analysis.ts`**

```ts
// src/lib/analysis.ts
import type { AnalysisSummary, PerformanceVideo, VideoSummary } from "./schemas";

export function analyzeVideos(videos: VideoSummary[]): { videos: PerformanceVideo[]; analysis: AnalysisSummary } {
  const viewCounts = videos.map((video) => video.viewCount);
  const averageViews = round(mean(viewCounts));
  const medianViews = round(median(viewCounts));
  const baseline = medianViews > 0 ? medianViews : averageViews || 1;

  const enriched = videos.map((video) => {
    const performanceRatio = round(video.viewCount / baseline, 2);
    return {
      ...video,
      performanceRatio,
      performanceLabel: labelPerformance(performanceRatio),
      hookTags: inferHookTags(video),
      inferredFormat: inferFormat(video),
    } satisfies PerformanceVideo;
  });

  const topVideos = [...enriched].sort((a, b) => b.performanceRatio - a.performanceRatio).slice(0, 8);
  const transcriptCount = videos.filter((video) => video.transcriptStatus === "available").length;
  const warnings = transcriptCount === 0
    ? ["자막 분석 가능한 영상이 없어 메타데이터 기반 추정만 사용했습니다."]
    : [];

  const analysis: AnalysisSummary = {
    averageViews,
    medianViews,
    topVideos,
    titlePatterns: inferTitlePatterns(enriched),
    hookPatterns: inferHookPatterns(enriched),
    contentClusters: inferContentClusters(videos),
    uploadPattern: inferUploadPattern(videos),
    lengthPattern: inferLengthPattern(videos),
    warnings,
  };

  return { videos: enriched, analysis };
}

function mean(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

function round(value: number, digits = 0): number {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function labelPerformance(ratio: number): PerformanceVideo["performanceLabel"] {
  if (ratio >= 3) return "breakout";
  if (ratio >= 1.5) return "strong";
  if (ratio >= 0.7) return "normal";
  return "weak";
}

function inferHookTags(video: VideoSummary): string[] {
  const text = `${video.title} ${video.description} ${video.tags.join(" ")}`.toLowerCase();
  const tags = new Set<string>();

  if (/손해|망|실패|위험|하지 마|절대|후회/.test(text)) tags.add("loss_aversion");
  if (/왜|비밀|진짜|이유|공개|알려/.test(text)) tags.add("curiosity_gap");
  if (/하지 마|보지 마|금지|추천하지/.test(text)) tags.add("reactance");
  if (/착각|오해|거짓말|반대로|틀렸/.test(text)) tags.add("contrarian");
  if (/\d+/.test(text)) tags.add("specific_number");
  if (/실제|내부|전직|운영해본|겪어본|폭로/.test(text)) tags.add("insider");
  if (video.transcriptPreview) tags.add("transcript_backed");

  return [...tags];
}

function inferFormat(video: VideoSummary): string {
  const title = video.title;
  if (/\d+/.test(title) && /가지|단계|방법/.test(title)) return "list_or_howto";
  if (/비교|vs|전후/.test(title.toLowerCase())) return "comparison";
  if (/실패|망|하지 마/.test(title)) return "mistake_warning";
  if (/후기|리뷰|써봤/.test(title)) return "review";
  return "topic_explainer";
}

function inferTitlePatterns(videos: PerformanceVideo[]): string[] {
  const top = videos.filter((video) => video.performanceLabel === "breakout" || video.performanceLabel === "strong");
  const source = top.length > 0 ? top : videos;
  const patterns = new Set<string>();
  if (source.some((video) => /\d+/.test(video.title))) patterns.add("숫자를 넣어 구체성을 만든 제목이 반복됩니다.");
  if (source.some((video) => /왜|이유|비밀|진짜/.test(video.title))) patterns.add("이유/비밀/진짜 같은 호기심 갭 표현이 보입니다.");
  if (source.some((video) => /하지 마|망|손해|실패/.test(video.title))) patterns.add("손실 회피 또는 경고형 제목이 성과 영상에 포함됩니다.");
  return patterns.size > 0 ? [...patterns] : ["강한 반복 제목 패턴은 아직 뚜렷하지 않습니다."];
}

function inferHookPatterns(videos: PerformanceVideo[]): string[] {
  const counts = new Map<string, number>();
  videos.forEach((video) => video.hookTags.forEach((tag) => counts.set(tag, (counts.get(tag) ?? 0) + 1)));
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([tag, count]) => `${tag}: 최근 50개 중 ${count}개 영상에서 감지`);
}

function inferContentClusters(videos: VideoSummary[]): string[] {
  const counts = new Map<string, number>();
  videos.flatMap((video) => video.tags).forEach((tag) => {
    const normalized = tag.trim().toLowerCase();
    if (normalized) counts.set(normalized, (counts.get(normalized) ?? 0) + 1);
  });
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([tag, count]) => `${tag} (${count})`);
}

function inferUploadPattern(videos: VideoSummary[]): string {
  if (videos.length < 2) return "업로드 패턴을 판단하기에는 영상 수가 부족합니다.";
  const dayCounts = new Map<string, number>();
  videos.forEach((video) => {
    const day = new Intl.DateTimeFormat("ko-KR", { weekday: "long", timeZone: "Asia/Seoul" }).format(new Date(video.publishedAt));
    dayCounts.set(day, (dayCounts.get(day) ?? 0) + 1);
  });
  const [day, count] = [...dayCounts.entries()].sort((a, b) => b[1] - a[1])[0];
  return `${day} 업로드가 가장 많습니다 (${count}개).`;
}

function inferLengthPattern(videos: VideoSummary[]): string {
  const averageSeconds = mean(videos.map((video) => video.durationSeconds));
  if (averageSeconds < 180) return "평균 길이가 3분 미만인 숏폼/짧은 영상 중심입니다.";
  if (averageSeconds < 900) return "평균 길이가 3~15분인 일반 롱폼 중심입니다.";
  return "평균 길이가 15분 이상인 심층 롱폼 중심입니다.";
}
```

- [ ] **Step 4: Run tests**

Run:

```bash
npm run test -- src/lib/analysis.test.ts
npm run typecheck
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/lib/hook-framework.ts src/lib/analysis.ts src/lib/analysis.test.ts
git commit -m "feat: analyze youtube performance and hooks"
```

---

## Task 5: Generate Reverse-Planned Ideas With OpenAI Structured Outputs

**Files:**
- Create: `src/lib/planner.ts`
- Create: `src/lib/planner.test.ts`

- [ ] **Step 1: Write failing planner tests**

```ts
// src/lib/planner.test.ts
import { describe, expect, it } from "vitest";
import { buildPlannerPrompt, normalizePlans } from "./planner";
import type { AnalysisSummary, ChannelSummary, PerformanceVideo } from "./schemas";

describe("buildPlannerPrompt", () => {
  it("includes benchmark evidence and reverse planning requirements", () => {
    const prompt = buildPlannerPrompt({
      channel: channel(),
      videos: [video()],
      analysis: analysis(),
      profile: { topic: "영상 편집", audience: "초보 프리랜서", tone: "솔직한 정보형" },
    });

    expect(prompt).toContain("제목 → 썸네일 → 첫 5초 → 첫 30초");
    expect(prompt).toContain("Bench Channel");
    expect(prompt).toContain("초보 프리랜서");
  });
});

describe("normalizePlans", () => {
  it("keeps exactly five plans with three titles and thumbnails", () => {
    const plans = normalizePlans({
      plans: Array.from({ length: 6 }, (_, index) => ({
        concept: `concept ${index}`,
        titles: ["a", "b", "c", "d"],
        thumbnails: [
          { copy: "a", layout: "layout", visual_emotion: "curious" },
          { copy: "b", layout: "layout", visual_emotion: "curious" },
          { copy: "c", layout: "layout", visual_emotion: "curious" },
          { copy: "d", layout: "layout", visual_emotion: "curious" },
        ],
        hook_5s: "hook",
        hook_30s: "hook",
        timeline: { "0_3": "a", "3_15": "b", "15_30": "c", "30_90": "d", ending: "e" },
        body_outline: ["a", "b", "c"],
        mechanisms: ["loss_aversion"],
        benchmark_basis: "basis",
        customization: "custom",
        risk_notes: "risk",
      })),
    });

    expect(plans).toHaveLength(5);
    expect(plans[0].titles).toHaveLength(3);
    expect(plans[0].thumbnails).toHaveLength(3);
  });
});

function channel(): ChannelSummary {
  return {
    id: "UC1",
    title: "Bench Channel",
    description: "description",
    subscriberCount: 1000,
    viewCount: 100000,
    videoCount: 80,
    uploadsPlaylistId: "UU1",
  };
}

function video(): PerformanceVideo {
  return {
    id: "v1",
    title: "부업 하지 마세요",
    description: "",
    thumbnailUrl: "",
    publishedAt: "2026-06-01T00:00:00Z",
    durationSeconds: 600,
    viewCount: 9000,
    likeCount: 100,
    commentCount: 20,
    tags: ["부업"],
    categoryId: "27",
    transcriptStatus: "missing",
    performanceRatio: 3,
    performanceLabel: "breakout",
    hookTags: ["reactance", "loss_aversion"],
    inferredFormat: "mistake_warning",
  };
}

function analysis(): AnalysisSummary {
  return {
    averageViews: 4000,
    medianViews: 3000,
    topVideos: [video()],
    titlePatterns: ["경고형 제목"],
    hookPatterns: ["loss_aversion: 최근 50개 중 1개 영상에서 감지"],
    contentClusters: ["부업 (1)"],
    uploadPattern: "월요일 업로드가 가장 많습니다.",
    lengthPattern: "일반 롱폼 중심입니다.",
    warnings: [],
  };
}
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
npm run test -- src/lib/planner.test.ts
```

Expected: FAIL because `src/lib/planner.ts` does not exist.

- [ ] **Step 3: Implement `src/lib/planner.ts`**

```ts
// src/lib/planner.ts
import OpenAI from "openai";
import { zodTextFormat } from "openai/helpers/zod";
import { HOOK_FRAMEWORK } from "./hook-framework";
import { GeneratedPlansSchema, type AnalysisSummary, type ChannelSummary, type UserProfile, type VideoPlan, type PerformanceVideo } from "./schemas";

type PlannerInput = {
  channel: ChannelSummary;
  videos: PerformanceVideo[];
  analysis: AnalysisSummary;
  profile: Partial<UserProfile>;
};

export async function generatePlans(input: PlannerInput): Promise<VideoPlan[]> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error("OPENAI_API_KEY가 설정되어 있지 않습니다. .env.local에 값을 추가해주세요.");
  }

  const client = new OpenAI({ apiKey });
  const response = await client.responses.parse({
    model: process.env.OPENAI_MODEL ?? "gpt-5-mini",
    input: [
      {
        role: "system",
        content: "You are a Korean YouTube strategist. Return only schema-valid structured output.",
      },
      {
        role: "user",
        content: buildPlannerPrompt(input),
      },
    ],
    text: {
      format: zodTextFormat(GeneratedPlansSchema, "youtube_reverse_plans"),
    },
  });

  if (!response.output_parsed) {
    throw new Error("AI가 기획안 JSON 구조를 반환하지 못했습니다.");
  }

  return normalizePlans(response.output_parsed);
}

export function buildPlannerPrompt(input: PlannerInput): string {
  const profileText = [
    ["내 채널 주제", input.profile.topic],
    ["타깃", input.profile.audience],
    ["톤", input.profile.tone],
    ["피하고 싶은 스타일", input.profile.avoidStyle],
    ["선호 길이", input.profile.preferredLength],
    ["현재 고민", input.profile.currentProblem],
  ]
    .filter(([, value]) => typeof value === "string" && value.trim().length > 0)
    .map(([label, value]) => `- ${label}: ${value}`)
    .join("\n");

  const topVideoText = input.analysis.topVideos
    .slice(0, 8)
    .map((video, index) => [
      `${index + 1}. ${video.title}`,
      `   views=${video.viewCount}, ratio=${video.performanceRatio}, hooks=${video.hookTags.join(", ") || "none"}`,
      video.transcriptPreview ? `   first_30s=${video.transcriptPreview}` : "",
    ].filter(Boolean).join("\n"))
    .join("\n");

  return [
    "아래 벤치마킹 채널 데이터를 근거로 역순 영상 기획안 5개를 생성하세요.",
    "역순 기획이란 본문 아이디어가 아니라 제목 → 썸네일 → 첫 5초 → 첫 30초 순서로 클릭과 유지 구조를 먼저 설계하는 방식입니다.",
    "",
    "반드시 지킬 규칙:",
    "- 기획안은 정확히 5개",
    "- 각 기획안에는 제목 후보 3개",
    "- 각 기획안에는 썸네일 후보 3개: 문구, 구도, 감정/시각 포인트",
    "- 첫 5초 후킹과 첫 30초 전개를 분리",
    "- 0~3초, 3~15초, 15~30초, 30~90초, 엔딩 1분 구조 포함",
    "- 사용한 후킹 메커니즘은 내장 프레임워크 id 중심으로 작성",
    "- 벤치마킹 근거는 최근 50개 분석에서 나온 패턴과 연결",
    "- 내 채널 정보가 부족하면 일반화하되, 베끼기처럼 보이는 표현은 피함",
    "",
    `벤치마킹 채널: ${input.channel.title}`,
    `채널 설명: ${input.channel.description.slice(0, 600)}`,
    `최근 50개 평균 조회수: ${input.analysis.averageViews}`,
    `최근 50개 중앙값 조회수: ${input.analysis.medianViews}`,
    "",
    "성과 상위 영상:",
    topVideoText,
    "",
    "제목 패턴:",
    input.analysis.titlePatterns.map((pattern) => `- ${pattern}`).join("\n"),
    "",
    "후킹 패턴:",
    input.analysis.hookPatterns.map((pattern) => `- ${pattern}`).join("\n"),
    "",
    "콘텐츠 클러스터:",
    input.analysis.contentClusters.map((cluster) => `- ${cluster}`).join("\n"),
    "",
    "내장 후킹 프레임워크:",
    JSON.stringify(HOOK_FRAMEWORK),
    "",
    "사용자 채널 정보:",
    profileText || "- 입력 없음. 벤치마킹 채널 기반 일반 기획안으로 생성.",
  ].join("\n");
}

export function normalizePlans(data: { plans: VideoPlan[] }): VideoPlan[] {
  return data.plans.slice(0, 5).map((plan) => ({
    ...plan,
    titles: plan.titles.slice(0, 3),
    thumbnails: plan.thumbnails.slice(0, 3),
    body_outline: plan.body_outline.slice(0, 7),
  }));
}
```

- [ ] **Step 4: Run tests**

Run:

```bash
npm run test -- src/lib/planner.test.ts
npm run typecheck
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/lib/planner.ts src/lib/planner.test.ts
git commit -m "feat: generate structured reverse plans"
```

---

## Task 6: Add Markdown Export

**Files:**
- Create: `src/lib/markdown.ts`
- Create: `src/lib/markdown.test.ts`

- [ ] **Step 1: Write failing markdown test**

```ts
// src/lib/markdown.test.ts
import { describe, expect, it } from "vitest";
import { buildMarkdownReport } from "./markdown";
import type { AnalyzeResponse } from "./schemas";

describe("buildMarkdownReport", () => {
  it("renders channel, analysis, and five plan sections", () => {
    const markdown = buildMarkdownReport(response());
    expect(markdown).toContain("# Bench Channel 벤치마킹 리포트");
    expect(markdown).toContain("## 성공 패턴");
    expect(markdown).toContain("## 기획안 1");
    expect(markdown).toContain("### 제목 후보");
    expect(markdown).toContain("### 썸네일 후보");
  });
});

function response(): AnalyzeResponse {
  const plan = {
    concept: "concept",
    titles: ["title 1", "title 2", "title 3"],
    thumbnails: [
      { copy: "copy 1", layout: "layout 1", visual_emotion: "curious" },
      { copy: "copy 2", layout: "layout 2", visual_emotion: "urgent" },
      { copy: "copy 3", layout: "layout 3", visual_emotion: "honest" },
    ],
    hook_5s: "hook 5",
    hook_30s: "hook 30",
    timeline: { "0_3": "a", "3_15": "b", "15_30": "c", "30_90": "d", ending: "e" },
    body_outline: ["a", "b", "c"],
    mechanisms: ["loss_aversion"],
    benchmark_basis: "basis",
    customization: "custom",
    risk_notes: "risk",
  };

  return {
    channel: {
      id: "UC1",
      title: "Bench Channel",
      description: "description",
      subscriberCount: 1000,
      viewCount: 100000,
      videoCount: 80,
      uploadsPlaylistId: "UU1",
    },
    videos: [],
    analysis: {
      averageViews: 4000,
      medianViews: 3000,
      topVideos: [],
      titlePatterns: ["경고형 제목"],
      hookPatterns: ["loss_aversion"],
      contentClusters: ["ai"],
      uploadPattern: "월요일",
      lengthPattern: "롱폼",
      warnings: [],
    },
    plans: [plan, plan, plan, plan, plan],
    warnings: [],
  };
}
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
npm run test -- src/lib/markdown.test.ts
```

Expected: FAIL because `src/lib/markdown.ts` does not exist.

- [ ] **Step 3: Implement `src/lib/markdown.ts`**

```ts
// src/lib/markdown.ts
import type { AnalyzeResponse, VideoPlan } from "./schemas";

export function buildMarkdownReport(result: AnalyzeResponse): string {
  return [
    `# ${result.channel.title} 벤치마킹 리포트`,
    "",
    "## 채널 요약",
    "",
    `- 구독자: ${formatNumber(result.channel.subscriberCount)}`,
    `- 총 조회수: ${formatNumber(result.channel.viewCount)}`,
    `- 총 영상 수: ${formatNumber(result.channel.videoCount)}`,
    `- 최근 50개 평균 조회수: ${formatNumber(result.analysis.averageViews)}`,
    `- 최근 50개 중앙값 조회수: ${formatNumber(result.analysis.medianViews)}`,
    "",
    "## 성공 패턴",
    "",
    "### 제목 패턴",
    ...result.analysis.titlePatterns.map((pattern) => `- ${pattern}`),
    "",
    "### 후킹 패턴",
    ...result.analysis.hookPatterns.map((pattern) => `- ${pattern}`),
    "",
    "### 콘텐츠 클러스터",
    ...result.analysis.contentClusters.map((cluster) => `- ${cluster}`),
    "",
    "## 성과 상위 영상",
    "",
    ...result.analysis.topVideos.map((video, index) => (
      `${index + 1}. ${video.title} — ${formatNumber(video.viewCount)} views, ${video.performanceRatio}x`
    )),
    "",
    ...result.plans.flatMap((plan, index) => renderPlan(plan, index + 1)),
    "",
  ].join("\n");
}

function renderPlan(plan: VideoPlan, index: number): string[] {
  return [
    `## 기획안 ${index}: ${plan.concept}`,
    "",
    "### 제목 후보",
    ...plan.titles.map((title) => `- ${title}`),
    "",
    "### 썸네일 후보",
    ...plan.thumbnails.map((thumb) => `- ${thumb.copy} / ${thumb.layout} / ${thumb.visual_emotion}`),
    "",
    "### 초반 후킹",
    "",
    `- 첫 5초: ${plan.hook_5s}`,
    `- 첫 30초: ${plan.hook_30s}`,
    "",
    "### 0-3-15-30-90 구조",
    "",
    `- 0~3초: ${plan.timeline["0_3"]}`,
    `- 3~15초: ${plan.timeline["3_15"]}`,
    `- 15~30초: ${plan.timeline["15_30"]}`,
    `- 30~90초: ${plan.timeline["30_90"]}`,
    `- 엔딩 1분: ${plan.timeline.ending}`,
    "",
    "### 본문 구성",
    ...plan.body_outline.map((item) => `- ${item}`),
    "",
    `- 사용 메커니즘: ${plan.mechanisms.join(", ")}`,
    `- 벤치마킹 근거: ${plan.benchmark_basis}`,
    `- 맞춤 변형: ${plan.customization}`,
    `- 주의할 점: ${plan.risk_notes}`,
    "",
  ];
}

function formatNumber(value: number | null): string {
  if (value === null) return "비공개";
  return new Intl.NumberFormat("ko-KR").format(value);
}
```

- [ ] **Step 4: Run tests**

Run:

```bash
npm run test -- src/lib/markdown.test.ts
npm run typecheck
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/lib/markdown.ts src/lib/markdown.test.ts
git commit -m "feat: export analysis as markdown"
```

---

## Task 7: Add Analyze API Route

**Files:**
- Create: `src/app/api/analyze/route.ts`

- [ ] **Step 1: Implement `src/app/api/analyze/route.ts`**

```ts
// src/app/api/analyze/route.ts
import { NextResponse } from "next/server";
import { AnalyzeRequestSchema, AnalyzeResponseSchema } from "@/lib/schemas";
import { getYouTubeChannelSnapshot } from "@/lib/youtube";
import { enrichVideosWithTranscripts } from "@/lib/transcript";
import { analyzeVideos } from "@/lib/analysis";
import { generatePlans } from "@/lib/planner";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const json = await request.json();
    const input = AnalyzeRequestSchema.parse(json);

    const snapshot = await getYouTubeChannelSnapshot({
      apiKey: input.youtubeApiKey,
      channelUrl: input.channelUrl,
    });

    const transcriptVideos = await enrichVideosWithTranscripts(snapshot.videos);
    const { videos, analysis } = analyzeVideos(transcriptVideos);
    const plans = await generatePlans({
      channel: snapshot.channel,
      videos,
      analysis,
      profile: input.profile,
    });

    const response = AnalyzeResponseSchema.parse({
      channel: snapshot.channel,
      videos,
      analysis,
      plans,
      warnings: analysis.warnings,
    });

    return NextResponse.json(response);
  } catch (error) {
    return NextResponse.json(
      { error: toUserMessage(error) },
      { status: statusFor(error) },
    );
  }
}

function toUserMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "분석 중 알 수 없는 오류가 발생했습니다.";
}

function statusFor(error: unknown): number {
  if (error instanceof Error && /API key|OPENAI_API_KEY|YouTube API|쿼터|quota/i.test(error.message)) {
    return 400;
  }
  if (error instanceof Error && /채널|URL|지원하지/i.test(error.message)) {
    return 400;
  }
  return 500;
}
```

- [ ] **Step 2: Run checks**

Run:

```bash
npm run typecheck
npm run test
```

Expected: PASS.

- [ ] **Step 3: Commit**

Run:

```bash
git add src/app/api/analyze/route.ts
git commit -m "feat: add analyze api route"
```

---

## Task 8: Build The Single-Page MVP UI

**Files:**
- Modify: `src/app/page.tsx`
- Modify: `src/app/layout.tsx`
- Modify: `src/app/globals.css`

- [ ] **Step 1: Replace `src/app/layout.tsx`**

```tsx
// src/app/layout.tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "YouTube Benchmark Planner",
  description: "Analyze a benchmark YouTube channel and generate reverse-planned video ideas.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 2: Replace `src/app/page.tsx`**

```tsx
// src/app/page.tsx
"use client";

import { useMemo, useState } from "react";
import type { AnalyzeResponse, UserProfile } from "@/lib/schemas";
import { buildMarkdownReport } from "@/lib/markdown";

type FormState = {
  youtubeApiKey: string;
  channelUrl: string;
  profile: UserProfile;
};

const initialForm: FormState = {
  youtubeApiKey: "",
  channelUrl: "",
  profile: {
    topic: "",
    audience: "",
    tone: "",
    avoidStyle: "",
    preferredLength: "",
    currentProblem: "",
  },
};

export default function Home() {
  const [form, setForm] = useState<FormState>(initialForm);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const markdown = useMemo(() => (result ? buildMarkdownReport(result) : ""), [result]);

  async function analyze() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "분석에 실패했습니다.");
      setResult(data as AnalyzeResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "분석 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }

  function updateProfile(key: keyof UserProfile, value: string) {
    setForm((prev) => ({ ...prev, profile: { ...prev.profile, [key]: value } }));
  }

  function downloadMarkdown() {
    if (!markdown) return;
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "youtube-benchmark-report.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="min-h-screen bg-zinc-50 text-zinc-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-2 border-b border-zinc-200 pb-5">
          <p className="text-sm font-medium text-zinc-500">YouTube Benchmark Planner</p>
          <h1 className="text-3xl font-semibold tracking-tight">채널 분석에서 역순 기획안까지</h1>
          <p className="max-w-3xl text-sm leading-6 text-zinc-600">
            벤치마킹 채널 URL을 넣으면 최근 50개 영상의 성과, 제목, 썸네일, 초반 후킹 패턴을 분석하고
            제목 → 썸네일 → 첫 5초 → 첫 30초 구조의 기획안 5개를 만듭니다.
          </p>
        </header>

        <section className="grid gap-4 lg:grid-cols-[360px_1fr]">
          <aside className="flex flex-col gap-4 rounded-lg border border-zinc-200 bg-white p-4">
            <label className="flex flex-col gap-2 text-sm font-medium">
              YouTube API Key
              <input
                className="rounded-md border border-zinc-300 px-3 py-2 font-mono text-sm outline-none focus:border-zinc-900"
                type="password"
                value={form.youtubeApiKey}
                onChange={(event) => setForm({ ...form, youtubeApiKey: event.target.value })}
                placeholder="AIza..."
              />
            </label>

            <label className="flex flex-col gap-2 text-sm font-medium">
              벤치마킹 채널 URL
              <input
                className="rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-zinc-900"
                value={form.channelUrl}
                onChange={(event) => setForm({ ...form, channelUrl: event.target.value })}
                placeholder="https://www.youtube.com/@channel"
              />
            </label>

            <div className="grid gap-3 border-t border-zinc-200 pt-4">
              <p className="text-sm font-semibold">내 채널 정보 (선택)</p>
              <Input label="내 채널 주제" value={form.profile.topic} onChange={(value) => updateProfile("topic", value)} />
              <Input label="타깃 시청자" value={form.profile.audience} onChange={(value) => updateProfile("audience", value)} />
              <Input label="원하는 톤" value={form.profile.tone} onChange={(value) => updateProfile("tone", value)} />
              <Input label="피하고 싶은 스타일" value={form.profile.avoidStyle} onChange={(value) => updateProfile("avoidStyle", value)} />
              <Input label="선호 영상 길이" value={form.profile.preferredLength} onChange={(value) => updateProfile("preferredLength", value)} />
              <Input label="현재 고민" value={form.profile.currentProblem} onChange={(value) => updateProfile("currentProblem", value)} />
            </div>

            <button
              className="rounded-md bg-zinc-950 px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-zinc-400"
              disabled={loading || !form.youtubeApiKey || !form.channelUrl}
              onClick={analyze}
            >
              {loading ? "분석 중..." : "최근 50개 분석하기"}
            </button>

            {error && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
          </aside>

          <section className="min-h-[640px] rounded-lg border border-zinc-200 bg-white p-4">
            {!result && !loading && (
              <div className="flex h-full min-h-[520px] items-center justify-center text-center text-sm text-zinc-500">
                채널을 분석하면 이곳에 성과표, 성공 패턴, 역순 기획안이 표시됩니다.
              </div>
            )}

            {loading && (
              <div className="flex h-full min-h-[520px] items-center justify-center text-center text-sm text-zinc-500">
                YouTube 데이터 수집, 자막 보강, 후킹 분석, 기획안 생성을 순서대로 진행 중입니다.
              </div>
            )}

            {result && (
              <div className="flex flex-col gap-6">
                <div className="flex flex-col gap-3 border-b border-zinc-200 pb-4 md:flex-row md:items-start md:justify-between">
                  <div>
                    <h2 className="text-2xl font-semibold">{result.channel.title}</h2>
                    <p className="mt-1 line-clamp-2 text-sm text-zinc-600">{result.channel.description}</p>
                  </div>
                  <button className="rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium" onClick={downloadMarkdown}>
                    Markdown 내보내기
                  </button>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  <Metric label="평균 조회수" value={formatNumber(result.analysis.averageViews)} />
                  <Metric label="중앙값 조회수" value={formatNumber(result.analysis.medianViews)} />
                  <Metric label="분석 영상 수" value={`${result.videos.length}개`} />
                </div>

                {result.warnings.length > 0 && (
                  <div className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                    {result.warnings.map((warning) => <p key={warning}>{warning}</p>)}
                  </div>
                )}

                <section>
                  <h3 className="mb-3 text-lg font-semibold">성과 상위 영상</h3>
                  <div className="overflow-hidden rounded-lg border border-zinc-200">
                    <table className="w-full min-w-[720px] text-left text-sm">
                      <thead className="bg-zinc-100 text-zinc-600">
                        <tr>
                          <th className="px-3 py-2">제목</th>
                          <th className="px-3 py-2">조회수</th>
                          <th className="px-3 py-2">성과</th>
                          <th className="px-3 py-2">후킹 태그</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.analysis.topVideos.map((video) => (
                          <tr key={video.id} className="border-t border-zinc-200">
                            <td className="px-3 py-2 font-medium">{video.title}</td>
                            <td className="px-3 py-2">{formatNumber(video.viewCount)}</td>
                            <td className="px-3 py-2">{video.performanceRatio}x</td>
                            <td className="px-3 py-2">{video.hookTags.join(", ") || "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>

                <section className="grid gap-3 lg:grid-cols-3">
                  <Pattern title="제목 패턴" items={result.analysis.titlePatterns} />
                  <Pattern title="후킹 패턴" items={result.analysis.hookPatterns} />
                  <Pattern title="콘텐츠 클러스터" items={result.analysis.contentClusters} />
                </section>

                <section className="flex flex-col gap-4">
                  <h3 className="text-lg font-semibold">역순 기획안 5개</h3>
                  {result.plans.map((plan, index) => (
                    <article key={`${plan.concept}-${index}`} className="rounded-lg border border-zinc-200 p-4">
                      <p className="text-sm font-medium text-zinc-500">기획안 {index + 1}</p>
                      <h4 className="mt-1 text-xl font-semibold">{plan.concept}</h4>
                      <div className="mt-4 grid gap-4 lg:grid-cols-2">
                        <PlanBlock title="제목 후보" items={plan.titles} />
                        <PlanBlock title="썸네일 후보" items={plan.thumbnails.map((thumb) => `${thumb.copy} / ${thumb.layout} / ${thumb.visual_emotion}`)} />
                      </div>
                      <div className="mt-4 grid gap-3 md:grid-cols-2">
                        <Metric label="첫 5초" value={plan.hook_5s} />
                        <Metric label="첫 30초" value={plan.hook_30s} />
                      </div>
                      <PlanBlock
                        title="0-3-15-30-90 구조"
                        items={[
                          `0~3초: ${plan.timeline["0_3"]}`,
                          `3~15초: ${plan.timeline["3_15"]}`,
                          `15~30초: ${plan.timeline["15_30"]}`,
                          `30~90초: ${plan.timeline["30_90"]}`,
                          `엔딩: ${plan.timeline.ending}`,
                        ]}
                      />
                      <p className="mt-3 text-sm text-zinc-600">근거: {plan.benchmark_basis}</p>
                      <p className="mt-1 text-sm text-zinc-600">맞춤 변형: {plan.customization}</p>
                    </article>
                  ))}
                </section>
              </div>
            )}
          </section>
        </section>
      </div>
    </main>
  );
}

function Input({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-zinc-600">
      {label}
      <input
        className="rounded-md border border-zinc-300 px-3 py-2 text-sm text-zinc-950 outline-none focus:border-zinc-900"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3">
      <p className="text-xs font-medium text-zinc-500">{label}</p>
      <p className="mt-1 whitespace-pre-wrap text-sm font-semibold text-zinc-950">{value}</p>
    </div>
  );
}

function Pattern({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-lg border border-zinc-200 p-3">
      <h3 className="text-sm font-semibold">{title}</h3>
      <ul className="mt-2 space-y-1 text-sm text-zinc-600">
        {items.map((item) => <li key={item}>- {item}</li>)}
      </ul>
    </div>
  );
}

function PlanBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="mt-4">
      <h5 className="text-sm font-semibold">{title}</h5>
      <ul className="mt-2 space-y-1 text-sm text-zinc-700">
        {items.map((item) => <li key={item}>- {item}</li>)}
      </ul>
    </div>
  );
}

function formatNumber(value: number | null): string {
  if (value === null) return "비공개";
  return new Intl.NumberFormat("ko-KR").format(value);
}
```

- [ ] **Step 3: Replace `src/app/globals.css`**

```css
/* src/app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  color-scheme: light;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: #fafafa;
}
```

- [ ] **Step 4: Run checks**

Run:

```bash
npm run typecheck
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/app/page.tsx src/app/layout.tsx src/app/globals.css
git commit -m "feat: build planner dashboard ui"
```

---

## Task 9: End-To-End Local Verification

**Files:**
- Modify only if verification exposes issues in files from previous tasks.

- [ ] **Step 1: Create local env**

Run:

```bash
cd /Users/gimseung-an/youtube-benchmark-planner
cp .env.example .env.local
```

Edit `.env.local` and set `OPENAI_API_KEY` to a valid key. Keep `OPENAI_MODEL=gpt-5-mini` unless there is a specific reason to use a larger model.

- [ ] **Step 2: Run automated checks**

Run:

```bash
npm run test
npm run typecheck
npm run build
```

Expected: all pass.

- [ ] **Step 3: Start dev server**

Run:

```bash
npm run dev -- --port 3000
```

Expected: server prints a local URL such as `http://localhost:3000`.

- [ ] **Step 4: Browser QA**

Open `http://localhost:3000` in the in-app browser.

Use a valid YouTube Data API key and a handle URL such as:

```text
https://www.youtube.com/@veritasium
```

Expected:

- API key and channel URL fields accept input.
- Optional profile fields can be left blank.
- Analyze button shows loading state.
- Completed result shows channel summary, top videos, patterns, and five plan cards.
- Markdown download produces a `.md` file with channel summary and five plans.
- If transcripts are unavailable, the app shows a warning but still completes.

- [ ] **Step 5: Error QA**

Submit with an invalid YouTube API key.

Expected:

- UI shows an error message.
- The page does not crash.
- Previous successful result, if any, is cleared before a new run.

- [ ] **Step 6: Commit fixes if needed**

If verification required code changes:

```bash
git add .
git commit -m "fix: harden planner mvp verification issues"
```

If no code changes were needed, do not create an empty commit.

---

## Task 10: Update Project README

**Files:**
- Modify: `/Users/gimseung-an/youtube-benchmark-planner/README.md`

- [ ] **Step 1: Replace README**

```md
# YouTube Benchmark Planner

Local MVP web app for benchmarking one YouTube channel and generating reverse-planned video ideas.

## What It Does

- Accepts a YouTube channel URL.
- Fetches the latest 50 uploads through YouTube Data API.
- Calculates performance patterns from public metadata.
- Adds first-30-second transcript analysis when publicly available.
- Generates five reverse-planned ideas:
  - title candidates
  - thumbnail candidates
  - first 5 seconds
  - first 30 seconds
  - 0-3-15-30-90 structure

## Setup

```bash
npm install
cp .env.example .env.local
```

Set `OPENAI_API_KEY` in `.env.local`.

The YouTube Data API key is entered in the local UI for each analysis request.

## Run

```bash
npm run dev
```

Open `http://localhost:3000`.

## Checks

```bash
npm run test
npm run typecheck
npm run build
```

## MVP Limits

- One benchmark channel at a time.
- Official YouTube metadata is the stable baseline.
- Transcript analysis is best effort and may be unavailable.
- Custom hook-file upload is planned for v2.
```

- [ ] **Step 2: Run checks**

Run:

```bash
npm run test
npm run typecheck
```

Expected: PASS.

- [ ] **Step 3: Commit**

Run:

```bash
git add README.md
git commit -m "docs: document youtube benchmark planner mvp"
```

---

## Final Verification Before Completion

Run from `/Users/gimseung-an/youtube-benchmark-planner`:

```bash
npm run test
npm run typecheck
npm run build
git status --short
```

Expected:

- Tests pass.
- TypeScript passes.
- Production build passes.
- `git status --short` is clean or contains only intentionally uncommitted local files such as `.env.local`.

Then report:

- Local app path.
- Dev server URL if still running.
- The final commit hash.
- Any remaining limits, especially transcript availability and YouTube API quota.
