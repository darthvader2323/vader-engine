# Darth Vader Chat character community

A coordinated, clearly disclosed Telegram character-bot service for Darth Vader Chat.
Telegram account status and each profile identify the automated character. Message
bodies do not repeat identity prefixes. The characters are
unofficial fictional personas, not independent people, customers or endorsements.

## Behavior

- One designated polling bot reads group messages; one bot answers each service request.
  TG_READER_NAME selects the listener independently of the service responder. Production
  uses Yoda because the delivery check verified incoming updates on that identity.
- Service questions direct the person to @darthvader privately.
- Owner questions follow the same topic routing and receive relevant replies.
- Directly addressing a configured character selects that voice, except service requests
  still go to the single service desk. Yoda uses inverted, reflective phrasing; Luke is
  hopeful, Chewbacca is direct, Bruce is measured and Chucky is playful. Character
  wording is authored inside the discussion itself. News has no stock introduction;
  facts and dates are retained, with a short plain-text source label. Routine posts
  contain no visible article URLs; bare feed hostnames are rendered as publisher
  names so Telegram does not auto-link them. Most source labels are plain text.
  An occasional short clickable source is allowed on every tenth scheduled news
  post, with at least an hour between links across the entire group. Replies do
  not automatically add links or consume that schedule. The counter and deadline
  survive restarts and checkpoints.
- A new pin gets one neutral assistant acknowledgement, without a swarm of automated likes.
- Scheduled posts rotate between Star Wars, NBA YoungBoy, sports, crypto, business deals,
  Elon Musk, world news and dated Fragment sale reports when available.
- News includes a publication date and plain-text source name. Failed feeds are skipped.
- Scheduled Star Wars discussion can use twelve short, authored two-persona
  exchanges with distinct viewpoints. The second turn is a native reply after
  45–120 seconds; real human activity pauses it. Only configured profiles are
  used. These are disclosed automated fan personas with character-inspired
  voices, not independent humans or
  customer endorsements. Each exchange runs once, preserves its place through
  worker handovers, and gives the room a pause before another broadcast.
  Four exchanges are light fan-persona banter, directed only at the fictional
  profiles rather than real visitors. Eligible topic order is mixed,
  and scheduled speakers vary among quieter profiles rather than following a
  fixed cycle of names. Existing topic cooldowns and repetition checks remain.
- Crypto snapshots use the actual quoted figures as their shared repeat key.
  A fresh price request is not blocked just because an earlier update was sent
  in the same clock hour; unchanged figures still share one key.
- TON is labeled TON. Pregame fixtures are labeled scheduled, without fake live 0–0 scores.
- No invented sales, hardcoded market numbers, claims to own the desired usernames,
  manufactured praise, fake personal experiences, or automated crowd endorsements.
- A discussion idea has one shared key across every character. Old wording variations
  migrate to that same key. Recent hashed headline fingerprints also reject near-duplicates
  across sources and speakers; changed numerical facts and negations are preserved.
  Necessary service contact details may recur in answers to separate requests.
- Speakers rotate across topics, with 3–6 minutes between production broadcast checks.
  Topic cooldowns prevent repeated prompts, and broadcasts give active human conversation
  90 seconds of space. Scheduled music posts require fresh news; unavailable feeds and
  unsupported questions do not produce repeated filler. Explicit help is rate limited.
  The worker checks incoming requests every five seconds between network operations.
- The @trillion context line appears at most once per day in scheduled business posts.
- Stickers must be animated or video stickers. A shared unique-ID ledger prevents repeats,
  including across different bot tokens. Exhausted/static packs are skipped.
- Moving stickers match the speaking character: Yoda uses Yoda, Luke uses Luke,
  Chewbacca uses Chewbacca and Chucky uses Chucky. Bruce Wayne uses a Batman pack
  only when one is configured. A missing or exhausted matching pack is skipped;
  another character is never substituted. This supersedes the earlier mixed-pack
  Darth Vader weighting.

## Running

Python 3.11 or later is sufficient; no third-party Python packages are required.
Run the tests with: python3 -m unittest -v test_community
Run the worker with: python3 run.py
Run read-only connectivity checks with: python3 healthcheck.py

This is a sourced-update worker with a finite authored discussion catalog in
conversation.py. No open-ended language-model API is configured. Exhausted ideas are
skipped instead of being reworded and replayed.
The catalog contains 35 different Star Wars discussion ideas with separate authored
voices, grounded in the official references listed in DISCUSSION_REFERENCES.
Star Wars becomes eligible again after 15 minutes, sports after 10 minutes, and
other topics after 15–60 minutes. Each still requires a genuinely unused item.
The worker emits a heartbeat in its operational log about once a minute, including
the time since a successful send and the next broadcast check. Deferral reasons
are logged without adding filler messages to the group.

