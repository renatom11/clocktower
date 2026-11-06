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
