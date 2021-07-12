import random

import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import pagify


class Penis(commands.Cog):
    """Penis related commands."""

    @commands.command(aliases=["pp"])
    async def penis(self, ctx, *users: discord.Member):
        """
        Detects user's penis length

        This is 100% accurate.
        Enter multiple users for an accurate comparison!
        """
        if not users:
            users = (ctx.author,)

        dongs = {}
        msg = ""
        state = random.getstate()
        king_dong = 749112024633704481

        for user in users:
            random.seed(user.id)

            if user.id == king_dong:
                dong_size = 40
            else:
                dong_size = random.randint(0, 30)

            dongs[user] = "8{}D".format("=" * dong_size)

        random.setstate(state)
        dongs = sorted(dongs.items(), key=lambda x: x[1])

        for user, dong in dongs:
            msg += "**{}'s size:**\n{}\n".format(user.display_name, dong)

        for page in pagify(msg):
            await ctx.send(page)
