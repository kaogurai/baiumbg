# sfx cog

this is a fork of [baiumbg](https://github.com/baiumbg/baiumbg-Cogs)'s original SFX cog for Red-DiscordBot

due to the backend TTS library, gTTS, using the python library requests, it caused many blocking issues

the TTS command has been rewritten to use my self-hosted [openTTS](https://github.com/synesthesiam/opentts) server, but of course you can change it to use yours with the `[p]ttsurl <url>` command (plz do this so my VPS doesn't die lol)

in addition, i have added TTS channels and global SFX