# Scripts

Each script is a JSON file in the official script tool's format: a list of official character ids, optionally led
by a `{"id": "_meta", "name": ...}` entry. A custom script exported from the official script tool loads the same way.
The order of the list is the order characters are listed (and dealt from) within each type; for `tb.json` it is part
of protocol v17, because random setups draw from it in this order.
