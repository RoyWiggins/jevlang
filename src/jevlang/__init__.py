"""jevlang: Python where every branch is decided by Jev.

Write ``# coding: jev`` at the top of a file and every ``if``, ``elif``,
``while`` and ``match`` in it is answered by the Jev decision engine
(https://jevai.net/) -- which also means the conditions can be plain
English::

    # coding: jev
    bottles = 99
    while there are bottles left:
        print(f"{bottles} bottles of beer")
        bottles -= 1
"""

from .codec import register
from .transform import transform

__all__ = ["register", "transform"]
__version__ = "0.1.0"
