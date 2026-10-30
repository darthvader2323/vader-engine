# vader-engine

Autonomous 24/7 persona ensemble for **Darth Vader Chat** (Telegram).

## Content
- **Fragment** - live username sales (namespace.my), NFTs on TON
- **Crypto** - live GRAM / BTC / ETH (CoinGecko)
- **Sports** - NBA, WNBA, NHL, MLB, NFL, MLS, EPL, UCL (ESPN)
- **Deals** - M&A headlines from the @trillion feed
- **World** - BBC world / business / tech RSS
- **Elon** - Grok / SpaceX / xAI
- **Debates** - who is the best Star Wars character, with arguments
- **Stickers** - 10 Star Wars packs, never the same sticker twice

## Realism rules
- One persona answers each human message (service questions -> @darthvader only)
- Bots never reply to bots
- Every reply is unique - a used-reply ledger prevents repeats
- Like counts vary: sometimes 1, sometimes everyone
- Reactions mix: heart, thumbs up, fire, etc.
- Sticker ledger prevents repeats

## State
`state/` lives in the repo and is committed back each run, so the update
offset, seen-message ledger, reply ledger and sticker ledger persist.
`actions/cache` is a second layer.

## Secrets
`CHAT_ID`, `TG_JOHNNY`, `TG_YODA`, `TG_LUKE`, `TG_CHEW`, `TG_CHUCKY`, `TG_VADER`

Add new bots by adding `TG_<NAME>` secrets - the engine picks them up automatically.