CHAT_ID must be the numeric ID of the authorized group. Tokens stay in deployment secrets.
CHAT_HANDLE can additionally name its public address (@darthvaderchat2). At startup the
worker verifies the group title/handle and resolves its canonical numeric ID, so a group
upgrade or an older ID alias cannot silently discard incoming messages.
Unavailable account identities are excluded for that run and checked again on restart.
A newly selected listener skips existing backlog once, then checkpoints its update offset.
Existing token names are TG_JOHNNY, TG_YODA, TG_LUKE, TG_CHEW, TG_CHUCKY and TG_VADER.
Additional owned bots can be configured in BOT_TOKENS_JSON as a JSON object mapping roster
names or their TG_ environment-variable names to tokens. Duplicate tokens are ignored.
Adding a roster name or a secret does not create a Telegram bot or buy a username.

Managed profiles can instead use the existing Bruce manager token. After the owner
creates a profile through Telegram's managed-bot flow, MANAGED_BOTS_JSON maps its
roster name to its public numeric bot ID, for example {"tonysoprano": 123456789}.
TG_MANAGER_NAME selects the manager (brucewayne by default). The worker fetches
the child token using getManagedBotToken at startup and keeps it only in memory;
no child tokens go in repository files, runtime checkpoints, or logs. Existing
configured identities take precedence, and duplicate or unknown records are rejected.
A regular worker activates a managed profile only after verifying its identity,
disabled group privacy, a profile picture, and membership in the authorized group.
The separate profiles command can prepare metadata before it joins. Its display
name uses the roster name directly; its description still discloses automation.
Missing avatar files leave profile setup incomplete, including for newly registered
characters. Existing Bruce/Chewbacca/Luke avatar filename aliases are supported.

This connection code does not register accounts, add them to a group, change privacy
mode, or grant administrators. Those remain Telegram operations. Managed-bot
creation uses Telegram's official flow and remains subject to Telegram's limits:
https://core.telegram.org/bots/features#managed-bots

Profile setup sets the display name, a clear bot description and an existing matching
avatar. It does not automatically grant administrator permissions.

RUN_MINUTES defaults to 48 for the existing GitHub runner. Use 0 only on a supervised
persistent host. GAP_MIN/GAP_MAX set the scheduled-post interval in seconds.
VADER_TIMEZONE defaults to America/Chicago.

## Sticker sources

STICKER_PACKS_JSON can supply a character-to-pack-name map.
CHUCKY_STICKER_PACK and YOUNGBOY_STICKER_PACK configure those additional packs.
Only packs actually containing unused animated/video assets can produce moving stickers.
The worker never substitutes a static image or resets the used-sticker ledger.
Pack keys follow the character identity, with vader, chew and luke as aliases for
Darth Vader, Chewbacca and Luke Skywalker; brucewayne maps to batman and the
unofficial NBA YoungBoy fan persona maps to youngboy. Broad legacy roster pack
assignments such as crew or han are not used as identity fallbacks.

Telegram rate-limit deadlines are saved by bot identity and restored on restart.
Failed sticker lookups are not cached as empty packs. Profile setup remembers each
successful field separately and delays incomplete setup for at least an hour, so a
failed avatar update cannot cause repeated name and description writes.

## Fragment feed contract

FRAGMENT_SALES_FEED_URL defaults to the previously configured namespace.my endpoint.
A usable record requires username, numeric price, currency TON, status sold, an explicitly
dated sold_at value and an HTTPS source URL on fragment.com, tonviewer.com or tonscan.org.
Records older than three days, missing fields, wrong units and unavailable providers are
skipped. Provider records are described as reported sales, not independently verified
blockchain transactions. There is no fallback list of supposed recent sales.

## Persistence and hosting

The one active workflow is engine.yml (Vader Character Community), scheduled from main.
It validates and runs an immutable verified release, loads the latest ledger from
community-live and saves runtime checkpoints there.
This separates production from overlapping experiments on main. The old room.yml is
manual-only and does not post. Production workers share a concurrency group and do not
cancel an active worker every ten minutes.

State is atomically written to state/runtime.json. It contains deduplication hashes,
message/update IDs, sticker IDs, hashed recent-content signatures and timing/profile
metadata, not message bodies or tokens. Recent signatures are capped at 100 entries
and compared for 48 hours; checkpoint merges preserve both workers' recent history.
The checkpoint updates only that file and merges ledgers/offsets, preserving concurrent
code changes. Checkpoints require the workflow's repository-scoped GITHUB_TOKEN.

GitHub scheduled runs are best effort: they can be delayed or skipped. This setup does not
guarantee uninterrupted operation. A supervised persistent host and durable external state
are the appropriate next step for stronger uptime requirements or a much larger deployment.

The GitHub workflow supports run, probe (read-only), validate (tests only), and
profiles (separate metadata setup). Normal runs do not repeatedly rewrite profiles.
BotFather creation limits, username availability and administrator grants remain controlled
by Telegram. This repository does not bypass those controls.
