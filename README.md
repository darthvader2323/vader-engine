# Darth Vader Chat character community

A coordinated, clearly disclosed Telegram character-bot service for Darth Vader Chat.
Telegram account status and each profile identify the automated character. Message
bodies do not repeat identity prefixes. The characters are
unofficial fictional personas, not independent people, customers or endorsements.

## Behavior

- One designated polling bot reads group messages; one bot answers each service request.
- Service questions direct the person to @darthvader privately.
- Owner questions follow the same topic routing and receive relevant replies.
- A new pin gets one neutral assistant acknowledgement, without a swarm of automated likes.
- Scheduled posts rotate between Star Wars, NBA YoungBoy, sports, crypto, business deals,
  Elon Musk, world news and dated Fragment sale reports when available.
- News includes a publication date and source link. Failed feeds are skipped.
- TON is labeled TON. Pregame fixtures are labeled scheduled, without fake live 0–0 scores.
- No invented sales, hardcoded market numbers, claims to own the desired usernames,
  manufactured praise, fake personal experiences, or automated crowd endorsements.
- Scripted discussion prompts and news items are not replayed. Necessary service contact
  details may recur in answers to separate requests.
- Speakers rotate for variety, with a default 10–20 minutes between scheduled text posts.
  The worker checks incoming requests every five seconds between network operations.
- Stickers must be animated or video stickers. A shared unique-ID ledger prevents repeats,
  including across different bot tokens. Exhausted/static packs are skipped.
- Darth Vader has four times the selection weight of each other pack when unused moving
  stickers are available. This cannot create moving assets missing from a pack.

## Running

Python 3.11 or later is sufficient; no third-party Python packages are required.
Run the tests with: python3 -m unittest -v test_community
Run the worker with: python3 run.py
Run read-only connectivity checks with: python3 healthcheck.py

CHAT_ID must be the numeric ID of the authorized group. Tokens stay in deployment secrets.
CHAT_HANDLE can additionally name its public address (@darthvaderchat2). At startup the
worker verifies the group title/handle and resolves its canonical numeric ID, so a group
upgrade or an older ID alias cannot silently discard incoming messages.
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
message/update IDs, sticker IDs and timing/profile metadata, not message bodies or tokens.
The checkpoint updates only that file and merges ledgers/offsets, preserving concurrent
code changes. Checkpoints require the workflow's repository-scoped GITHUB_TOKEN.

GitHub scheduled runs are best effort: they can be delayed or skipped. This setup does not
guarantee uninterrupted operation. A supervised persistent host and durable external state
are the appropriate next step for stronger uptime requirements or a much larger deployment.

The GitHub workflow supports run, probe (read-only), validate (tests only), and
profiles (separate metadata setup). Normal runs do not repeatedly rewrite profiles.
BotFather creation limits, username availability and administrator grants remain controlled
by Telegram. This repository does not bypass those controls.
