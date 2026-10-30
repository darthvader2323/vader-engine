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
  facts and dates are retained, with the source attached as a compact clickable label.
- A new pin gets one neutral assistant acknowledgement, without a swarm of automated likes.
- Scheduled posts rotate between Star Wars, NBA YoungBoy, sports, crypto, business deals,
  Elon Musk, world news and dated Fragment sale reports when available.
- News includes a publication date and source link. Failed feeds are skipped.
- TON is labeled TON. Pregame fixtures are labeled scheduled, without fake live 0–0 scores.
- No invented sales, hardcoded market numbers, claims to own the desired usernames,
  manufactured praise, fake personal experiences, or automated crowd endorsements.
- A discussion idea has one shared key across every character. Old wording variations
  migrate to that same key. Recent hashed headline fingerprints also reject near-duplicates
  across sources and speakers; changed numerical facts and negations are preserved.
  Necessary service contact details may recur in answers to separate requests.
- Speakers rotate across topics, with 8–14 minutes between production broadcasts.
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
