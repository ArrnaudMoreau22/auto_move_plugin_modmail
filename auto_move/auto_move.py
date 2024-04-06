import discord
from discord.ext import commands
from core import checks
from core.models import PermissionLevel
import asyncio

class AutoMove(commands.Cog):
    """Automatically moves discussion threads based on activity."""

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.plugin_db.get_partition(self)
        bot.loop.create_task(self.ensure_config_keys())

    async def ensure_config_keys(self):
        """Ensures that all necessary configuration keys exist."""
        default_keys = {
            "waiting_user_message_category_id": None,
            "waiting_staff_message_category_id": None,
            "closing_category_id": None,
            "recruitment_id": None,
        }
        for key, default_value in default_keys.items():
            if await self.get_config(key) is None:
                await self.set_config(key, default_value)

    async def get_config(self, key):
        """Retrieves a specific configuration."""
        config = await self.db.find_one({"_id": key})
        return config['value'] if config else None

    async def set_config(self, key, value):
        """Updates a specific configuration."""
        await self.db.find_one_and_update({"_id": key}, {"$set": {"value": value}}, upsert=True)

    async def get_global_config(self, key):
        """Retrieves a specific configuration from the global configuration."""
        return self.bot.config.get(key)

    @commands.Cog.listener()
    async def on_ready(self):
        """Triggers when the bot is ready."""
        await self.ensure_config_keys()

    @commands.command(name='initinfo', help='Displays commands for initializing ID variables.')
    @checks.has_permissions(PermissionLevel.MODERATOR)
    async def display_init_info(self, ctx):
        """Displays initialization information to configure necessary IDs."""
        embed = discord.Embed(title="Initialization of IDs",
                              description="Use the following commands to configure necessary IDs.",
                              color=discord.Color.blue())
        embed.add_field(name="Set User Message Category ID", value="`?setwaitingusermessagecategory [ID]`", inline=False)
        embed.add_field(name="Set Staff Message Category ID", value="`?setwaitingstaffmessagecategory [ID]`", inline=False)
        embed.add_field(name="Set Closing Category ID", value="`?setclosingcategory [ID]`", inline=False)
        embed.set_field(3, name="Set Recruitment Category ID", value="`?setrecruitmentcategory [ID]`", inline=False)
        embed.set_footer(text="Replace [ID] with the actual ID of each category or role.")

        await ctx.send(embed=embed)

    async def move_channel(self, channel, category_id):
        """Moves a channel to a specified category."""
        category_id = int(category_id)
        target_category = self.bot.get_channel(category_id)
        if target_category and channel.category_id != category_id:
            try:
                await channel.edit(category=target_category)
            except Exception as e:
                print(f"Failed to move the channel: {e}")

    @commands.command(name='movetoclosingcategory')
    @checks.has_permissions(PermissionLevel.MODERATOR)
    async def move_to_closing_category(self, ctx):
        """Moves the current thread to the closing category."""
        await asyncio.sleep(3)
        thread = await self.bot.threads.find(channel=ctx.channel)
        if thread:
            category_id = await self.get_config("closing_category_id")
            
            if category_id is not None:
                await self.move_channel(thread.channel, category_id)
            else:
                await ctx.send('The closing category ID is not configured.')
        else:
            await ctx.send('This command must be used in a thread channel.')


    @commands.command(name='setwaitingusermessagecategory')
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def set_waiting_user_message_category(self, ctx, category_id: int):
        """Sets the ID for the category for user messages awaiting response."""
        await self.set_config('waiting_user_message_category_id', str(category_id))
        await ctx.send(f'User message waiting category ID updated successfully: <#{category_id}>.')

    @commands.command(name='setwaitingstaffmessagecategory')
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def set_waiting_staff_message_category(self, ctx, category_id: int):
        """Sets the ID for the category for staff messages awaiting response."""
        await self.set_config('waiting_staff_message_category_id', str(category_id))
        await ctx.send(f'Staff message waiting category ID updated successfully: <#{category_id}>.')

    @commands.command(name='setclosingcategory')
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def set_closing_category(self, ctx, category_id: int):
        """Sets the ID for the category for closing threads."""
        await self.set_config('closing_category_id', str(category_id))
        await ctx.send(f'Closing category ID updated successfully: <#{category_id}>.')

    @commands.command(name='setrecruitmentcategory')
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def set_recruitment_category(self, ctx, category_id: int):
        """Sets the ID for the category for recruitment threads."""
        await self.set_config('recruitment_id', str(category_id))
        await ctx.send(f'Recruitment category ID updated successfully: <#{category_id}>.')

    async def has_mod_replied(self, thread):
        mod_color = await self.get_global_config("mod_color")
        async for message in thread.channel.history():
            for embed in message.embeds:
                if embed.color.value == mod_color:
                    return True
        return False
    
    @commands.Cog.listener()
    async def on_thread_reply(self, thread, from_mod, message, anonymous, plain):
        mod_has_replied = await self.has_mod_replied(thread)
        recruitment_category_id = await self.get_config("recruitment_id")
        category_id = None
        if recruitment_category_id and thread.channel.category_id == int(recruitment_category_id):
            return

        if from_mod:
                category_id = await self.get_config("waiting_user_message_category_id")
        else:
            if mod_has_replied:
                category_id = await self.get_config("waiting_staff_message_category_id")
            
        if category_id:
            await self.move_channel(thread.channel, category_id)

async def setup(bot):
    """Necessary function to load the Cog."""
    await bot.add_cog(AutoMove(bot))
