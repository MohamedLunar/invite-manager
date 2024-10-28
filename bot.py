import nextcord
from nextcord.ext import commands
from collections import defaultdict
import json
import os
from dotenv import load_dotenv

load_dotenv()

intents = nextcord.Intents.default()
intents.invites = True
intents.members = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents, help_command=None)

TOKEN = os.getenv("TOKEN")  # Replace with your bot's token

# Dictionary to track invites and channels
invite_tracker = defaultdict(lambda: defaultdict(int))

# Path to the JSON file to store invite channels
INVITES_CHANNEL_FILE = 'invites_channel.json'

# Load invites_channel from JSON file if it exists
if os.path.exists(INVITES_CHANNEL_FILE):
    with open(INVITES_CHANNEL_FILE, 'r') as f:
        invites_channel = json.load(f)
else:
    invites_channel = {}

@bot.event
async def on_ready():
    activity = nextcord.Game(name='my game')
    await bot.change_presence(status=nextcord.Status.idle, activity=activity)
    print(f'Logged in as {bot.user}')
    for guild in bot.guilds:
        invites = await guild.invites()
        for invite in invites:
            invite_tracker[guild.id][invite.code] = invite.uses

@bot.event
async def on_invite_create(invite):
    invite_tracker[invite.guild.id][invite.code] = invite.uses

@bot.event
async def on_invite_delete(invite):
    del invite_tracker[invite.guild.id][invite.code]

@bot.event
async def on_member_join(member):
    invites_before = invite_tracker[member.guild.id]
    invites_now = await member.guild.invites()

    for invite in invites_now:
        if invite.code in invites_before:
            uses = invite.uses - invites_before[invite.code]
            if uses > 0:
                channel_id = invites_channel.get(str(member.guild.id))
                if channel_id:
                    channel = bot.get_channel(int(channel_id))
                    if channel:
                        inviter = invite.inviter
                        # Calculate total invites by this inviter
                        total_invites = sum(i.uses for i in invites_now if i.inviter == inviter)
                        
                        # Send the message with the new format
                        await channel.send(f'➕ {member.mention} has been invited by **__{inviter.name}__** '
                                           f'and has now **__{total_invites}__** invites!')
                
                # Update the invite tracker for this invite
                invite_tracker[member.guild.id][invite.code] = invite.uses

# Helper function to save invites_channel to JSON file
def save_invites_channel():
    with open(INVITES_CHANNEL_FILE, 'w') as f:
        json.dump(invites_channel, f)

@bot.slash_command(name="set-invites-channel", description="Set the channel for invite tracking")
async def set_invites_channel(interaction: nextcord.Interaction, channel: nextcord.TextChannel):
    invites_channel[str(interaction.guild.id)] = str(channel.id)
    save_invites_channel()
    await interaction.response.send_message(f'Invite tracking channel set to {channel.mention}!')

@bot.slash_command(name="reset-invites-channel", description="Reset the invite tracking channel")
async def reset_invites_channel(interaction: nextcord.Interaction):
    if str(interaction.guild.id) in invites_channel:
        del invites_channel[str(interaction.guild.id)]
        save_invites_channel()
        await interaction.response.send_message("Invite tracking channel has been reset!")
    else:
        await interaction.response.send_message("No invite tracking channel is set.")

@bot.slash_command(name="invites", description="Check how many members a user has invited")
async def invites(interaction: nextcord.Interaction, member: nextcord.Member = None):
    member = member or interaction.user
    invites = await interaction.guild.invites()
    total_uses = sum(invite.uses for invite in invites if invite.inviter == member)
    await interaction.response.send_message(f'{member.mention} has invited {total_uses} members!')

# New $i command for showing invite count
@bot.command(name="i")
async def i(ctx, member: nextcord.Member = None):
    # If no member is mentioned, use the command author (ctx.author)
    member = member or ctx.author
    invites = await ctx.guild.invites()
    
    # Count how many invites the user has
    total_uses = sum(invite.uses for invite in invites if invite.inviter == member)
    
    if member == ctx.author:
        # Personalized message if the user didn't mention anyone
        await ctx.send(f'{ctx.author.mention}, you have **__{total_uses}__** invites!')
    else:
        # Mention the target user and show their invites
        await ctx.send(f'{member.mention} has **__{total_uses}__** invites!')
        
# Slash command /invited
@bot.slash_command(name="invited", description="Display the list of members a user has invited")
async def invited(interaction: nextcord.Interaction, member: nextcord.Member = None):
    member = member or interaction.user
    invites = await interaction.guild.invites()
    
    invited_members = [invite.inviter.mention for invite in invites if invite.inviter == member]
    
    if invited_members:
        invite_list = "\n".join(invited_members)
        description = f"Invited members:\n{invite_list}"
    else:
        description = "No members invited yet."

    embed = nextcord.Embed(
        title=f"{member.mention}'s Invites",
        description=description,
        color=nextcord.Color.blue()
    )
    embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.avatar.url)

    await interaction.response.send_message(embed=embed)

@bot.command(name="help")
async def help(ctx):
    description = (
        "**Slash Commands**\n"
        "`/set-invites-channel` - Set invite tracking channel\n"
        "`/reset-invites-channel` - Reset invites tracking channel\n"
        "`/invites` - Check another user's invites\n"
        "**Prefix Commands**\n"
        "`$i` - Check how many invites a user has"
    )
    
    embed = nextcord.Embed(
        title="Bot Commands",
        description=description,
        color=nextcord.Color.green()
    )
    embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)

    await ctx.send(embed=embed)
    

bot.run(TOKEN)
