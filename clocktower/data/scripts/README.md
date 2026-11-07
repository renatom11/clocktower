# Scripts

Each script is a JSON file in the official script tool's format: a list of official character ids, optionally led
by a `{"id": "_meta", "name": ...}` entry. A custom script exported from the official script tool loads the same way.
The order of the list is the order characters are listed (and dealt from) within each type; for `tb.json` it is part
of protocol v17, because random setups draw from it in this order.

`carousel-1.json` ("Carousel test 1") is a synthetic test script, not a published one: characters already built from
Trouble Brewing, Bad Moon Rising and Sects & Violets, chosen so that all seven official jinxes between them are on it
(docs/carousel-rulings.md) and every table size from 5 to 15 can be dealt. Its games are protocol `custom-carousel-1`.

`carousel-2.json` ("Carousel test 2") is the second: the thirteen experimental characters of batch 1 (Banshee, Damsel,
Steward, Nightwatchman, Al-Hadikhia, Magician, Golem, Summoner, Ojo, Fisherman, Plague Doctor, Hatter, Politician) with
built characters chosen so that all seventeen official jinxes between them and built characters are on it and every
table size from 5 to 15 can be dealt. Its games are protocol `custom-carousel-2`.

`carousel-3.json` ("Carousel test 3") is the third: the fifteen experimental characters of batch 2 (Pixie, High
Priestess, Poppy Grower, Shugenja, Balloonist, General, Preacher, Cannibal, Puzzlemaster, Heretic, Marionette, Widow,
Goblin, Kazali, Leviathan) with built characters chosen so that all thirty-three official jinxes between them and built
characters are on it and every table size from 5 to 15 can be dealt. Its games are protocol `custom-carousel-3`.

`carousel-4.json` ("Carousel test 4") is the fourth: the thirteen experimental characters of batch 3 (Village Idiot,
Acrobat, Lycanthrope, Alchemist, Zealot, Organ Grinder, Noble, Farmer, Harpy, Boffin, Boomdandy, Fearmonger, Xaan)
with built characters chosen so that all eighteen official jinxes between them and built characters are on it and
every table size from 5 to 15 can be dealt. Its games are protocol `custom-carousel-4`.

`carousel-5.json` ("Carousel test 5") is the fifth: the nine experimental characters of batch 3b (Alsaahir, Huntsman,
Snitch, Knight, Choirboy, King, Cult Leader, Lord of Typhon, Lleech) with built characters chosen so that all eight
official jinxes between them and built characters are on it and every table size from 5 to 15 can be dealt. Its games
are protocol `custom-carousel-5`.

`carousel-6.json` ("Carousel test 6") is the sixth: the eight experimental characters of batch 4 (Bounty Hunter,
Engineer, Princess, Hermit, Ogre, Psychopath, Wraith, Vizier) with built characters chosen so that all twenty official
jinxes between them and built characters are on it and every table size from 5 to 15 can be dealt. Its games are
protocol `custom-carousel-6`.

`carousel-7.json` ("Carousel test 7") is the seventh: the three experimental characters of batch 5 (Amnesiac,
Mezepheles, Yaggababble) with built characters chosen so that the one official jinx between them and built characters
(the Yaggababble's with the Exorcist) is on it, the Amnesiac's model characters and the Demon-protecting ones (Monk,
Soldier, Princess) meet the Yaggababble, and every table size from 5 to 15 can be dealt. Its games are protocol
`custom-carousel-7`.
