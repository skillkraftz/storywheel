"""Where things live. Override with environment variables:

    STORYWHEEL_HOME  stories, universe and your own lists  (~/.storywheel)
    STORYWHEEL_OUT   where markdown goes, e.g. your vault  (~/storywheel)
"""
import os
from pathlib import Path

HOME = Path(os.environ.get("STORYWHEEL_HOME", Path.home() / ".storywheel"))
OUT = Path(os.environ.get("STORYWHEEL_OUT", Path.home() / "storywheel"))
