# Official character data

`roles.json`, `nightsheet.json` and `jinxes.json` are The Pandemonium Institute's data files for community
toolmakers, copied unchanged from
[ThePandemoniumInstitute/botc-release](https://github.com/ThePandemoniumInstitute/botc-release/tree/f10cd02e3401af227ce406287eaae7bb99a06a42/resources/data)
at commit `f10cd02e3401af227ce406287eaae7bb99a06a42` (2026-08-05), also served at
https://release.botc.app/resources/data/.

They are used here under TPI's
[Community Created Content Policy](https://bloodontheclocktower.com/pages/community-created-content-policy),
which makes them available to toolmakers "subject to the terms of the policy" (non-commercial, clearly
community-made, not competing with TPI's own products). TPI asks projects that need stable files to host their
own copy, which is why they are pinned here rather than fetched. Blood on the Clocktower and its characters
belong to The Pandemonium Institute.

What the engine takes from them: each character's official id, name, type and edition, the universal night
order (`nightsheet.json`), reminder tokens and jinxes. It does not take ability wording: the player prompt keeps
the protocol's own text (`clocktower/characters.py`), so updating these files never changes a frozen protocol.

To update: copy the three files from a newer commit, change the commit above, and run
`python -m unittest discover -s tests` (the tests check the engine's characters against this data).
