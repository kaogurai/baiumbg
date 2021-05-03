from redbot.core import commands, checks, data_manager, Config
from .api import TTSAPI
import tempfile
import discord
import os
import random
import lavalink
import aiohttp
import pydub


class SFX(commands.Cog):
    """Plays uploaded sounds or text-to-speech."""

    def __init__(self, bot):
        self.bot = bot
        self.last_track_info = None
        self.current_sfx = None
        self.config = Config.get_conf(self, identifier=134621854878007296)
        self.sound_base = (data_manager.cog_data_path(self) / "sounds").as_posix()
        self.session = aiohttp.ClientSession()
        user_config = {"voice": "clara", "speed": 0}
        guild_config = {"sounds": {}, "channels": []}
        global_config = {"sounds": {}}
        self.config.register_user(**user_config)
        self.config.register_guild(**guild_config)
        self.config.register_global(**global_config)
        lavalink.register_event_listener(self.ll_check)
        if not os.path.exists(self.sound_base):
            os.makedirs(self.sound_base)

    def __unload(self):
        lavalink.unregister_event_listener(self.ll_check)

    @commands.command()
    @commands.cooldown(
        rate=1, per=1, type=discord.ext.commands.cooldowns.BucketType.guild
    )
    async def tts(self, ctx, *, text):
        """
        Plays the given text as TTS in your current voice channel.
        """

        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("You are not connected to a voice channel.")
            return

        audio_file = os.path.join(
            tempfile.gettempdir(),
            "tts/",
            "".join(random.choice("0123456789ABCDEF") for i in range(15)) + ".mp3",
        )
        author_voice = await self.config.user(ctx.author).voice()
        author_speed = await self.config.user(ctx.author).speed()

        encoded_string = text.encode("ascii", "ignore")
        decoded_string = encoded_string.decode()

        if not decoded_string:
            await ctx.send("That's not a valid message, sorry.")
            return

        if len(decoded_string) > 1000:
            await ctx.send(
                "Sorry, I only allow messages with 1000 characters or below to be spoken."
            )
            return

        await TTSAPI.get_audio(
            self, decoded_string, author_voice, author_speed, audio_file
        )

        try:
            audio_data = pydub.AudioSegment.from_file(audio_file)
        except Exception:
            await ctx.send("Uh oh, an error occured. The text you provided most likely isn't a valid message.")
            return

        silence = pydub.AudioSegment.silent(duration=750)
        padded_audio = silence + audio_data
        padded_audio.export(audio_file)

        try:
            await self._play_sfx(ctx.author.voice.channel, audio_file, True)
        except Exception:
            await ctx.send("Lavalink doesn't seem to be ready, please try again later.")
            return

    @commands.command()
    @commands.cooldown(
        rate=1, per=1, type=discord.ext.commands.cooldowns.BucketType.guild
    )
    async def sfx(self, ctx, sound: str):
        """
        Plays an existing sound in your current voice channel.
        If a guild SFX exists with the same name as a global one, the guild SFX will be played.
        """

        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("You are not connected to a voice channel.")
            return

        if str(ctx.guild.id) not in os.listdir(self.sound_base):
            os.makedirs(os.path.join(self.sound_base, str(ctx.guild.id)))

        guild_sounds = await self.config.guild(ctx.guild).sounds()
        global_sounds = await self.config.sounds()

        if sound not in guild_sounds.keys():
            if sound not in global_sounds.keys():
                await ctx.send(
                    f"Sound **`{sound}`** does not exist. Try `{ctx.prefix}listsfx` for a list."
                )
                return

        if sound in guild_sounds.keys():
            filepath = os.path.join(
                self.sound_base, str(ctx.guild.id), guild_sounds[sound]
            )
        else:
            filepath = os.path.join(self.sound_base, global_sounds[sound])

        if not os.path.exists(filepath):
            if sound in guild_sounds.keys():
                del guild_sounds[sound]
                await self.config.guild(ctx.guild).sounds.set(guild_sounds)
                await ctx.send(
                    "Looks like this sound's file has gone missing! I've removed it from the list of guild sounds."
                )
                if sound in global_sounds.keys():
                    del global_sounds[sound]
                    await self.config.sounds.set(global_sounds)
                    await ctx.send(
                        "Looks like this sound's file has gone missing! I've removed it from the list of global sounds."
                    )
                    return
                else:
                    return
            if sound in global_sounds.keys():
                del global_sounds[sound]
                await self.config.sounds.set(global_sounds)
                await ctx.send(
                    "Looks like this sound's file has gone missing! I've removed it from the list of global sounds."
                )
                if sound in global_sounds.keys():
                    del global_sounds[sound]
                    await self.config.sounds.set(global_sounds)
                    await ctx.send(
                        "Looks like this sound's file has gone missing! I've removed it from the list of guild sounds."
                    )
                    return
                else:
                    return
            else:
                await ctx.send("Sorry, I can't seem to find that SFX.")

        await self._play_sfx(ctx.author.voice.channel, filepath)

    @commands.command()
    @checks.mod()
    async def addsfx(self, ctx, name: str, link: str = None):
        """Adds a new sound.
        Either upload the file as a Discord attachment and make your comment
        `[p]addsfx <name>`, or use `[p]addsfx <name> <direct-URL-to-file>`.
        """
        guild_sounds = await self.config.guild(ctx.guild).sounds()

        if str(ctx.guild.id) not in os.listdir(self.sound_base):
            os.makedirs(os.path.join(self.sound_base, str(ctx.guild.id)))

        attach = ctx.message.attachments
        if len(attach) > 1 or (attach and link):
            await ctx.send("Please only add one sound at a time.")
            return

        url = ""
        filename = ""
        if attach:
            a = attach[0]
            url = a.url
            filename = a.filename
        elif link:
            url = "".join(link)
            filename = os.path.basename("_".join(url.split()).replace("%20", "_"))
        else:
            await ctx.send(
                "You must provide either a Discord attachment or a direct link to a sound."
            )
            return

        _, file_extension = os.path.splitext(filename)
        if file_extension != ".wav" and file_extension != ".mp3":
            await ctx.send("Only .wav and .mp3 sounds are currently supported.")
            return

        filepath = os.path.join(self.sound_base, str(ctx.guild.id), filename)

        if name in guild_sounds.keys():
            await ctx.send(
                "A sound with that name already exists. Please choose another name and try again."
            )
            return

        if os.path.exists(filepath):
            await ctx.send(
                "A sound with that filename already exists. Please change the filename and try again."
            )
            return

        async with self.session.get(url) as new_sound:
            f = open(filepath, "wb")
            f.write(await new_sound.read())
            f.close()

        audio_data = pydub.AudioSegment.from_file(filepath)
        silence = pydub.AudioSegment.silent(duration=750)
        padded_audio = silence + audio_data
        padded_audio.export(filepath)

        guild_sounds[name] = filename
        await self.config.guild(ctx.guild).sounds.set(guild_sounds)

        await ctx.send(f"Sound **{name}** added.")

    @commands.command()
    @commands.is_owner()
    async def addglobalsfx(self, ctx, name: str, link: str = None):
        """Adds a new sound globally.

        Either upload the file as a Discord attachment and make your comment
        `[p]addglobalsfx <name>`, or use `[p]addglobalsfx <name> <direct-URL-to-file>`.
        """

        global_sounds = await self.config.sounds()

        attach = ctx.message.attachments
        if len(attach) > 1 or (attach and link):
            await ctx.send("Please only add one sound at a time.")
            return

        url = ""
        filename = ""
        if attach:
            a = attach[0]
            url = a.url
            filename = a.filename
        elif link:
            url = "".join(link)
            filename = os.path.basename("_".join(url.split()).replace("%20", "_"))
        else:
            await ctx.send(
                "You must provide either a Discord attachment or a direct link to a sound."
            )
            return

        _, file_extension = os.path.splitext(filename)
        if file_extension != ".wav" and file_extension != ".mp3":
            await ctx.send("Only .wav and .mp3 sounds are currently supported.")
            return

        filepath = os.path.join(self.sound_base, filename)

        if name in global_sounds.keys():
            await ctx.send(
                "A sound with that name already exists. Please choose another name and try again."
            )
            return

        if os.path.exists(filepath):
            await ctx.send(
                "A sound with that filename already exists. Please change the filename and try again."
            )
            return

        async with self.session.get(url) as new_sound:
            f = open(filepath, "wb")
            f.write(await new_sound.read())
            f.close()
        try:
            audio_data = pydub.AudioSegment.from_file(filepath)
        except pydub.CouldntDecodeError:
            await ctx.send("Uh oh, an error occured. Please try again later.")
            return
        silence = pydub.AudioSegment.silent(duration=500)
        padded_audio = silence + audio_data
        padded_audio.export(filepath)

        global_sounds[name] = filename
        await self.config.sounds.set(global_sounds)

        await ctx.send(f"Sound **{name}** added.")

    @commands.command()
    @checks.mod()
    async def delsfx(self, ctx, soundname: str):
        """
        Deletes an existing sound.
        """

        if str(ctx.guild.id) not in os.listdir(self.sound_base):
            os.makedirs(os.path.join(self.sound_base, str(ctx.guild.id)))

        cfg_sounds = await self.config.guild(ctx.guild).sounds()

        if soundname not in cfg_sounds.keys():
            await ctx.send(
                f"Sound **{soundname}** does not exist. Try `{ctx.prefix}listsfx` for a list."
            )
            return

        filepath = os.path.join(
            self.sound_base, str(ctx.guild.id), cfg_sounds[soundname]
        )

        if os.path.exists(filepath):
            os.remove(filepath)

        del cfg_sounds[soundname]
        await self.config.guild(ctx.guild).sounds.set(cfg_sounds)

        await ctx.send(f"Sound **{soundname}** deleted.")

    @commands.command()
    @checks.is_owner()
    async def delglobalsfx(self, ctx, soundname: str):
        """
        Deletes an existing global sound.
        """

        global_sounds = await self.config.sounds()

        if soundname not in global_sounds.keys():
            await ctx.send(
                f"Sound **{soundname}** does not exist. Try `{ctx.prefix}listsfx` for a list."
            )
            return

        filepath = os.path.join(self.sound_base, global_sounds[soundname])

        if os.path.exists(filepath):
            os.remove(filepath)

        del global_sounds[soundname]
        await self.config.sounds.set(global_sounds)

        await ctx.send(f"Sound **{soundname}** deleted.")

    @commands.command()
    async def listsfx(self, ctx):
        """
        Prints all available sounds for this server.
        """

        if str(ctx.guild.id) not in os.listdir(self.sound_base):
            os.makedirs(os.path.join(self.sound_base, str(ctx.guild.id)))

        guild_sounds = await self.config.guild(ctx.guild).sounds()
        global_sounds = await self.config.sounds()

        if (len(guild_sounds.items()) + len(global_sounds.items())) == 0:
            await ctx.send(f"No sounds found. Use `{ctx.prefix}addsfx` to add one.")
            return

        guild_paginator = discord.ext.commands.help.Paginator()
        global_paginator = discord.ext.commands.help.Paginator()
        for soundname, filepath in guild_sounds.items():
            guild_paginator.add_line(soundname)
        for soundname, filepath in global_sounds.items():
            global_paginator.add_line(soundname)

        await ctx.send("Guild sounds for this server:")
        for page in guild_paginator.pages:
            await ctx.send(page)
        if not guild_paginator.pages:
            await ctx.send("```None```")
        await ctx.send("Global sounds for this server:")
        for page in global_paginator.pages:
            await ctx.send(page)
        if not global_paginator.pages:
            await ctx.send("```None```")

    @commands.command(aliases=["setvoice"])
    async def myvoice(self, ctx, voice: str = None):
        """
        Changes your TTS voice.
        Type `[p]listvoices` to view all possible voices.
        If no voice is provided, it will show your current voice.
        """

        current_voice = await self.config.user(ctx.author).voice()

        if voice is None:
            await ctx.send(f"Your current voice is **{current_voice}**")
            return
        voice = voice.lower()
        voices = TTSAPI.voices
        if voice in voices:
            await self.config.user(ctx.author).voice.set(voice)
            await ctx.send(f"Your new TTS voice is: **{voice}**")
        else:
            await ctx.send(
                f"Sorry, that's not a valid voice. You can view voices with the `{ctx.clean_prefix}listvoices` command."
            )

    @commands.command(aliases=["setspeed"])
    async def myspeed(self, ctx, speed: int = None):
        """
        Changes your TTS speed.
        If no speed is provided, it will show your current speed.
        The speed range is 0-10 (higher is faster, 5 is normal.)
        """

        current_speed = await self.config.user(ctx.author).voice()

        if speed is None:
            await ctx.send(f"Your current speed is **{current_speed}**")
            return

        speeds = TTSAPI.speeds

        if speed in speeds:
            await self.config.user(ctx.author).speed.set(speeds[speed])
            await ctx.send(f"Your new TTS speed is: **{speed}**")
        else:
            await ctx.send(
                "Sorry, that's not a valid speed. The speed range is 0-10 higher is faster, 5 is normal.)"
            )

    @commands.command()
    async def listvoices(self, ctx, lang="en"):
        """
        Lists all the TTS voices.
        """
        voices = TTSAPI.voices
        embed = discord.Embed(
            title="Available TTS Voices", color=await ctx.embed_colour()
        )
        for voice in voices:
            value = voices[voice]["gender"] + " - " + voices[voice]["language"]
            embed.add_field(name=voice, value=value, inline=False)
        await ctx.send(embed=embed)

    @commands.group()
    @commands.guild_only()
    @commands.admin()
    async def ttschannel(self, ctx):
        """
        Configures automatic TTS channels.
        """

    @ttschannel.command()
    async def add(self, ctx, channel: discord.TextChannel):
        """Add a channel for automatic TTS."""
        channel_list = await self.config.guild(ctx.guild).channels()
        if channel.id not in channel_list:
            channel_list.append(channel.id)
            await self.config.guild(ctx.guild).channels.set(channel_list)
            await ctx.send(f"Okay, I've added {channel.mention} to the config.")
        else:
            await ctx.send(
                f"{channel.mention} was already in the config, did you mean to remove it?"
            )

    @ttschannel.command()
    async def remove(self, ctx, channel: discord.TextChannel):
        """
        Removes a channel for automatic TTS.
        """
        channel_list = await self.config.guild(ctx.guild).channels()
        if channel.id in channel_list:
            channel_list.remove(channel.id)
            await self.config.guild(ctx.guild).channels.set(channel_list)
            await ctx.send(f"Okay, I've removed {channel.mention} from the config.")
        else:
            await ctx.send(
                f"I couldn't find {channel.mention} in the config, did you mean to add it?"
            )

    @ttschannel.command()
    async def clear(self, ctx):
        """
        Removes all the channels for automatic TTS.
        """
        channel_list = await self.config.guild(ctx.guild).channels()
        if not channel_list:
            await ctx.send("There's no channels in the config.")
        else:
            await self.config.guild(ctx.guild).channels.set([])
            await ctx.send("Ok, I've removed them all.")

    @ttschannel.command()
    async def list(self, ctx):
        """
        Shows all the channels for automatic TTS.
        """
        channel_list = await self.config.guild(ctx.guild).channels()
        if not channel_list:
            await ctx.send("There's no channels in the config.")
        else:
            lolidk = ""
            for obj in channel_list:
                lolidk = lolidk + "\n <#" + str(obj) + "> - " + str(obj)
            embed = discord.Embed(
                title="Automatic TTS Channels",
                color=await ctx.embed_colour(),
                description=lolidk,
            )
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        if not message.channel.permissions_for(message.guild.me).send_messages:
            return
        if await self.bot.allowed_by_whitelist_blacklist(who=message.author) is False:
            return

        channel_list = await self.config.guild(message.guild).channels()
        if not channel_list:
            return
        if message.channel.id not in channel_list:
            return

        if not message.author.voice or not message.author.voice.channel:
            await message.channel.send("You are not connected to a voice channel.")
            return

        audio_file = os.path.join(
            tempfile.gettempdir(),
            "tts/",
            "".join(random.choice("0123456789ABCDEF") for i in range(15)) + ".wav",
        )
        author_voice = await self.config.user(message.author).voice()
        author_speed = await self.config.user(message.author).speed()

        encoded_string = message.content.encode("ascii", "ignore")
        decoded_string = encoded_string.decode()

        if not decoded_string:
            await message.channel.send("That's not a valid message, sorry.")
            return

        if len(decoded_string) > 1000:
            await message.channel.send(
                "Sorry, I only allow messages with 1000 characters or below to be spoken."
            )
            return

        await TTSAPI.get_audio(
            self, decoded_string, author_voice, author_speed, audio_file
        )
        try:
            audio_data = pydub.AudioSegment.from_file(audio_file)
        except pydub.CouldntDecodeError:
            await message.channel.send(
                "Uh oh, an error occured. Please try again later."
            )
            return
        silence = pydub.AudioSegment.silent(duration=500)
        padded_audio = silence + audio_data
        padded_audio.export(audio_file)
        try:
            await self._play_sfx(message.author.voice.channel, audio_file, True)
        except Exception:
            await message.channel.send(
                "Lavalink doesn't seem to be ready, please try again later."
            )
            return

    async def _play_sfx(self, vc, filepath, is_tts=False):
        player = await lavalink.connect(vc)
        tracks = await player.load_tracks(query=filepath)
        track = tracks.tracks[0]

        if player.current is None:
            player.queue.append(track)
            self.current_sfx = (track, is_tts)
            await player.play()
            return

        if self.current_sfx is not None:
            player.queue.insert(0, track)
            await player.skip()
            if self.current_sfx[1]:
                os.remove(self.current_sfx[0].uri)
            self.current_sfx = (track, is_tts)
            return

        self.last_track_info = (player.current, player.position)
        self.current_sfx = (track, is_tts)
        player.queue.insert(0, track)
        player.queue.insert(1, player.current)
        await player.skip()

    async def ll_check(self, player, event, reason):
        if self.current_sfx is None and self.last_track_info is None:
            return

        if (
            event == lavalink.LavalinkEvents.TRACK_EXCEPTION
            and self.current_sfx is not None
        ):
            if self.current_sfx[1]:
                os.remove(self.current_sfx[0].uri)
            self.current_sfx = None
            return

        if (
            event == lavalink.LavalinkEvents.TRACK_STUCK
            and self.current_sfx is not None
        ):
            if self.current_sfx[1]:
                os.remove(self.current_sfx[0].uri)
            self.current_sfx = None
            await player.skip()
            return

        if (
            event == lavalink.LavalinkEvents.TRACK_END
            and player.current is None
            and self.current_sfx is not None
        ):
            if self.current_sfx[1]:
                os.remove(self.current_sfx[0].uri)
            self.current_sfx = None
            return

        if (
            event == lavalink.LavalinkEvents.TRACK_END
            and self.last_track_info is not None
            and player.current.track_identifier
            == self.last_track_info[0].track_identifier
        ):
            print(str(self.last_track_info[0].uri))
            if self.current_sfx[1]:
                os.remove(self.current_sfx[0].uri)
            self.current_sfx = None
            await player.pause()
            await player.seek(self.last_track_info[1])
            await player.pause(False)
            self.last_track_info = None
