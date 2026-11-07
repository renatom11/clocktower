"""Batch 6 of the experimental characters, removable by design: Lil' Monsta, the Atheist, the Wizard, Legion and Riot,
the five the brief kept for a design with the owner (its batch 6 update brings them in on one condition: each can
always be taken out again).

So each is a section of its own below, between its markers, holding everything about it: its imports, its class, its
Storyteller's weights (added to state.POLICY here, under the Carousel heading's batch 6 entries, rather than written
into state.py), the jinxes it implements (declared here, and listed in JINXES for tests/test_carousel.py), its
registration in characters.CHARACTERS. Nothing outside this module names them. The core hooks a section uses do
nothing on a script without its character (most are generic: an attribute or a list on the Script that only these
characters set), and the generic ones several of them need were added before any of them (the deal hooks in state.py,
the rule sentences in prompts.py), so each character is one commit, and `git revert` of that commit removes it (its
section, its core hooks, its tests in tests/test_carousel_<id>.py, its rulings, its synthetic script and fingerprints)
without touching the others. Where a section reads another batch 6 character (a jinx between two of them), it asks
whether that character is built, so either can go.

As in carousel.py to carousel6.py (whose helpers and conventions this module shares): each entry follows the wiki's How
to Run, and where the rules leave a question open, a comment says which reading the entry takes, and why
(docs/carousel-rulings.md, batch 6, lists them for review, one subsection per character).
"""
from __future__ import annotations

from .characters import CHARACTERS

JINXES = []  # the official jinxes implemented here, as (a, b) pairs (tests/test_carousel.py checks them all)


def built(name):
    """Whether batch 6's character `name` is built (its section is here): a section that reads another asks this."""
    return name in CHARACTERS


def ability(name):
    """The official ability text."""
    from . import official
    return official.role(name)['ability']


async def ask_yes(game, p, n, text):
    """`p`'s yes or no, asked in `vote` (required: asked again, never made for them; a seat that never answers stops
    the game, as a failed seat does)."""
    from .llm import SeatFailed
    req = game.request('decide', text, n)
    for _ in range(game.REASKS + 1):
        a = await game.ask(p.name, req)
        if isinstance(a.get('vote'), bool):
            return a['vote']
        req = game.request('decide', '(Your answer was missing: set `vote` to true or false.) ' + text, n)
    raise SeatFailed(f'{p.name}: no answer to a required choice after {game.REASKS} reminders')


# ---- Lil' Monsta -------------------------------------------------------------------------------------------------

# ---- end of Lil' Monsta ------------------------------------------------------------------------------------------


# ---- Atheist -----------------------------------------------------------------------------------------------------

# ---- end of Atheist ----------------------------------------------------------------------------------------------


# ---- Wizard ------------------------------------------------------------------------------------------------------

# ---- end of Wizard -----------------------------------------------------------------------------------------------


# ---- Legion ------------------------------------------------------------------------------------------------------

# ---- end of Legion -----------------------------------------------------------------------------------------------


# ---- Riot --------------------------------------------------------------------------------------------------------

# ---- end of Riot -------------------------------------------------------------------------------------------------
