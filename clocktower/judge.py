"""The Storyteller judge: for decisions that need judgment, the judge listens and ranks, the code decides.

The scripted Storyteller (state.POLICY) picks among every legal value of a Choice by fixed weights, and so cannot
"listen to the bluffs of the evil players, and support those bluffs wherever possible" (rulebook, Drunkenness and
Poisoning), nor weigh how the game is going. A judge follows the game as a skilled Storyteller does and ranks the
legal values. The code then picks from the ranking with fixed weights (POLICY 'judge_top', 'judge_second';
otherwise the scripted style), so only legal values can appear and no single habit takes over. Every ruling is
logged with its reason.

What the judge knows (`--judge-hears`, docs/open-decisions.md section 2b):
- all (the default): the Grimoire, every night choice, everything said aloud, every whisper, every nomination and
  vote, the death log. Never a player's thinking or their answers to belief probes.
- public: the same without the whispers (and only the latest night's choices), as a human Storyteller hears.
Madness is judged on the same hearing (madness_evidence): with `all`, a whispered confession is overheard. The
scripted Storyteller's own madness floor reads only what was said aloud (docs/snv-rulings.md, ruling 1).

Modes (`--judge`):
- scripted: no judge; the scripted Storyteller decides (the default; Trouble Brewing's protocol v17).
- rules: a free, deterministic judge (RulesJudge: its heuristics are listed there).
- dry-run: writes the prompt a model judge would get (judge-prompts.jsonl in the game folder), calls nothing,
  and ranks as `rules` does.
- model: a model ranks (`--judge-model`, an API key, within the budget ledger).

Only decisions sent through Game.decide_judged reach the judge: every discretionary call the engine makes (a
Choice's context names the `call`; see state.judged). Calls that are pure dice the rules require (completing a
player's incomplete choice, which of several simultaneous nominations is taken) stay with the game's rng.

The judge studies the script: Storyteller's notes per script (data/storyteller/<script>.md, one section per
character) are in every model and dry-run prompt, for the characters in play.
"""
from __future__ import annotations
import json
import random
import re
from pathlib import Path

from .characters import kind
from .state import _key

HEARS = ('all', 'public')

RUBRIC = """You are the Storyteller of a game of Blood on the Clocktower, deciding one thing the rules leave to you.
Decide as a skilled Storyteller who has followed everything: who is what, what each player has claimed and to whom,
how the votes went, and what each answer would do to the game from here.
The engine has listed every legal answer; rank them, best first, by these principles:
- Honour both abilities where you can: when two characters' abilities meet (the Spy nominating the Virgin, the
  Slayer shooting the Recluse), prefer the answer that lets each do what it is for and makes sense afterwards.
- Listen to the bluffs of the evil players and support those bluffs wherever possible. If information is about an
  evil player who has claimed a good character, showing that character helps their lie sound like the truth.
- Make drunkenness and poisoning as harmful as possible to the drunk or poisoned player: their information should
  usually be false, and false in a way that misleads them and the town, not in a way that gives the lie away.
- Honour deliberate plays: if evil poisoned or drank someone to support a bluff, reward it.
- Keep the game close: when one team is far ahead, lean your free choices toward the other (the designers' advice
  to help the weaker team), without breaking a rule or making an answer impossible for the setup.
- Keep the game fun and fair: never give information that is impossible for the setup, and avoid answers that
  would end the game on the spot by your own choice.
- Use the Storyteller's notes for the characters in play: they say what to watch for and how it is usually run.
What you heard (every whisper, or only what was said aloud) is stated at the top of each decision. You never see the
players' private thinking.
Answer with JSON: {"ranking": [indexes of the answers, best first, at least the top three], "reason": "one or two
sentences, quoting what you relied on"}."""

SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['ranking', 'reason'],
          'properties': {'ranking': {'type': 'array', 'items': {'type': 'integer'}}, 'reason': {'type': 'string'}}}
PUBLIC = ('say', 'nomination', 'defense', 'ability', 'slayer')
NOTES = Path(__file__).resolve().parent / 'data' / 'storyteller'
SHORTLIST = 40  # a model is shown at most this many answers (the rules judge's, then the scripted style's draws)


