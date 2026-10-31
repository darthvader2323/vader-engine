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
- New standalone greetings, including "what's up!", can receive one short native
  reply from one disclosed character and one thumbs-up acknowledgement from that
  same character. Recognized greetings include hello, hi, hey, yo, good morning
  and /hello. This uses the existing polling worker, credentials and permission
  scope. It adds no separate welcome workflow and never backfills older greetings.
  Per-person ten-minute and group twenty-second cooldowns avoid repeated welcomes.
  Human-to-human replies are left alone. Bots, other groups, duplicate updates
  and uncertain deliveries cannot trigger a swarm. The greeting activation time,
  visitor hashes, cooldowns and variant count persist through checkpoints.
- Reading styles split the configured profiles as evenly as possible between
  analytical and plain wording. The groups swap at midnight in VADER_TIMEZONE
  (America/Chicago in this deployment), deterministically across worker restarts.
  With five profiles, the two/three split reverses each day. Plain wording uses
  short, authored fan comments and familiar language; it does not invent a child
  identity or deliberate factual mistakes. Shared idea keys and repeat history
  apply across both styles, so a new day never replays an exhausted idea.
  Source headlines keep their facts and uncertainty; only a small set of safe
  vocabulary changes is allowed outside quotes. All numbers and uncertainty
  remain intact. Market quotes expand abbreviations in the plain style.
- Owner questions follow the same topic routing and the same single-character
  reply rule. A recognized hypothetical Mars-trip question gets an authored
  fictional viewpoint, rather than an Elon/SpaceX news headline. The seven
  configured voices have distinct analytical/plain versions of that one shared
  idea. This is a bounded rule and catalog, not open-ended question answering.
  Feed replies require an explicit update/price/score/sale request, and named
  supported subjects must match the returned item. Unsupported direct questions
  are skipped instead of being answered with an unrelated headline.
- Directly addressing a configured character selects that voice, except service requests
  still go to the single service desk. Yoda uses inverted, reflective phrasing; Luke is
  hopeful, Chewbacca is direct, Bruce is measured and Chucky is playful. Character
  wording is authored inside the discussion itself. Routine updates omit the
  feed's publisher/date/time footer, while retrieval still verifies freshness
  and source links. Actual game times, price windows and dates inside a story
  remain when they carry meaning. Market quotes use conversational sentences;
  planned acquisitions stay plans rather than becoming completed sales.
  There is no stock introduction. An occasional compact 'More here' link is
  allowed on every tenth scheduled news post, with at least an hour between
  links across the entire group. Replies do
  not automatically add links or consume that schedule. The counter and deadline
  survive restarts and checkpoints.
- Pins never get a generic acknowledgement or a swarm of automated likes.
  A fresh, unanswered human question can receive one relevant native reply using
  the same routing. A previously answered message is not answered again because
  it was pinned. Old/bot/unsupported pins are recorded quietly; pin handling
  cannot attach a separate reaction GIF. Existing pin/reply histories survive.
- Scheduled posts rotate between Star Wars, NBA YoungBoy, sports, crypto, business deals,
  Elon Musk, world news and dated Fragment sale reports when available.
- One daily KJV Bible passage is eligible from noon America/Chicago, using
  Bible Gateway's documented public Verse of the Day feed. The worker checks
  the feed's actual date, version, Bible reference and canonical source link.
  Scripture wording and its reference are preserved exactly; no article footer,
  promotion, unrelated GIF or reaction crowd is attached. The local-day claim
  uses the existing checkpointed timing ledger and survives restarts and unknown
  deliveries. Failed/stale feeds and already used passages are skipped. Human
  conversation and pending fan threads keep their existing priority. This adds
  no second poster or separate automation. Scheduled execution remains best effort.
