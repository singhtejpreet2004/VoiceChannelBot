import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

load_dotenv()

intents = discord.Intents.default()
intents.members = True  # Needed to invite members and manage permissions
intents.guilds = True
intents.voice_states = True
intents.messages = True  # Needed for message-related intents
intents.dm_messages = True  # Necessary for sending DMs

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    try:
        synced = await bot.tree.sync()  # Syncing slash commands
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.tree.command(name="create_channel", description="Create a temporary voice channel and invite members")
async def create_channel(interaction: discord.Interaction, name: str, members: discord.Member = None):
    guild = interaction.guild

    # Create the voice channel
    temp_channel = await guild.create_voice_channel(name)
    await interaction.response.send_message(f'Voice channel "{name}" created!', ephemeral=False)

    invited_members = []

    # Check if members are mentioned and set permissions
    if members:
        if isinstance(members, list):  # If multiple members are provided
            for member in members:
                await temp_channel.set_permissions(guild.default_role, connect=False)  # Default is no one can connect
                await temp_channel.set_permissions(member, connect=True)  # Invite specific members
                invited_members.append(member)
                await interaction.followup.send(f'{member.mention} has been invited to "{name}".', ephemeral=False)
        else:  # Single member case
            await temp_channel.set_permissions(guild.default_role, connect=False)  # Default is no one can connect
            await temp_channel.set_permissions(members, connect=True)  # Invite specific members
            invited_members.append(members)
            await interaction.followup.send(f'{members.mention} has been invited to "{name}".', ephemeral=False)

        # Notify invited members via DM
        for member in invited_members:
            await send_initial_notification(member, temp_channel)
            await send_continuous_notifications(temp_channel, member, guild)

    # Generate an instant invite link
    invite = await temp_channel.create_invite(max_uses=1, unique=True)
    print(f"Invite link for channel '{temp_channel.name}': {invite}")

    # Send the invite link to the members via DM
    for member in invited_members:
        await member.send(f"🎉 Join the voice channel '{temp_channel.name}' here: {invite}")

    # Start tracking inactivity and delete the channel after 5 minutes
    await check_for_inactivity(temp_channel)

async def send_initial_notification(member, channel):
    try:
        await member.send(f"🎉 A new voice channel named '{channel.name}' has been created just for you! Join us there!")
        print(f"Initial notification sent to {member.name}.")
    except discord.Forbidden:
        print(f"Could not send DM to {member.name} (DMs disabled).")
    except Exception as e:
        print(f"Error sending DM to {member.name}: {e}")

async def send_continuous_notifications(channel, member, guild):
    notification_interval = 60  # Send notification every 60 seconds

    while True:
        if member in channel.members:
            print(f"{member.name} has joined the voice channel. Stopping notifications.")
            break

        try:
            await member.send(f"🔔 Don't forget to join the voice channel '{channel.name}' in {guild.name}!")
            print(f"Notification sent to {member.name}.")
        except discord.Forbidden:
            print(f"Could not send DM to {member.name} (DMs disabled).")
            break
        except Exception as e:
            print(f"Error sending DM to {member.name}: {e}")

        await asyncio.sleep(notification_interval)

async def check_for_inactivity(channel):
    inactivity_period = 300  # 5 minutes (in seconds)
    
    while True:
        await asyncio.sleep(inactivity_period)
        
        if len(channel.members) == 0:
            await channel.delete()
            print(f"Deleted inactive channel: {channel.name}")
            break

@bot.tree.command(name="make_public", description="Make a voice channel public for everyone to join")
async def make_public(interaction: discord.Interaction, channel: discord.VoiceChannel):
    guild = interaction.guild
    await channel.set_permissions(guild.default_role, connect=True)  # Allow everyone to connect
    await interaction.response.send_message(f'Voice channel "{channel.name}" is now public!', ephemeral=False)

@bot.tree.command(name="make_private", description="Make a voice channel private to only selected members")
async def make_private(interaction: discord.Interaction, channel: discord.VoiceChannel):
    guild = interaction.guild
    await channel.set_permissions(guild.default_role, connect=False)  # Deny access to everyone by default
    await interaction.response.send_message(f'Voice channel "{channel.name}" is now private!', ephemeral=False)

@bot.tree.command(name="delete_channel", description="Delete a voice channel")
async def delete_channel(interaction: discord.Interaction, channel: discord.VoiceChannel):
    if channel:
        try:
            await channel.delete()
            await interaction.response.send_message(f'Voice channel "{channel.name}" has been deleted!', ephemeral=False)
            print(f"Deleted channel: {channel.name} by {interaction.user.name}.")  # Debugging output
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to delete this channel.", ephemeral=True)
            print(f"Failed to delete channel: {channel.name}. Permission denied.")
        except discord.HTTPException:
            await interaction.response.send_message("Failed to delete the channel due to a server error.", ephemeral=True)
            print(f"Failed to delete channel: {channel.name}. HTTP error occurred.")
    else:
        await interaction.response.send_message("Please specify a valid voice channel to delete.", ephemeral=True)

@bot.tree.command(name="test_dm", description="Test sending a DM")
async def test_dm(interaction: discord.Interaction):
    try:
        await interaction.user.send("This is a test DM from your bot!")
        await interaction.response.send_message("Test DM sent!", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I can't send you a DM. Please check your DM settings.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

bot.run('DISCORD_TOKEN')