def _heard(ev, hears):
    """Whether a judge with this hearing heard the event: public speech, what players said to the Storyteller on a
    visit (the Savant's, the Artist's: said to them, so heard either way), and whispers when hearing all."""
    if ev['to'] == 'public' and ev['kind'] in PUBLIC:
        return True
    if ev['kind'] == 'visit_text':
        return True
    return hears == 'all' and ev['kind'] == 'whisper'


def record(game, hears='public', limit=None):
    """What the judge heard, as text: speech, nominations, defenses, claimed abilities, and (hearing all) whispers.
    Never anyone's thinking."""
    out = []
    for ev in game.events:
        if not _heard(ev, hears):
            continue
        d = ev['data']
        if ev['kind'] == 'whisper':
            out.append(f"Day {ev['day']}, {d['from']} whispers to {' and '.join(d['to'])}: {d.get('text') or ''}")
            continue
        if ev['kind'] == 'visit_text':
            out.append(f"Day {ev['day']}, {d['player']} visits you in private (as the {d['character']}): "
                       f"{d.get('text') or '(says nothing)'}")
            continue
        who = d.get('speaker') or d.get('nominator') or d.get('nominee') or d.get('player') or d.get('shooter')
        text = d.get('text') or (f"claims the {d['character']}'s ability" if ev['kind'] == 'ability' else '')
        if ev['kind'] == 'nomination':
            text = f"nominates {d['nominee']}: {text}"
        if text:
            out.append(f"Day {ev['day']}, {who}: {text}")
    return out[-limit:] if limit else out


def public_record(game, limit=None):
    """What everyone heard (no whispers, no thinking)."""
    return record(game, 'public', limit)


def claim_events(game, hears='public'):
    """Every simple claim heard ("I'm the X", "I am the X"), in order: (player, character, None if said aloud, else
    the whisper's recipients)."""
    names = sorted(game.g.script.all, key=len, reverse=True)
    pattern = re.compile(r"\bI(?:'m| am)(?: the| a| an)? (" + '|'.join(re.escape(n) for n in names) + r")\b", re.I)
    by_lower = {n.lower(): n for n in names}
    out = []
    for ev in game.events:
        d = ev['data']
        if ev['to'] == 'public' and ev['kind'] in ('say', 'defense', 'nomination'):
            who, to = d.get('speaker') or (d.get('nominee') if ev['kind'] == 'defense' else d.get('nominator')), None
        elif hears == 'all' and ev['kind'] == 'whisper':
            who, to = d['from'], list(d['to'])
        else:
            continue
        for m in pattern.finditer(d.get('text') or ''):
            out.append((who, by_lower[m.group(1).lower()], to))
    return out


def claims(game, hears='public'):
    """{player: the character they most recently claimed}: aloud, or (hearing all) to anyone."""
    return {who: c for who, c, _ in claim_events(game, hears)}


TYPES = ('townsfolk', 'outsider', 'minion', 'demon')


