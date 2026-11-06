"""The Storyteller judge: for decisions that need judgment, the judge listens and ranks, the code decides.

The scripted Storyteller (state.POLICY) picks among every legal value of a Choice by fixed weights, and so cannot
"listen to the bluffs of the evil players, and support those bluffs wherever possible" (rulebook, Drunkenness and
Poisoning). A judge reads what a real Storyteller knows (the Grimoire, tonight's choices, everything said aloud;
never private whispers or anyone's thinking) and ranks the legal values. The code then picks from the ranking with
fixed weights (POLICY 'judge_top', 'judge_second'; otherwise the scripted style), so only legal values can appear
and no single habit takes over. Every ruling is logged with its reason.

Modes (`--judge`):
- scripted: no judge; the scripted Storyteller decides (the default; Trouble Brewing always).
- rules: a free, deterministic judge that reads simple public claims ("I'm the Washerwoman").
- dry-run: writes the prompt a model judge would get (judge-prompts.jsonl in the game folder), calls nothing,
  and ranks as `rules` does.
- model: a model ranks (`--judge-model`, an API key, within the budget ledger).

Only decisions the characters send through Game.decide_judged reach the judge.
"""
from __future__ import annotations
import json
import re

from .characters import kind

RUBRIC = """You are the Storyteller of a game of Blood on the Clocktower, deciding one thing the rules leave to you.
The engine has listed every legal answer; rank them, best first, by how a skilled human Storyteller would decide:
- Listen to the bluffs of the evil players and support those bluffs wherever possible. If information is about an
  evil player who has claimed a good character, showing that character helps their lie sound like the truth.
- Make drunkenness and poisoning as harmful as possible to the drunk or poisoned player: their information should
  usually be false, and false in a way that misleads them and the town, not in a way that gives the lie away.
- Honour deliberate plays: if evil poisoned or drank someone to support a bluff, reward it.
- Keep the game fun and fair: never give information that is impossible for the setup, and avoid answers that
  would end the game on the spot.
You know the whole Grimoire and everything said aloud. You do not hear private whispers.
Answer with JSON: {"ranking": [indexes of the answers, best first, at least the top three], "reason": "one or two
sentences, quoting what you relied on"}."""

SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['ranking', 'reason'],
          'properties': {'ranking': {'type': 'array', 'items': {'type': 'integer'}}, 'reason': {'type': 'string'}}}
PUBLIC = ('say', 'nomination', 'defense', 'ability', 'slayer')


def public_record(game, limit=None):
    """What everyone heard, as text: speech, nominations, defenses, claimed abilities (no whispers, no thinking)."""
    out = []
    for ev in game.events:
        d = ev['data']
        if ev['to'] != 'public' or ev['kind'] not in PUBLIC:
            continue
        who = d.get('speaker') or d.get('nominator') or d.get('nominee') or d.get('player') or d.get('shooter')
        text = d.get('text') or (f"claims the {d['character']}'s ability" if ev['kind'] == 'ability' else '')
        if ev['kind'] == 'nomination':
            text = f"nominates {d['nominee']}: {text}"
        out.append(f"Day {ev['day']}, {who}: {text}")
    return out[-limit:] if limit else out


def claims(game):
    """{player: the character they most recently claimed aloud}, from simple claims ("I'm the X", "I am the X")."""
    names = sorted(game.g.script.all, key=len, reverse=True)
    pattern = re.compile(r"\bI(?:'m| am)(?: the| a| an)? (" + '|'.join(re.escape(n) for n in names) + r")\b", re.I)
    by_lower = {n.lower(): n for n in names}
    out = {}
    for ev in game.events:
        if ev['to'] == 'public' and ev['kind'] in ('say', 'defense', 'nomination'):
            who = ev['data'].get('speaker') or (ev['data'].get('nominee') if ev['kind'] == 'defense'
                                                 else ev['data'].get('nominator'))
            for m in pattern.finditer(ev['data'].get('text') or ''):
                out[who] = by_lower[m.group(1).lower()]
    return out


def describe(value):
    v = {k: x for k, x in value.items() if x not in (None, [])}
    return ', '.join(f'{k}: {x}' for k, x in v.items()) or 'nothing'


