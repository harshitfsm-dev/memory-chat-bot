import { DEFAULT_SETTINGS } from "@/lib/defaults";
import type { Conversation, UserProfile } from "@/lib/types";

export { DEFAULT_SETTINGS };

export const MOCK_USER: UserProfile = {
  name: "Harshit Singh",
  email: "harshit@novalabs.io",
  initials: "HS",
  plan: "Nova Plus",
};


const now = Date.now();
const HOUR = 3600_000;
const DAY = 24 * HOUR;
const iso = (offset: number) => new Date(now - offset).toISOString();

let seq = 0;
const mid = () => `seed-msg-${++seq}`;

function conv(
  id: string,
  title: string,
  ago: number,
  model: Conversation["model"],
  messages: Conversation["messages"],
  archived = false,
): Conversation {
  return {
    id,
    title,
    createdAt: iso(ago + HOUR),
    updatedAt: iso(ago),
    model,
    archived,
    messages,
  };
}

export const MOCK_CONVERSATIONS: Conversation[] = [
  conv("c-q3-marketing", "Q3 Marketing Strategy", 1.5 * HOUR, "nova-pro", [
    {
      id: mid(),
      role: "user",
      content:
        "We're planning Q3 for our analytics product. Help me build a marketing strategy focused on mid-market teams.",
      createdAt: iso(1.6 * HOUR),
    },
    {
      id: mid(),
      role: "assistant",
      content: `Here's a Q3 strategy built around one bet: **make mid-market teams feel the product in week one**.

### 1. Positioning
Move from "analytics platform" to "the answer layer for revenue teams". Mid-market buyers don't want another dashboard, they want fewer meetings about numbers.

### 2. Three plays
1. **Activation-led content** — 6 teardown posts showing a real funnel fixed in under an hour.
2. **Partner co-marketing** — 2 joint webinars with CRM integrations you already ship.
3. **Champion program** — 15 power users, private Slack, early access in exchange for quotes.

### 3. Quarterly targets

| Metric | Q2 actual | Q3 target |
| --- | --- | --- |
| Trials started | 480 | 720 |
| Trial → paid | 11% | 16% |
| Pipeline from content | $340k | $600k |

### 4. What to cut
Paid search on generic head terms. It converted at 1.2% and ate 38% of spend.

Want me to turn play #1 into a week-by-week content calendar?`,
      createdAt: iso(1.5 * HOUR),
      feedback: "up",
    },
  ]),
  conv("c-rsc", "Explain React Server Components", 4 * HOUR, "nova-pro", [
    {
      id: mid(),
      role: "user",
      content: "Explain React Server Components like I already know hooks but not SSR internals.",
      createdAt: iso(4.1 * HOUR),
    },
    {
      id: mid(),
      role: "assistant",
      content: `A Server Component is a component that **never ships to the browser**. It runs on the server, returns a serialized description of UI, and React stitches that into the client tree.

### What changes for you
- No \`useState\`, \`useEffect\`, or event handlers inside them.
- You can \`await\` directly in the component body.
- Props crossing the boundary must be serializable.

\`\`\`tsx
// server component
async function Invoices({ orgId }: { orgId: string }) {
  const rows = await db.invoice.findMany({ where: { orgId } });
  return <InvoiceTable rows={rows} />; // client component
}
\`\`\`

Use \`"use client"\` only at the leaves that genuinely need interactivity — a filter input, a chart tooltip — and keep data fetching above it.

Rule of thumb: *server for data and layout, client for interaction*.`,
      createdAt: iso(4 * HOUR),
    },
    {
      id: mid(),
      role: "user",
      content: "So is `useSuspenseQuery` pointless now?",
      createdAt: iso(3.9 * HOUR),
    },
    {
      id: mid(),
      role: "assistant",
      content: `Not at all — it's the right tool the moment data has to *refetch on the client*: filters, polling, optimistic writes, infinite lists.

- **Server component fetch** → first paint, static-ish data.
- **\`useSuspenseQuery\`** → anything that changes while the user is on the page.

Most production apps use both, with the loader priming the cache.`,
      createdAt: iso(3.85 * HOUR),
    },
  ]),
  conv("c-sales-report", "Analyze Sales Report", 6 * HOUR, "nova-pro", [
    {
      id: mid(),
      role: "user",
      content: "Can you pull the highlights out of this month's sales export?",
      createdAt: iso(6.1 * HOUR),
      attachments: [
        {
          id: "att-1",
          name: "sales-june-2026.xlsx",
          mime: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          size: 284_512,
          status: "done",
          progress: 100,
        },
        {
          id: "att-2",
          name: "regional-breakdown.csv",
          mime: "text/csv",
          size: 41_233,
          status: "done",
          progress: 100,
        },
      ],
    },
    {
      id: mid(),
      role: "assistant",
      content: `Three things stand out in the export.

1. **APAC carried the quarter** — 34% of net new revenue from 19% of accounts.
2. **Mid-market churn doubled** — 2.1% → 4.4%, concentrated in accounts onboarded without a success call.
3. **Discounting crept up** — average discount 14.8% vs 9.2% target.

| Region | Net new | QoQ | Churn |
| --- | --- | --- | --- |
| APAC | $1.24M | +28% | 1.8% |
| NA | $2.06M | +6% | 4.4% |
| EMEA | $0.87M | −3% | 3.1% |

The fastest lever is the onboarding call — cohorts that had one churned at 1.6%.`,
      createdAt: iso(6 * HOUR),
    },
  ]),
  conv("c-launch-ideas", "Product Launch Ideas", 9 * HOUR, "nova-fast", [
    {
      id: mid(),
      role: "user",
      content: "Give me 5 launch ideas for a new AI summarization feature. Nothing generic.",
      createdAt: iso(9.1 * HOUR),
    },
    {
      id: mid(),
      role: "assistant",
      content: `1. **"Inbox zero, live"** — a 30-minute stream where your team clears a real 400-message backlog with the feature.
2. **The long-document gauntlet** — publish summaries of five notoriously dense public filings, side by side with human notes.
3. **Summary of the summaries** — a weekly email that summarizes your own changelog using the feature.
4. **Bring your worst PDF** — a contest; the ugliest scanned doc wins a year free.
5. **Silent demo** — a 45-second video, no voiceover, no music, just the interaction. Ships everywhere.`,
      createdAt: iso(9 * HOUR),
      feedback: "up",
    },
  ]),
  conv("c-python-debug", "Python Debugging", 26 * HOUR, "nova-pro", [
    {
      id: mid(),
      role: "user",
      content: "My async worker hangs after ~200 jobs. No error, no exit. Where do I start?",
      createdAt: iso(26.2 * HOUR),
    },
    {
      id: mid(),
      role: "assistant",
      content: `That pattern is almost always **exhausted concurrency, not a crash** — a resource that is acquired and never released.

Check in this order:

1. Are you awaiting inside a lock you also acquire downstream?
2. Is your connection pool smaller than your task fan-out?
3. Any \`asyncio.create_task\` results you never await (swallowed exceptions)?

Dump the loop state when it stalls:

\`\`\`python
import asyncio, faulthandler, signal

faulthandler.register(signal.SIGUSR1)

def dump_tasks():
    for t in asyncio.all_tasks():
        print(t.get_name(), t.get_coro(), t.done())
\`\`\`

If every task shows \`acquire\` in its stack, it's the pool.`,
      createdAt: iso(26 * HOUR),
    },
  ]),
  conv("c-travel", "Travel Planning", 30 * HOUR, "nova-fast", [
    {
      id: mid(),
      role: "user",
      content: "9 days in Japan in late October, first visit, moderate budget. Draft an itinerary.",
      createdAt: iso(30.2 * HOUR),
    },
    {
      id: mid(),
      role: "assistant",
      content: `### Shape of the trip
Tokyo (3) → Hakone (1) → Kyoto (3) → Osaka (2)

**Days 1–3 · Tokyo**
- Yanaka and Nezu on foot, then Shimokitazawa in the evening.
- One early morning at Tsukiji Outer Market, before 07:30.

**Day 4 · Hakone**
Ryokan night with a private onsen. Book 6+ weeks out for late October.

**Days 5–7 · Kyoto**
- Fushimi Inari at 06:30 — the difference is dramatic.
- Arashiyama in the late afternoon when day-trippers leave.

**Days 8–9 · Osaka**
Kuromon Market, Namba at night, day trip to Nara if the weather holds.

Get a 7-day JR Pass only if you keep the Hakone leg — otherwise single tickets are cheaper.`,
      createdAt: iso(30 * HOUR),
    },
  ]),
  conv("c-meeting-notes", "Meeting Notes Summary", 2.2 * DAY, "nova-fast", [
    {
      id: mid(),
      role: "user",
      content: "Summarize these notes into decisions and owners.",
      createdAt: iso(2.25 * DAY),
      attachments: [
        {
          id: "att-3",
          name: "platform-sync-notes.docx",
          mime: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          size: 68_402,
          status: "done",
          progress: 100,
        },
      ],
    },
    {
      id: mid(),
      role: "assistant",
      content: `**Decisions**
- Ship the new billing page behind a flag on the 14th.
- Freeze schema changes until the migration lands.

**Owners**

| Item | Owner | Due |
| --- | --- | --- |
| Flag rollout plan | Priya | Jul 12 |
| Migration dry run | Marco | Jul 10 |
| Support macros | Dana | Jul 15 |

**Open question:** who signs off on the pricing copy?`,
      createdAt: iso(2.2 * DAY),
    },
  ]),
  conv("c-onboarding-copy", "Rewrite Onboarding Copy", 3.4 * DAY, "nova-fast", [
    {
      id: mid(),
      role: "user",
      content: "Our onboarding empty state says 'No data yet'. Make it useful.",
      createdAt: iso(3.45 * DAY),
    },
    {
      id: mid(),
      role: "assistant",
      content: `Try: **"Connect a source to see your first report"** with a one-line subhead — *Takes about two minutes. We'll backfill 30 days automatically.* — and a single primary button.

Empty states should answer: what happened, what to do, how long it takes.`,
      createdAt: iso(3.4 * DAY),
    },
  ]),
  conv("c-sql-optimization", "Optimize a Slow Query", 4.6 * DAY, "nova-pro", [
    {
      id: mid(),
      role: "user",
      content: "This query takes 8 seconds on 12M rows. Ideas?",
      createdAt: iso(4.65 * DAY),
    },
    {
      id: mid(),
      role: "assistant",
      content: `Start with the plan, not the query:

\`\`\`sql
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;
\`\`\`

Most 8-second scans on that size come from one of three things:

- A \`LIKE '%term%'\` that can't use a btree index → move to a trigram or FTS index.
- Sorting before limiting on an unindexed column.
- A correlated subquery that should be a lateral join.

If \`created_at\` filters most rows, a composite \`(tenant_id, created_at DESC)\` index usually drops this under 200 ms.`,
      createdAt: iso(4.6 * DAY),
      feedback: "up",
    },
  ]),
  conv("c-design-review", "Design Review Feedback", 6.1 * DAY, "nova-fast", [
    {
      id: mid(),
      role: "user",
      content: "Review this dashboard screenshot and tell me what's wrong with the hierarchy.",
      createdAt: iso(6.15 * DAY),
      attachments: [
        {
          id: "att-4",
          name: "dashboard-v3.png",
          mime: "image/png",
          size: 1_284_921,
          status: "done",
          progress: 100,
        },
      ],
    },
    {
      id: mid(),
      role: "assistant",
      content: `The screen has four things competing to be first: the KPI row, the chart title, the filter bar, and the alert banner.

- Pick one hero number and make it 2× the next largest type size.
- Demote filters to a single line with a "More filters" affordance.
- The alert banner should be inline, not full-width — it's not blocking work.
- Drop one border per card; use spacing instead.`,
      createdAt: iso(6.1 * DAY),
    },
  ]),
  conv("c-competitor-teardown", "Competitor Teardown", 12 * DAY, "nova-pro", [
    {
      id: mid(),
      role: "user",
      content: "Compare our pricing page against the two closest competitors.",
      createdAt: iso(12.1 * DAY),
    },
    {
      id: mid(),
      role: "assistant",
      content: `Your page explains packaging; theirs explain outcomes.

| | You | Competitor A | Competitor B |
| --- | --- | --- | --- |
| Tiers | 4 | 3 | 3 |
| Free trial | 14 days | 30 days | Free tier |
| Annual discount | 10% | 20% | 17% |

Two changes with the most upside: collapse to three tiers, and put the "most teams choose" marker on the middle plan.`,
      createdAt: iso(12 * DAY),
    },
  ]),
  conv("c-okrs", "Draft Team OKRs", 18 * DAY, "nova-fast", [
    {
      id: mid(),
      role: "user",
      content: "Help me write OKRs for a 6-person platform team.",
      createdAt: iso(18.1 * DAY),
    },
    {
      id: mid(),
      role: "assistant",
      content: `**Objective:** Make shipping boring.

- KR1: p95 deploy time 22 min → 8 min.
- KR2: change failure rate below 8%.
- KR3: 90% of services on the shared observability baseline.

Keep it to one objective — six people can't move three.`,
      createdAt: iso(18 * DAY),
    },
  ]),
  conv("c-support-macros", "Support Macro Library", 24 * DAY, "nova-fast", [
    {
      id: mid(),
      role: "user",
      content: "Write 3 support macros for billing disputes.",
      createdAt: iso(24.1 * DAY),
    },
    {
      id: mid(),
      role: "assistant",
      content: `**1 · Duplicate charge**
"I can see both charges on your account and I've refunded the second one. It should land in 5–7 business days."

**2 · Unexpected upgrade**
"Your plan changed on {{date}} when seats went from {{a}} to {{b}}. I can prorate that back if it wasn't intended."

**3 · Failed payment**
"Your last invoice didn't go through, so the account is in a grace period until {{date}}. Here's a secure link to update the card."`,
      createdAt: iso(24 * DAY),
    },
  ]),
  conv(
    "c-archived-brand",
    "Old Brand Guidelines Notes",
    41 * DAY,
    "nova-fast",
    [
      {
        id: mid(),
        role: "user",
        content: "Summarize our 2024 brand guidelines.",
        createdAt: iso(41.1 * DAY),
      },
      {
        id: mid(),
        role: "assistant",
        content:
          "Archived summary: two typefaces, a single accent, and a rule against gradients in product UI.",
        createdAt: iso(41 * DAY),
      },
    ],
    true,
  ),
];

