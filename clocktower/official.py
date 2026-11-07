"""The Pandemonium Institute's character data (clocktower/data/official/, see SOURCE.md there).

Every released character's official id, name, type and edition, the universal night order, reminder tokens and
jinxes. A script's night order is the universal one filtered to the script's characters, which is how the
official script tool builds its night sheets.
"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / 'data' / 'official'
# Steps of the night sheet that are not characters
MARKERS = {'dusk': 'Dusk', 'dawn': 'Dawn', 'minioninfo': 'Minion info', 'demoninfo': 'Demon info'}
TYPES = {'townsfolk': 'Townsfolk', 'outsider': 'Outsider', 'minion': 'Minion', 'demon': 'Demon',
         'traveller': 'Traveller', 'fabled': 'Fabled', 'loric': 'Loric'}


def _load(name):
    return json.loads((DATA / name).read_text())


@lru_cache(maxsize=None)
def roles():
    """{official id: role} for every released character."""
    return {r['id']: r for r in _load('roles.json')}


@lru_cache(maxsize=None)
def ids():
    """{character name: official id}."""
    return {r['name']: i for i, r in roles().items()}


def role(name):
    """The official record of a character, by name (e.g. 'Fortune Teller')."""
    return roles()[ids()[name]]


def kind(name):
    """'Townsfolk', 'Outsider', 'Minion', 'Demon', 'Traveller', 'Fabled' or 'Loric'."""
    return TYPES[role(name)['team']]


@lru_cache(maxsize=None)
def nightsheet():
    return _load('nightsheet.json')


def night_order(names, first):
    """The characters among `names` that have a step on the first night (first=True) or on other nights, in the
    official order."""
    wanted = {ids()[n] for n in names}
    steps = nightsheet()['firstNight' if first else 'otherNight']
    return [roles()[i]['name'] for i in steps if i in wanted]


SCRIPTS = Path(__file__).resolve().parent / 'data' / 'scripts'


PLAYER_TYPES = ('Townsfolk', 'Outsider', 'Minion', 'Demon')


def official_id(entry_id):
    """The official id a script entry's id names, or None: ids are matched ignoring case and anything not a letter or
    digit, so 'fortune_teller', 'Fortune Teller', 'lil-monsta' and 'fortuneteller' are the same character."""
    key = ''.join(ch for ch in str(entry_id).lower() if ch.isalnum())
    return key if key in roles() else None


def script_entries(source):
    """A script in the official script tool's JSON format: a built-in script by id ('tb', 'bmr') or a path to a JSON
    file. Returns {'name', 'meta', 'entries'}, each entry {'id', 'name', 'type', 'official'} in the file's order: an
    official character by its official record (an entry naming one is that character, whatever else it holds), or a
    homebrew one the file defines itself (an object with a name and a team: `official` False). An id that is neither
    raises ValueError."""
    path = Path(source) if str(source).endswith('.json') else SCRIPTS / f'{source}.json'
    raw = json.loads(path.read_text())
    meta = next((e for e in raw if isinstance(e, dict) and e.get('id') == '_meta'), {})
    entries, unknown = [], []
    for e in raw:
        if e is meta:
            continue
        i = e if isinstance(e, str) else e.get('id')
        oid = official_id(i)
        if oid:
            r = roles()[oid]
            entries.append({'id': oid, 'name': r['name'], 'type': TYPES[r['team']], 'official': True})
        elif isinstance(e, dict) and e.get('name') and e.get('team') in TYPES:
            entries.append({'id': i, 'name': e['name'], 'type': TYPES[e['team']], 'official': False})
        else:
            unknown.append(i)
    if unknown:
        raise ValueError(f'{path.name}: characters not in the official data: {unknown}')
    return {'name': meta.get('name', path.stem), 'meta': meta, 'entries': entries}


def script(source):
    """(name, [character names]) of a script (see script_entries): its official characters of the four player types,
    in the file's order (Travellers, Fabled, Loric and homebrew entries left out)."""
    s = script_entries(source)
    return s['name'], [e['name'] for e in s['entries'] if e['official'] and e['type'] in PLAYER_TYPES]


@lru_cache(maxsize=None)
def jinxes():
    """{(name, name): ruling} for every official jinx, both orders."""
    out = {}
    for entry in _load('jinxes.json'):
        a = roles()[entry['id']]['name'] if entry['id'] in roles() else entry['id']
        for j in entry.get('jinx', []):
            b = roles()[j['id']]['name'] if j['id'] in roles() else j['id']
            out[(a, b)] = out[(b, a)] = j['reason']
    return out
