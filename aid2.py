import requests

URL = 'https://api.aidungeon.io'

TOKEN = None
CONFIG = None
MAX_RERUN = 5

def init_session(cred_file_path):
    global TOKEN
    data = {}
    with open(cred_file_path) as f:
        data['email'] = f.readline().strip()
        data['password'] = f.readline().strip()
    r = requests.post(f'{URL}/users', data)
    if not r.ok:
        print('/users', r.status_code, r.reason)
        return None
    try:
        TOKEN = r.json()['accessToken']
    except (ValueError, KeyError):
        print(f'{URL}/users: invalid response: {r.content}')


def read_config():
    global CONFIG
    r = requests.get(f'{URL}/sessions/*/config', headers={'X-Access-Token': TOKEN})
    if not r.ok:
        print('/sessions/*/config', r.status_code, r.reason)
    else:
        try:
            CONFIG = r.json()
        except ValueError:
            print(f'{URL}/sessions/*/config: invalid response: {r.content}')


def ready():
    return TOKEN is not None


def init_story(mode, character, name):
    data = {
        'storyMode': mode,
        'characterType': character,
        'name': name,
        'customPrompt': None,
        'promptId': None
    }
    r = None
    times = 0
    while (r is None or r.status_code >= 500) and times < MAX_RERUN:
        r = requests.post(f'{URL}/sessions', data, headers={'X-Access-Token': TOKEN})
        times += 1
    if not r.ok:
        print('/sessions', r.status_code, r.reason)
        return None, None
    else:
        try:
            r = r.json()
            return r['id'], r['story'][0]['value']
        except (ValueError, KeyError, IndexError):
            print(f'{URL}/sessions: invalid response: {r.content}')
            return None, None


def continue_story(story_id, text):
    data = {
        'text': text
    }
    r = None
    times = 0
    while (r is None or r.status_code >= 500) and times < MAX_RERUN:
        r = requests.post(f'{URL}/sessions/{story_id}/inputs', data, headers={'X-Access-Token': TOKEN})
        times += 1
    if not r.ok:
        print(f'/sessions/{story_id}/inputs', r.status_code, r.reason)
        return None, None
    else:
        try:
            r = r.json()
            return r[-1]['value']
        except (ValueError, KeyError, IndexError):
            print(f'{URL}/sessions/{story_id}/inputs: {r.content}')
            return None, None


def command_line():
    init_session('aid2_cred.txt')
    read_config()
    if TOKEN is None or CONFIG is None:
        print('init failed')
        exit(1)

    modes = list(CONFIG['modes'].keys())
    print('Pick a setting...')
    for i in range(len(modes)):
        print(f"{i + 1}) {modes[i]}")
    s = int(input('> '))
    mode = modes[s-1]

    characters = list(CONFIG['modes'][mode]['characters'].keys())
    print('Select a character...')
    for i in range(len(characters)):
        print(f"{i + 1}) {characters[i]}")
    s = int(input('> '))
    character = characters[s-1]

    print('Enter your character name...')
    name = input('> ')

    story_id, story = init_story(mode, character, name)

    while story is not None:
        print(story)
        user_input = input('> ')
        story = continue_story(story_id, user_input)


if __name__ == '__main__':
    # running as script
    command_line()