- News freshness is checked before rendering. Failed feeds are skipped.
- Scheduled Star Wars discussion can use fourteen short, authored two-persona
  exchanges with distinct viewpoints. The second turn is a native reply after
  45–120 seconds; real human activity pauses it. Only configured profiles are
  used. These are disclosed automated fan personas with character-inspired
  voices, not independent humans or
  customer endorsements. Each exchange runs once, preserves its place through
  worker handovers, and gives the room a pause before another broadcast.
  A rejected followup is attempted at most three times; an exchange expires
  after ten minutes. Neither a permanent Telegram error nor continuous visitor
  activity can leave an old exchange blocking future broadcasts indefinitely.
  Six exchanges are light fan-persona banter, directed only at the fictional
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
- Movie reactions also match the accompanying comment's mood. A reviewed catalog
  labels the ordered clips in the owned character packs; unknown packs, unknown
  slots, exhausted moods and mismatched emotions are skipped. A sad Yoda comment
  cannot select a laughing clip or another character. The small rule-based mood
  selector uses explicit cues, defaults uncertain tone to serious, and avoids
  reactions to distressing real-world headlines. Successful topical comments,
  including native answers and fan-thread turns, can attach a reaction as a
  native reply to that exact comment. Failed/uncertain text deliveries, service
  replies, pins and help do not trigger clips. There is no context-free startup
  sticker. The permanent used-ID ledger still applies across every mood.

## Running

Python 3.11 or later is sufficient; no third-party Python packages are required.
Run the tests with: python3 -m unittest -v test_community
Run the worker with: python3 run.py
Run read-only connectivity checks with: python3 healthcheck.py

This is a sourced-update worker with a finite authored discussion catalog in
conversation.py. No open-ended language-model API is configured. Exhausted ideas are
skipped instead of being reworded and replayed.
The catalog contains 42 different Star Wars discussion ideas with separate authored
voices, grounded in the official references listed in DISCUSSION_REFERENCES.
Star Wars becomes eligible again after 15 minutes, sports after 10 minutes, and
other topics after 15–60 minutes. Each still requires a genuinely unused item.
The worker emits a heartbeat in its operational log about once a minute, including
the time since a successful send and the next broadcast check. Deferral reasons
are logged without adding filler messages to the group.

CHAT_ID must be the numeric ID of the authorized group. Tokens stay in deployment secrets.
CHAT_HANDLE can additionally name its public address (@vadersocial). At startup the
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

Tony Soprano has a matching SFW fan avatar and 42 separately authored takes in
tony_voice.py and vader_discussions.py, each with analytical and plain wording. These reuse the room's
existing idea keys, so activating Tony or changing his daily style cannot replay
exhausted discussions. His profile remains an unofficial automated fan persona.

The requested generic alias killer is an original fictional sci-fi fan persona,
with a SFW masked-character avatar and a restrained authored voice. Its 42 ideas
have separate analytical/plain wording and share the same room history keys.
There is no reviewed movie pack for this original character; it must not borrow
another character's face or replay somebody else's clips.

Future human-member join events use the existing bounded greeting path: one
character sends one native welcome, with no welcome swarm or service-message
reaction. Each configured voice has eight distinct short greetings.
The shared counter rotates the wording and survives restarts. Human arrivals
share the existing ten-minute person cooldown and twenty-second room cooldown;
a batch join gets one welcome. Bot arrivals and pre-activation joins are skipped.
Disable legacy clone welcome handlers before enabling this join path in production.

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

The Tony pack appends three reviewed live-action reactions for serious, sad and
happy/playful comments. The sitting scene is an HBO GIPHY upload; the crying and
winking scenes are attributed community uploads on GIPHY and Tenor. The previous
31 ordered assets, pack slots and used identities are unchanged.
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

Normal production runs confirm durable ledger saves during operation, including the
claims made before sending text or a moving reaction. The single posting process
receives Telegram credentials; a separate local checkpoint helper receives only the
existing repository credential and no Telegram credentials. If the helper cannot
confirm a save, posting stops. The final workflow checkpoint remains as a fallback.
Versioned claims preserve both uncertain deliveries and explicit rollbacks after a
known rejection, so a delayed older checkpoint cannot undo a successful rollback.

GitHub scheduled runs are best effort: they can be delayed or skipped. This setup does not
guarantee uninterrupted operation. A supervised persistent host and durable external state
are the appropriate next step for stronger uptime requirements or a much larger deployment.

The GitHub workflow supports run, probe (read-only), validate (tests only), and
profiles (separate metadata setup). Normal runs do not repeatedly rewrite profiles.
BotFather creation limits, username availability and administrator grants remain controlled
by Telegram. This repository does not bypass those controls.
