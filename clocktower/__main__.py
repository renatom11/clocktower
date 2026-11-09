import os
import sys

# `python -m clocktower --without lilmonsta,atheist ...`: build the engine without those batch 6 characters, as
# CLOCKTOWER_WITHOUT does (clocktower/carousel_extra.py). Set before anything loads, since the characters register
# when the engine is imported.
if sys.argv[1:2] == ['--without'] and len(sys.argv) > 2:
    os.environ['CLOCKTOWER_WITHOUT'] = sys.argv.pop(2)
    sys.argv.pop(1)
elif sys.argv[1:2] and sys.argv[1].startswith('--without='):
    os.environ['CLOCKTOWER_WITHOUT'] = sys.argv.pop(1).split('=', 1)[1]

from .cli import main  # noqa: E402

main()