/** Canned assistant replies used by the mock streaming layer. */
export const MOCK_REPLIES: string[] = [
  `Here's how I'd approach that.

### The short answer
Start with the smallest version that produces a real result, then expand only where you feel friction.

### Why this order works
1. It surfaces the hard constraint early.
2. You get something reviewable within a day.
3. Anything you cut later costs almost nothing.

### Next step
Pick the single output you'd show someone tomorrow, and work backwards from it. Want me to draft that first version?`,

  `Good question — there are three ways to read it, and they lead somewhere different.

- **Fastest:** reuse what exists and accept some rough edges.
- **Cleanest:** rebuild the core piece, roughly 2× the effort.
- **Balanced:** keep the current surface, replace the layer underneath.

| Option | Effort | Risk | Best when |
| --- | --- | --- | --- |
| Fastest | Low | Medium | Deadline is fixed |
| Cleanest | High | Low | You'll live here for years |
| Balanced | Medium | Low | Most of the time |

I'd take balanced unless the deadline is immovable.`,

  `Let me break it down.

**What's happening**
The behaviour you're describing usually comes from state being derived in two places, so the two copies drift.

**The fix**

\`\`\`ts
// one source of truth, derived on read
const visible = useMemo(
  () => items.filter((i) => matches(i, query)),
  [items, query],
);
\`\`\`

**How to verify**
Change the input twice quickly. If the list settles correctly, the drift is gone.`,

  `Here's a draft you can edit.

> Nova helps teams turn scattered notes, files and data into decisions they can act on the same day.

Three variations by emphasis:
1. **Speed** — "Decisions in an afternoon, not a sprint."
2. **Clarity** — "One place where the numbers agree."
3. **Scope** — "From raw export to shareable summary."

Tell me which one feels closest and I'll take it further.`,

  `Short version: yes, but with one condition.

It works well as long as the inputs stay small and predictable. Once they grow past a few thousand items you'll want pagination and a cursor, otherwise the first render gets expensive.

A reasonable checkpoint: revisit this when you cross 2,000 records or 300 ms of render time, whichever comes first.`,
];