class Judge:
    """The base judge: no opinion (the scripted Storyteller decides)."""
    mode = 'scripted'

    async def rank(self, game, choice):
        """(values of choice.values, best first, or [] for no opinion; the reason)."""
        return [], ''


class RulesJudge(Judge):
    """Free and deterministic: supports a public claim when the information is about an evil player who made one,
    and otherwise prefers what a working ability could not show (misinformation is false)."""
    mode = 'rules'

    async def rank(self, game, choice):
        ctx = getattr(choice, 'context', {}) or {}
        about = ctx.get('about')
        said = claims(game)
        truth = getattr(choice, 'truth', None)
        g = game.g
        ranked, reasons = [], []
        claim = said.get(about) if about else None
        if claim and g[about].evil and kind(claim) in ('Townsfolk', 'Outsider'):
            match = [v for v in choice.values if v.get('character') == claim]
            if match:
                ranked += match
                reasons.append(f'{about} claimed the {claim} aloud: support the bluff')
        if truth is not None and ctx.get('impaired'):
            false = [v for v in choice.values if not truth(v) and v not in ranked]
            if about and not g[about].evil:  # about a good player: an evil character misleads most (rulebook)
                false.sort(key=lambda v: kind(v['character']) not in ('Minion', 'Demon') if v.get('character') else 1)
            ranked += false
            if false:
                reasons.append('the recipient is drunk or poisoned: give false information'
                               + (', and show a good player as evil' if about and not g[about].evil else ''))
        return ranked, '; '.join(reasons)


class DryRunJudge(RulesJudge):
    """Writes the prompt a model would get, and ranks as the rules judge does."""
    mode = 'dry-run'

    async def rank(self, game, choice):
        if game.out:
            with (game.out / 'judge-prompts.jsonl').open('a') as f:
                f.write(json.dumps({'choice': choice.id, 'day': game.day, 'prompt': prompt(game, choice)}) + '\n')
        return await super().rank(game, choice)


class ModelJudge(Judge):
    """A model ranks the legal values (an API call per judged decision; recorded in calls.jsonl)."""
    mode = 'model'

    def __init__(self, model, client=None, ledger=None, effort='low'):
        self.model, self.client, self.ledger, self.effort = model, client, ledger, effort

    async def rank(self, game, choice):
        from .llm import conversation
        c = conversation(self.client, RUBRIC, SCHEMA, model=self.model, effort=self.effort, label='storyteller',
                         ledger=self.ledger, on_call=game.record_call, max_tokens=4000)
        reply = await c.send(prompt(game, choice), {'kind': 'judge', 'day': game.day, 'choice': choice.id})
        a = reply.action or {}
        order = [i for i in a.get('ranking') or [] if isinstance(i, int) and 0 <= i < len(choice.values)]
        return [choice.values[i] for i in dict.fromkeys(order)], str(a.get('reason') or '')[:500]


def prompt(game, choice):
    """Everything a Storyteller would know for this decision, and the legal answers, numbered."""
    g = game.g
    ctx = getattr(choice, 'context', {}) or {}
    lines = ['THE GRIMOIRE', g.grimoire_text(), '', f'Night or day: {game.phase} {game.day}.']
    said = claims(game)
    if said:
        lines.append('Public claims so far: ' + '; '.join(f'{p} claims {c}' for p, c in said.items()) + '.')
    lines += ['', 'WHAT EVERYONE HAS SAID ALOUD'] + (public_record(game, limit=200) or ['(nothing yet)'])
    lines += ['', 'THE DECISION', ctx.get('question') or choice.id]
    if ctx.get('impaired'):
        lines.append(f"{ctx.get('recipient')} is drunk or poisoned, so any answer is legal.")
    lines += ['Legal answers:'] + [f'{i}: {describe(v)}' for i, v in enumerate(choice.values)]
    return '\n'.join(lines)


def make(mode, **kw):
    """The judge for a `--judge` mode, or None (scripted)."""
    if mode in (None, 'scripted'):
        return None
    if mode == 'rules':
        return RulesJudge()
    if mode == 'dry-run':
        return DryRunJudge()
    if mode == 'model':
        return ModelJudge(**kw)
    raise ValueError(f'unknown judge mode: {mode}')
