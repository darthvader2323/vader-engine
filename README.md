# vader-engine

Autonomous persona engine for **Darth Vader Chat** (Telegram).

Posts beats with live data and answers human messages:

- **Fragment** - live username sales (namespace.my API), NFTs on TON
- **Crypto** - live GRAM / BTC / ETH from CoinGecko
- **Sports** - live NBA / NHL / MLB / NFL / MLS / EPL / UCL / WNBA from ESPN
- **Business deals** - filtered M&A headlines (the @trillion feed)
- **World news** - BBC world / business / tech RSS
- **Elon** - Grok / SpaceX / xAI updates
- **Debate** - two personas argue over the best Star Wars character

Rules: one persona answers each human message, bots never reply to bots,
sentences never repeat, stickers never repeat, like counts are mixed.

## Secrets

Required repository secrets: `CHAT_ID`, `TG_JOHNNY`, `TG_YODA`, `TG_LUKE`,
`TG_CHEW`, `TG_CHUCKY`, `TG_VADER`.

The workflow runs every 3 hours. Trigger it manually from the Actions tab.