def madness_evidence(game, player, about, since, hears='public', after=None):
    """What the Storyteller heard `player` say from day `since` on (and, given `after`, only in events from that
    sequence number on: a later checkpoint the same day) about being `about` (a character, or a character type such as
    'Outsider'), for judging madness: aloud (speech, nominations, defenses, and public ability claims, which claim that
    character), what they said to the Storyteller on a visit (not aloud), and whispers too when hearing all (the
    almanac: the Storyteller "overhears" a private hint). Never anyone's thinking or belief probes. Returns {'since',
    'after', 'aloud': claimed `about` aloud,
    'claimed': claimed it anywhere heard, 'latest_matches': the latest character or type they were heard claiming is
    `about` (None: no claim), 'denied': said they are not `about`, 'confessed': said they are mad, 'quotes'}."""
    g = game.g
    names = sorted(g.script.all, key=len, reverse=True)
    alt = '|'.join(re.escape(n) for n in names) + '|' + '|'.join(TYPES)
    claim = re.compile(rf"\bI(?:'m| am)(?: the| a| an)? ({alt})\b", re.I)
    deny = re.compile(rf"\bI(?:'m| am) not(?: the| a| an)? ({alt})\b", re.I)
    mad = re.compile(r"\bI(?:'m| am| was)(?: actually| really| secretly| made)? mad\b(?! at)"
                     r"|\bCerenovus (?:chose|picked|made|selected|targeted|got) me\b", re.I)
    canon = {n.lower(): n for n in names} | {t: t.capitalize() for t in TYPES}

    def fits(c):
        return c == about or (c in g.script.all and kind(c) == about)
    out = {'since': since, 'after': after, 'aloud': False, 'claimed': False, 'latest_matches': None, 'denied': False,
           'confessed': False, 'quotes': []}
    for ev in game.events:
        d = ev['data']
        if ev['day'] < since or (after is not None and ev['seq'] < after) or not _heard(ev, hears):
            continue
        if ev['kind'] == 'whisper':
            who = d.get('from')
        elif ev['kind'] == 'defense':
            who = d.get('nominee')
        else:
            who = d.get('speaker') or d.get('nominator') or d.get('player')
        if who != player:
            continue
        aloud = ev['kind'] not in ('whisper', 'visit_text')
        text = d.get('text') or ''
        said = [canon[m.group(1).lower()] for m in claim.finditer(text)]
        if ev['kind'] == 'ability':
            said.append(d['character'])  # claiming a character's ability claims the character
        for c in said:
            out['latest_matches'] = fits(c)
            if fits(c):
                out['claimed'] = True
                out['aloud'] = out['aloud'] or aloud
        if any(fits(canon[m.group(1).lower()]) for m in deny.finditer(text)):
            out['denied'] = True
        if mad.search(text):
            out['confessed'] = True
        if said or out['denied'] or mad.search(text):
            how = '' if aloud else ', to you' if ev['kind'] == 'visit_text' else ', whispered'
            out['quotes'].append(f"day {ev['day']}{how}: {text[:120]}")
    return out


