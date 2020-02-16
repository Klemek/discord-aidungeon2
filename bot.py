import os
import traceback
import discord
import aid2
import re
from datetime import datetime
from dotenv import load_dotenv

VERSION = "1.0"
t0 = datetime.now()

# Loading token
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

client = discord.Client()

STORIES = {}

MODES = {
    'fantasy': ['noble', 'knight', 'squire', 'ranger', 'peasant', 'rogue'],
    'mystery': ['patient', 'detective', 'spy'],
    'apocalyptic': ['soldier', 'scavenger', 'survivor', 'courier'],
    'zombies': ['soldier', 'survivor', 'scientist']
}

STATUS_ASKED = 'asked'
STATUS_MODE = 'mode'
STATUS_CHARACTER = 'character'
STATUS_NAME = 'name'
STATUS_STORY = 'story'


def debug(message, txt):
    """
    Print a log with the context of the current event

    :param message: message that triggered the event
    :type message: discord.Message
    :param txt: text of the log
    :type txt: str
    """
    print(f"{message.guild} > #{message.channel}: {txt}")


@client.event
async def on_ready():
    """
    Called when client is connected
    """
    # Change status
    await client.change_presence(
        activity=discord.Game(f"v{VERSION}"),
        status=discord.Status.online
    )
    # Debug connected guilds
    print(f'{client.user} v{VERSION} has connected to Discord\nto the following guilds:')
    for guild in client.guilds:
        print(f'- {guild.name}(id: {guild.id})')


@client.event
async def on_message(message):
    """
    Called when a message is sent to any channel on any guild

    :param message: message sent
    :type message: discord.Message
    """

    # Ignore self messages
    if message.author == client.user:
        return

    mid = f'{message.guild.id}/{message.channel.id}/{message.author.id}'

    if mid in STORIES and STORIES[mid]['status'] != STATUS_STORY:
        # story creation mode
        await new_story(mid, message)

    if client.user in message.mentions:
        message.content = re.sub(r'<@[^>]+>', '', message.content).strip()
        debug(message, f"'{message.content}'")

        # Check if bot can respond on current channel or DM user
        permissions = message.channel.permissions_for(message.guild.me)
        if not permissions.send_messages:
            debug(message, f"missing 'send_messages' permission")
            await message.author.create_dm()
            await message.author.dm_channel.send(
                f"Hi, this bot doesn\'t have the permission to send a message to"
                f" #{message.channel} in server '{message.guild}'")
            return

        if message.content.lower().startswith('new story'):
            await new_story(mid, message)
            return

        if mid not in STORIES or STORIES[mid]['status'] != STATUS_STORY:
            response = await message.channel.send(f'{message.author.mention}\n'
                                                  f'You don\'t have any stories right now, do you want to create one ?\n'
                                                  f'(yes/no)')
            STORIES[mid] = {
                'id': None,
                'status': STATUS_ASKED,
                'response': response
            }
            return

        story = STORIES[mid]

        async with message.channel.typing():
            result = aid2.continue_story(story['id'], message.content)
            if result is not None:
                await message.channel.send(f'{message.author.mention}:\n```{result}```')
            else:
                await message.channel.send(f'{message.author.mention}: Error during request')
                del STORIES[mid]


async def new_story(mid, message):
    if mid not in STORIES:
        STORIES[mid] = {
            'id': None,
            'status': STATUS_ASKED,
            'response': await message.channel.send(f'{message.author.mention}')
        }
    story = STORIES[mid]
    if story['status'] == STATUS_ASKED:
        if message.content.strip().lower() == 'yes' or message.content.strip().lower() == 'new story':
            modes_names = list(MODES.keys())
            await story['response'].edit(content=f'{message.author.mention}\n'
                                                 f'\n'
                                                 f'**Pick a setting...**\n' +
                                                 '\n'.join([f'{i+1}) {modes_names[i]}' for i in range(len(modes_names))]))
            story['status'] = STATUS_MODE
        else:
            await story['response'].edit(
                content=f'{message.author.mention} You can start a new story by typing "{client.user.mention} new story"')
            del STORIES[mid]
    elif story['status'] == STATUS_MODE:
        mode = message.content.lower().strip()
        try:
            mode_i = int(mode) - 1
            modes_names = list(MODES.keys())
            if 0 <= mode_i < len(modes_names):
                mode = modes_names[mode_i]
        except ValueError:
            pass
        if mode in MODES:
            story['mode'] = mode
            characters = MODES[mode]
            await story['response'].edit(content=f'{message.author.mention}\n'
                                                 f'Setting: *{mode}*\n'
                                                 f'\n'
                                                 f'**Select a character...**\n' +
                                                 '\n'.join(
                                                     [f'{i + 1}) {characters[i]}' for i in range(len(characters))]))
            story['status'] = STATUS_CHARACTER
    elif story['status'] == STATUS_CHARACTER:
        character = message.content.lower().strip()
        try:
            char_i = int(character) - 1
            characters = MODES[story['mode']]
            if 0 <= char_i < len(characters):
                character = characters[char_i]
        except ValueError:
            pass
        if character in MODES[story['mode']]:
            story['character'] = character
            await story['response'].edit(content=f'{message.author.mention}\n'
                                                 f'Setting: *{story["mode"]}*\n'
                                                 f'Character: *{character}*\n'
                                                 f'\n'
                                                 f'**Enter your character name...**')
            story['status'] = STATUS_NAME
    elif story['status'] == STATUS_NAME:
        story['name'] = message.content.strip()
        await story['response'].edit(content=f'{message.author.mention}\n'
                                             f'Setting: *{story["mode"]}*\n'
                                             f'Character: *{story["character"]}*\n'
                                             f'Name: *{story["name"]}*\n'
                                             f'\n'
                                             f'**Generating story...**')
        async with message.channel.typing():
            story_id, result = aid2.init_story(story['mode'], story['character'], story['name'])
            await story['response'].delete()
            if result is not None:
                story['id'] = story_id
                story['status'] = STATUS_STORY
                await message.channel.send(f'{message.author.mention}:\n```{result}```')
            else:
                await message.channel.send(f'{message.author.mention}: Error during request')
                del STORIES[mid]
    try:
        await message.delete()
    except:
        pass


print(f"Current PID: {os.getpid()}")

aid2.init_session('aid2_cred.txt')

if not aid2.ready():
    print('AID2 lib not ready')
    exit(1)

# Launch client and rerun on errors
while True:
    try:
        client.run(token)
        break  # clean kill
    except Exception as e:
        t = datetime.now()
        print(f"Exception raised at {t:%Y-%m-%d %H:%M} : {repr(e)}")
        fileName = f"error_{t:%Y-%m-%d_%H-%M-%S}.txt"
        if os.path.exists(fileName):
            print("Two many errors, killing")
            break
        with open(fileName, 'w') as f:
            f.write(f"Discord AI Dungeon 2 v{VERSION} started at {t0:%Y-%m-%d %H:%M}\r\n"
                    f"Exception raised at {t:%Y-%m-%d %H:%M}\r\n"
                    f"\r\n"
                    f"{traceback.format_exc()}")
