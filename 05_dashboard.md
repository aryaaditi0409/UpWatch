# Architecture SOP — Dashboard

> Layer 1: Next.js 15 App Router dashboard

---

## Overview

The dashboard is a Next.js 15 application using App Router, providing real-time outage monitoring via SSE and a global heatmap.

## App Router Structure

```
apps/dashboard/
├── app/
│   ├── layout.tsx           # Root layout, dark theme, navbar
│   ├── page.tsx             # Main dashboard page
│   ├── api/
│   │   └── live/
│   │       └── route.ts     # SSE endpoint
│   └── components/
│       ├── Heatmap.tsx      # react-leaflet map
│       ├── OutageTable.tsx  # Confirmed outages table
│       ├── LiveFeed.tsx     # SSE consumer
│       └── ConnectionStatus.tsx  # Connection indicator
```

## SSE Endpoint (`/api/live`)

```typescript
import { NextRequest } from "next/server";
import Redis from "ioredis";

export const runtime = "edge";

export async function GET(request: NextRequest) {
  const redis = new Redis(process.env.REDIS_URL!);
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      await redis.subscribe("outages:live");

      redis.on("message", (channel, message) => {
        controller.enqueue(encoder.encode(`data: ${message}\n\n`));
      });

      // Keep connection alive
      const keepAlive = setInterval(() => {
        controller.enqueue(encoder.encode(`: keepalive\n\n`));
      }, 30_000);

      request.signal.addEventListener("abort", () => {
        clearInterval(keepAlive);
        redis.unsubscribe();
        redis.disconnect();
        controller.close();
      });
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
    },
  });
}
```

## Heatmap (`Heatmap.tsx`)

### react-leaflet Implementation
- Uses `CircleMarker` for each region
- Color coding:
  - Green (`#22c55e`): All nodes UP
  - Yellow (`#eab308`): Some nodes DEGRADED
  - Red (`#ef4444`): Consensus DOWN confirmed
- Tooltip on hover: region name, active nodes, last outage
- Auto-center and zoom to fit all markers

### Marker Updates
- Receives SSE events from LiveFeed component
- Updates marker color/size based on consensus score
- Animates pulse on new outage

## OutageTable (`OutageTable.tsx`)

### Server Component
- Reads from Neon `outages` table via server-side query
- Columns: Target, Region, Start, Duration, Consensus Score, TX Hash, SLA Status
- Pagination: 20 rows per page

### Fallback Mode
- If RPC is slow (timeout > 5s), reads from Neon
- Shows amber badge: "Showing cached data"
- Polls for fresh data every 30s

## LiveFeed (`LiveFeed.tsx`)

### Client Component
- Connects to `/api/live` via `EventSource`
- Exponential backoff on disconnect:
  - 1s, 2s, 4s, 8s, 16s, max 60s
- Updates ConnectionStatus component
- Passes events to Heatmap for real-time updates

### Reconnect Logic

```typescript
const [retryDelay, setRetryDelay] = useState(1000);

useEffect(() => {
  const es = new EventSource("/api/live");

  es.onerror = () => {
    es.close();
    setTimeout(() => {
      setRetryDelay(prev => Math.min(prev * 2, 60000));
      // Reconnect...
    }, retryDelay);
  };

  es.onopen = () => setRetryDelay(1000); // Reset on success

  return () => es.close();
}, [retryDelay]);
```

## ConnectionStatus (`ConnectionStatus.tsx`)

- Green dot: SSE connected
- Red dot: SSE disconnected / reconnecting
- Positioned in navbar
- Shows retry countdown on disconnect

## Styling

### Dark Theme
- Tailwind CSS `dark:` classes
- `darkMode: "class"` in tailwind.config.js
- Default theme: dark

### Responsive Layout
- Mobile: stacked layout, single column
- Tablet: 2-column grid
- Desktop: full grid with sidebar

## Environment Variables

```
NEXT_PUBLIC_API_URL=http://localhost:3001
NEXT_PUBLIC_RPC_URL=https://base-sepolia.g.alchemy.com/v2/YOUR_KEY
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://... (Neon)
```
