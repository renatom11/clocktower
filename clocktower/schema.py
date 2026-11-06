"""One fixed output schema for every player decision.

Every decision uses the same schema, so it never changes the request prefix; the
prompt says which fields matter and the engine validates the rest.
"""


def _obj(props):
    return {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def player_schema(names, script=None):
    """The output schema for a table of `names`. Trouble Brewing's (the default) is protocol v17's; another
    script's adds a `character` field (night choices of a character) and drops the Slayer's shot unless the script
    has a Slayer."""
    name = {'type': 'string', 'enum': list(names)}
    fields = {
        'say': {'type': 'string'},
        'whispers': {'type': 'array', 'items': _obj({'to': {'type': 'array', 'items': name}, 'text': {'type': 'string'}})},
        'nominate': _nullable(name),
        'vote': _nullable({'type': 'boolean'}),
        'targets': {'type': 'array', 'items': name},
        'slayer_shot': _nullable(name),
    }
    if script is not None and script.id != 'tb':
        fields['character'] = _nullable({'type': 'string', 'enum': list(script.all)})
        if 'slayer_shot' not in script.public_actions:
            del fields['slayer_shot']
    return _obj(fields)