def standing(game):
    """Which team is well ahead, from the Grimoire and the votes: ('good', 'evil' or 'close', why). A heuristic for
    the rules judge's balancing (TPI's advice to help the weaker team), for review:
    - evil is well ahead when three or fewer players live, the Demon among them (the final day);
    - good is well ahead when an evil player has died and five or more players live, or when the Demon's latest
      nomination put them on the block;
    - evil is also well ahead when no evil player has died and either four or fewer players live or at least half the
      good team (two at least) is dead;
    - otherwise the game is close."""
    g = game.g
    alive = [p for p in g.players if p.alive]
    evil_dead = sum(1 for p in g.players if p.evil and not p.alive)
    good = [p for p in g.players if not p.evil]
    good_dead = sum(1 for p in good if not p.alive)
    demon = g.demon()
    noms = [x for x in g.nominations if demon and x['nominee'] == demon.name]
    last_day = max((x['day'] for x in g.nominations), default=None)
    if demon and len(alive) <= 3:
        return 'evil', f'only {len(alive)} players live, the Demon among them'
    if evil_dead and len(alive) >= 5:
        return 'good', f'an evil player is dead and {len(alive)} players live'
    if noms and noms[-1]['day'] == last_day and noms[-1].get('outcome') == 'block':
        return 'good', f'the Demon ({demon.name}) was put on the block on day {last_day}'
    if not evil_dead and (len(alive) <= 4 or good_dead >= max(2, len(good) // 2)):
        return 'evil', f'no evil player is dead, {good_dead} good players are, and {len(alive)} live'
    return 'close', 'neither team is far ahead'


def summary(game, hears='public'):
    """A short state of the game for the judge: alive and dead, ghost votes left, claims (aloud, and whispered when
    hearing all), executions so far, the death log, recent votes, and which team is ahead."""
    g = game.g
    alive = [p.name for p in g.players if p.appears_alive]
    dead = [p for p in g.players if not p.appears_alive]
    lines = [f'Alive ({len(alive)}): {", ".join(alive) or "nobody"}.',
             f'Dead ({len(dead)}): {", ".join(p.name for p in dead) or "nobody"}.'
             + (f' Ghost votes left: {", ".join(p.name for p in dead if p.ghost_vote) or "none"}.' if dead else '')]
    events = claim_events(game, hears)
    aloud = {who: c for who, c, to in events if to is None}
    if aloud:
        lines.append('Claims aloud (the latest each): ' + '; '.join(f'{p} claims {c}' for p, c in aloud.items())
                     + '.')
    if hears == 'all':
        whispered = {}
        for who, c, to in events:
            if to is not None:
                whispered[(who, c)] = sorted(set(whispered.get((who, c), [])) | set(to))
        if whispered:
            lines.append('Claims in whispers: ' + '; '.join(f'{p} told {", ".join(to)} they are the {c}'
                                                           for (p, c), to in whispered.items()) + '.')
    if g.executions:
        lines.append('Executions: ' + '; '.join(f"day {e['day']} {e['player']}" + ('' if e['died'] else
                                                                                  ' (did not die)')
                                                for e in g.executions) + '.')
    if g.death_log:
        lines.append('Deaths: ' + '; '.join(f"{d['player']} (day {d['day']}, {d['phase']}, {d['cause']}"
                                            + (', seems dead' if d.get('seems') else '') + ')'
                                            for d in g.death_log) + '.')
    if g.nominations:
        lines.append('Recent votes: ' + '; '.join(
            f"day {x['day']} {x['nominator']} nominated {x['nominee']}: {x.get('votes', '?')} votes"
            + (f" ({x['outcome']})" if x.get('outcome') else '') for x in g.nominations[-6:]) + '.')
    lead, why = standing(game)
    lines.append(f'Who is ahead: {"close" if lead == "close" else lead + " is well ahead"} ({why}).')
    return '\n'.join(lines)


def night_choices(game, hears='public'):
    """The players' night choices the Storyteller saw: every night's when hearing all, else the latest night's."""
    evs = [ev for ev in game.events if ev['kind'] == 'night_choice']
    if hears != 'all' and evs:
        evs = [ev for ev in evs if ev['day'] == evs[-1]['day']]
    out = []
    for ev in evs:
        d = ev['data']
        what = ', '.join(d.get('targets') or []) or 'no one'
        if d.get('character'):
            what += f" (character: {d['character']})"
        out.append(f"Night {ev['day']}, {d['player']} ({d['role']}) chose {what}")
    return out


def _sections(path):
    """{heading: text} for a notes file's '## ' sections."""
    out, name, body = {}, None, []
    for line in path.read_text().split('\n'):
        if line.startswith('## '):
            if name:
                out[name] = '\n'.join(body).strip()
            name, body = line[3:].strip(), []
        elif name:
            body.append(line)
    if name:
        out[name] = '\n'.join(body).strip()
    return out


def storyteller_notes(script_id, characters):
    """The Storyteller's notes for these characters, as text: their sections of data/storyteller/<script_id>.md
    (or of another script's notes, for a character from elsewhere), in the order given."""
    own = NOTES / f'{script_id}.md'
    found = _sections(own) if own.exists() else {}
    for path in sorted(NOTES.glob('*.md')):
        if path != own:
            for k, v in _sections(path).items():
                found.setdefault(k, v)
    return '\n\n'.join(f'{c}: {found[c]}' for c in dict.fromkeys(characters) if c in found)


def in_play(g):
    """The characters in play, in seat order, with the ones players believe they are (the Drunk's, the Lunatic's)."""
    return list(dict.fromkeys(c for p in g.players for c in (p.character, p.shown)))


def describe(value):
    v = {k: x for k, x in value.items() if x not in (None, [])}
    return ', '.join(f'{k}: {x}' for k, x in v.items()) or 'nothing'


class Judge:
    """The base judge: no opinion (the scripted Storyteller decides). `hears`: 'all' or 'public'."""
    mode = 'scripted'

    def __init__(self, hears='all'):
        if hears not in HEARS:
            raise ValueError(f'unknown hearing: {hears}')
        self.hears = hears

    async def rank(self, game, choice):
        """(values of choice.values, best first, or [] for no opinion; the reason)."""
        return [], ''


class RulesJudge(Judge):
    """Free and deterministic. Its heuristics, by the call (state.judged), each giving a short reason:
    - information: supports a claim, showing an evil player who claimed a good character as that character (the
      rulebook: support evil's bluffs; the wiki's Spy advice); for a drunk or poisoned recipient, what a working
      ability could not show, an evil character first for a good player (the rulebook's Ravenkeeper tip).
    - spy_virgin: a nominator who claims a Townsfolk registers as one and is executed (both abilities honoured: the
      Virgin works, and the claim is borne out); one who claims an Outsider, Minion or Demon does not; with no claim,
      by balance (below).
    - yes/no calls that help one team (the context's 'helps': the Slayer killing the Recluse and the Tinker dying
      help evil; the Spy executed by the Virgin and the Pacifist's save help good): when a team is well ahead
      (standing), the answer that helps the other; when it is close, no opinion (the scripted weight).
    - mayor_bounce: good well ahead, the Mayor dies; evil well ahead, the kill bounces to another good player
      (clockwise from the Mayor); close, no opinion.
    - starpass: the Minion who claimed a good character first, then the one the town suspects least (fewest votes
      against them), so evil's bluff carries on.
    - gossip_victim: good well ahead, a good player who will die; evil well ahead, an evil one (never the Demon);
      close, or three alive, no opinion.
    - regurgitation: evil well ahead, a good player comes back; otherwise no opinion.
    - madness: whether the player broke their madness, from what this judge heard (madness_evidence, with
      whispers when hearing all): told to be mad about a character, they broke it unless they claimed it aloud and
      their latest claim heard was it, without denying it or saying they were mad; told not to be mad about something
      (the Mutant), they broke it by claiming it. The quotes it relied on are the reason.
    - madness_penalty: a good player who broke madness is executed (the rulebook: the player's choice); an evil one
      by the balance (the almanac: "might" lets the Storyteller stop evil using it).
    - sweetheart_drunk: a living good Townsfolk; with evil well ahead, a living evil player (the almanac).
    - the Savant's statements, the Artist's questions the code can't answer, the Barber's Demon: no opinion (the
      scripted style: the Savant's scoring rule, "I don't know"); a model judge ranks them.
    - speech_near_miss (the Mezepheles's word, the Yaggababble's phrase said not quite exactly): it counts when what
      was said is the same word in another form (the word and an ending: s, es, 's, d, ed, ing, ly, er), or the phrase
      with each of its words so; a misspelling, another word that starts the same, or a word added inside a phrase
      does not.
    - setup calls (the red herring, the Drunk's character, the Demon's and the Lunatic's bluffs, the Grandchild),
      the Sailor's and Innkeeper's drunk, and Gossip statements the code can't read: no opinion (the scripted
      style, which follows the almanacs; there is nothing yet to read, or nothing this judge can read)."""
    mode = 'rules'

    async def rank(self, game, choice):
        return self.ranking(game, choice)

    def ranking(self, game, choice):
        ctx = getattr(choice, 'context', {}) or {}
        call = ctx.get('call')
        ranked, reasons = [], []
        if ctx.get('rules_opinion') is False:  # (the Savant's thousands of pairs: the scripted scoring rule picks)
            return [], ''

        def add(values, reason):
            ranked.extend(v for v in values if v not in ranked)
            if values and reason:
                reasons.append(reason)
        for values, reason in self.bluff_support(game, choice, ctx):
            add(values, reason)
        rule = getattr(self, f'_{call}', None) if call else None
        if rule:
            add(*rule(game, choice, ctx))
        elif 'helps' in ctx:
            add(*self.balance(game, choice, ctx))
        truth = getattr(choice, 'truth', None)
        if truth is not None and ctx.get('impaired'):
            about = ctx.get('about')
            good = about and not game.g[about].evil
            false = [v for v in choice.values if not truth(v) and v not in ranked]
            if good:  # about a good player: an evil character misleads most (rulebook)
                false.sort(key=lambda v: kind(v['character']) not in ('Minion', 'Demon') if v.get('character') else 1)
            add(false, 'the recipient is drunk or poisoned: give false information'
                + (', and show a good player as evil' if good else ''))
        return ranked, '; '.join(reasons)

    def _tinker(self, game, choice, ctx):
        """The Tinker usually dies at night, where the death hides (owner's notes): first choice on a night with no
        other death yet (it passes for the Demon's kill) or after a fake Gossip claim that day (it passes for the
        Gossip's kill); by day, not (a public death confirms the Tinker). Otherwise by the balance."""
        yes = [v for v in choice.values if v.get('yes')]
        no = [v for v in choice.values if v.get('yes') is False]
        if ctx.get('when') != 'night':
            return no, 'a Tinker death by day stands out: keep it for the night'
        if ctx.get('quiet_night'):
            return yes, 'nobody has died tonight: a Tinker death passes for the Demon\'s kill'
        if ctx.get('fake_gossip'):
            who = ', '.join(ctx['fake_gossip'])
            return yes, f"{who} falsely claimed the Gossip today: a death tonight looks like the Gossip's"
        return self.balance(game, choice, ctx)  # no cover tonight: by the balance, as for other calls

    def bluff_support(self, game, choice, ctx):
        """[(values showing an evil player as the good character they claimed, why)], by this judge's hearing."""
        if ctx.get('call') not in (None, 'information'):
            return []
        g = game.g
        out = []
        for who, claim in claims(game, self.hears).items():
            if not g[who].evil or kind(claim) not in ('Townsfolk', 'Outsider'):
                continue
            match = [v for v in choice.values if (v.get('character') == claim or
                                                  (who == ctx.get('about') and claim in v.get('characters', [])))
                     and (who == ctx.get('about') or who in v.get('players', []))]  # (the Dreamer's pair)
            if match:
                out.append((match, f'{who} claimed the {claim}: support the bluff'))
        return out

    def balance(self, game, choice, ctx):
        """A yes/no call whose yes helps ctx['helps']: the answer that helps the team behind, when one is far
        behind."""
        lead, why = standing(game)
        if lead == 'close':
            return [], ''
        yes = lead != ctx['helps']  # yes helps the trailing team
        return [v for v in choice.values if v.get('yes') is yes], f'{lead} is well ahead ({why}): help the other team'

    ENDINGS = ('s', 'es', 'd', 'ed', 'ing', 'ly', 'er', 'r')

    def _speech_near_miss(self, game, choice, ctx):
        from .game import words
        said, target = words(ctx.get('form')), words(ctx.get('phrase'))
        same = len(said) == len(target) and all(a == b or (a.startswith(b) and a[len(b):] in self.ENDINGS)
                                                for a, b in zip(said, target))
        return ([v for v in choice.values if v['yes'] is same],
                f'"{ctx.get("form")}" is {"" if same else "not "}a form of "{ctx.get("phrase")}"')

    def _spy_virgin(self, game, choice, ctx):
        claim = claims(game, self.hears).get(ctx['about'])
        if claim and kind(claim) == 'Townsfolk':
            return ([v for v in choice.values if v['yes'] is True],
                    f"{ctx['about']} claims the {claim}: registering as a Townsfolk honours the Virgin and bears out "
                    'the claim')
        if claim:
            return ([v for v in choice.values if v['yes'] is False],
                    f"{ctx['about']} claims the {claim}, not a Townsfolk: the Virgin's silence fits the claim")
        return self.balance(game, choice, ctx)

    def _madness(self, game, choice, ctx):
        from .state import madness_broken
        ev = madness_evidence(game, ctx['about'], ctx['mad_about'], ctx.get('since', game.day), self.hears,
                              ctx.get('after'))
        broke = madness_broken(ev, ctx.get('must', True))
        quotes = '; '.join(ev['quotes'][-3:]) or 'nothing said about it'
        return ([v for v in choice.values if v['yes'] is broke],
                f"{ctx['about']} {'broke' if broke else 'kept'} their madness about the {ctx['mad_about']} ({quotes})")

    def _madness_penalty(self, game, choice, ctx):
        if not game.g[ctx['about']].evil:
            return ([v for v in choice.values if v['yes'] is True],
                    'a good player who broke their madness chose the penalty: execute them')
        return self.balance(game, choice, ctx)

    def _sweetheart_drunk(self, game, choice, ctx):
        """The almanac: almost always a Townsfolk, which hurts good; with evil winning convincingly, an evil player."""
        lead, why = standing(game)
        g = game.g
        alive = [v for v in choice.values if g[v['players'][0]].alive]
        if lead == 'evil':
            return ([v for v in alive if g[v['players'][0]].evil],
                    f'evil is well ahead ({why}): an evil player is made drunk')
        return ([v for v in alive if not g[v['players'][0]].evil and kind(g[v['players'][0]].character) == 'Townsfolk'],
                'a living good Townsfolk is made drunk, as the almanac advises')

    def _mayor_bounce(self, game, choice, ctx):
        lead, why = standing(game)
        g, mayor = game.g, ctx['about']
        if lead == 'good':
            return [v for v in choice.values if v['players'] == [mayor]], f'good is well ahead ({why}): the Mayor dies'
        if lead == 'evil':
            names = [p.name for p in g.players]
            i = names.index(mayor)
            good = [v for x in names[i + 1:] + names[:i] for v in choice.values
                    if v['players'] == [x] and not g[x].evil]
            return good, f'evil is well ahead ({why}): the kill bounces to another good player'
        return [], ''

    def _starpass(self, game, choice, ctx):
        g = game.g
        said = claims(game, self.hears)
        against = {}
        for x in g.nominations:
            against[x['nominee']] = against.get(x['nominee'], 0) + (x.get('votes') or 0)

        def key(v):
            m = v['players'][0]
            claimed = said.get(m)
            return not (claimed and kind(claimed) in ('Townsfolk', 'Outsider')), against.get(m, 0), g[m].seat
        return sorted(choice.values, key=key), ('the Minion with a good claim, then the least suspected, takes over, '
                                                "so evil's bluff carries on")

    def _gossip_victim(self, game, choice, ctx):
        from .bmr import will_die
        lead, why = standing(game)
        g = game.g
        if lead == 'close' or g.alive_count() <= 3:
            return [], ''
        dying = [v for v in choice.values if will_die(g, g[v['players'][0]], 'gossip')
                 and not g[v['players'][0]].is_demon]
        team = [v for v in dying if g[v['players'][0]].evil == (lead == 'evil')]
        return team, f'{lead} is well ahead ({why}): a{"n evil" if lead == "evil" else " good"} player dies'

    def _regurgitation(self, game, choice, ctx):
        lead, why = standing(game)
        if lead != 'evil':
            return [], ''
        good = [v for v in choice.values if v['players'] and not game.g[v['players'][0]].evil]
        return good, f'evil is well ahead ({why}): a good player comes back'


class DryRunJudge(RulesJudge):
    """Writes the prompt a model would get, and ranks as the rules judge does."""
    mode = 'dry-run'

    async def rank(self, game, choice):
        ranked, reason = self.ranking(game, choice)
        if game.out:
            values = shortlist(game, choice, ranked)
            with (game.out / 'judge-prompts.jsonl').open('a') as f:
                f.write(json.dumps({'choice': choice.id, 'day': game.day, 'hears': self.hears,
                                    'prompt': prompt(game, choice, self.hears, values)}) + '\n')
        return ranked, reason


class ModelJudge(Judge):
    """A model ranks the legal values (an API call per judged decision; recorded in calls.jsonl)."""
    mode = 'model'

    def __init__(self, model, client=None, ledger=None, effort='low', hears='all'):
        super().__init__(hears)
        self.model, self.client, self.ledger, self.effort = model, client, ledger, effort

    async def rank(self, game, choice):
        from .llm import conversation
        values = shortlist(game, choice, RulesJudge(self.hears).ranking(game, choice)[0])
        c = conversation(self.client, RUBRIC, SCHEMA, model=self.model, effort=self.effort, label='storyteller',
                         ledger=self.ledger, on_call=game.record_call, max_tokens=4000)
        reply = await c.send(prompt(game, choice, self.hears, values),
                             {'kind': 'judge', 'day': game.day, 'choice': choice.id})
        a = reply.action or {}
        order = [i for i in a.get('ranking') or [] if isinstance(i, int) and 0 <= i < len(values)]
        return [values[i] for i in dict.fromkeys(order)], str(a.get('reason') or '')[:500]


def shortlist(game, choice, ranked=(), limit=SHORTLIST):
    """The answers a model is shown: all of them, or for a long list (the Demon's bluffs, a drunk Washerwoman's
    pairs) the rules judge's top answers, then distinct draws of the scripted style from a private random generator
    (the game's own draws, and the Grimoire's false worlds for impaired players, are left untouched)."""
    if len(choice.values) <= limit:
        return list(choice.values)
    out, keys = [], set()

    def add(v):
        if choice.legal(v) and _key(v) not in keys and len(out) < limit:
            keys.add(_key(v))
            out.append(v)
    for v in ranked[:limit // 4]:
        add(v)
    g = game.g
    saved = {k: dict(getattr(g, k)) for k in ('truthful', 'decoys') if isinstance(getattr(g, k, None), dict)}
    r = random.Random(f'{game.seed}:{choice.id}:{len(game.events)}')
    try:
        for _ in range(limit * 5):
            if len(out) >= limit:
                break
            add(choice.options(r))
    finally:
        for k, v in saved.items():
            setattr(g, k, v)
    for v in choice.values:  # too few distinct draws: the rest in order
        add(v)
    return out


def prompt(game, choice, hears='public', values=None):
    """Everything the Storyteller knows for this decision (by `hears`), the Storyteller's notes for the characters
    in play, and the legal answers (or `values`, a shortlist of them), numbered."""
    g = game.g
    ctx = getattr(choice, 'context', {}) or {}
    values = list(choice.values) if values is None else values
    heard = ('You hear everything: every whisper as well as everything said aloud.' if hears == 'all' else
             'You hear only what is said aloud, not private whispers.')
    lines = [heard, '', 'THE GRIMOIRE', g.grimoire_text(), '', f'Night or day: {game.phase} {game.day}.', '',
             'THE STATE OF THE GAME', summary(game, hears), '',
             'NIGHT CHOICES' + (' (every night)' if hears == 'all' else ' (the latest night)')]
    lines += night_choices(game, hears) or ['(none yet)']
    lines += ['', 'WHAT EVERYONE HAS SAID ALOUD' + (', AND EVERY WHISPER' if hears == 'all' else '')]
    lines += record(game, hears, limit=200) or ['(nothing yet)']
    notes = storyteller_notes(g.script.id, in_play(g))
    if notes:
        lines += ['', "STORYTELLER'S NOTES (the characters in play)", notes]
    lines += ['', 'THE DECISION', ctx.get('question') or choice.id]
    if ctx.get('impaired'):
        lines.append(f"{ctx.get('recipient')} is drunk or poisoned, so any answer is legal.")
    if len(values) < len(choice.values):
        lines.append(f'(A shortlist of {len(values)} of the {len(choice.values)} legal answers.)')
    lines += ['Legal answers:'] + [f'{i}: {describe(v)}' for i, v in enumerate(values)]
    return '\n'.join(lines)


def make(mode, hears='all', **kw):
    """The judge for a `--judge` mode, hearing `hears` (`--judge-hears`), or None (scripted)."""
    if mode in (None, 'scripted'):
        return None
    if mode == 'rules':
        return RulesJudge(hears)
    if mode == 'dry-run':
        return DryRunJudge(hears)
    if mode == 'model':
        return ModelJudge(hears=hears, **kw)
    raise ValueError(f'unknown judge mode: {mode}')
