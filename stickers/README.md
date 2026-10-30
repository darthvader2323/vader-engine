# Vader Social video stickers

Eight actual moving clips encoded as silent VP9 WEBM files for Telegram. Three are Darth Vader, with one each of Yoda, Luke Skywalker, Chewbacca, Chucky and NBA YoungBoy.

`manifest.json` preserves the original GIPHY post and creator for each clip. These are unofficial fan sticker conversions of existing published clips, not newly generated footage or endorsements. Source artwork remains with its respective rights holders.

Each file has a 512-pixel longest edge, a duration below three seconds, at most 30 frames per second, no audio, and a size below 256 KiB. `validation.json` records dimensions, duration, bytes, frame uniqueness and SHA-256. Run `python3 stickers/build.py` to validate the packaged files. Rebuild from downloaded GIF source files with `python3 stickers/build.py /path/to/source-gifs` (requires Pillow and FFmpeg).

`sticker_setup.py` creates character-specific packs owned by the verified group creator @darthvader using an existing bot. It does not create new bots, request expanded permissions, or bypass Telegram cooldowns. It checks for existing packs before creation, stops on rate limits, and never prints credentials. An optional test sends a single Vader video sticker to the configured group.
