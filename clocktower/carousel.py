"""The experimental characters (the official data's "carousel" edition) and the jinxes between built characters, on
the script-independent core (characters.py, state.py, game.py), for custom scripts.

Each entry follows the almanac's How to Run (the wiki's, for characters the printed almanac predates). Where the rules
leave a question open, a comment says which reading the entry takes, and why (docs/carousel-rulings.md lists them for
review, numbered across batches).

Jinxes. An official jinx is in effect when both its characters are on the script (`Script.jinxed`), in play or not;
the code a jinx changes asks that and then checks the situation the jinx describes. A jinx between two characters of
the base scripts changes their own entries (in characters.py, bmr.py or snv.py), guarded so that Trouble Brewing, Bad
Moon Rising and Sects & Violets, which hold no jinx, play as before. Every implemented jinx is declared below with
`jinx(a, b, where)`; tests/test_carousel.py checks that each official jinx between two built characters is.
"""
from __future__ import annotations

from . import snv
from .characters import jinx, kind


def ability(name):
    """The official ability text."""
    from . import official
    return official.role(name)['ability']


def townsfolk(q):
    return kind(q.character) == 'Townsfolk'


# Later entries share Sects & Violets' helpers, through the module (snv may be the module being imported first, so
# its names are not bound yet when this one loads): who has or believes they have an ability (snv.believers,
# snv.holders), information through the judge (snv.info, snv.learn, snv.when), once-per-game abilities per player
# (snv.used, snv.use, snv.fresh), the abnormal record for the Mathematician (snv.failed), the final night
# (snv.final_night).
BASE = snv


# ---- Batch 0: the jinxes between characters of the base scripts (docs/carousel-rulings.md, 5-11) ---------------

jinx('Mastermind', 'Vigormortis', 'snv.Vigormortis.dies')
jinx('Mathematician', 'Chambermaid', 'bmr.chambermaid_choice')
jinx('Mathematician', 'Drunk', 'game.Game.note_information; characters.Drunk; characters.Slayer.act_publicly')
jinx('Mathematician', 'Lunatic', 'snv.lunatic_attacked_elsewhere')
jinx('Pit-Hag', 'Goon', 'snv.PitHag.resolve_night; bmr.Goon.chosen')
jinx('Recluse', 'Sage', 'snv.sage_choice')
jinx('Scarlet Woman', 'Fang Gu', 'characters.ScarletWoman.on_death')
