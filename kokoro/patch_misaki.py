#!/usr/bin/env python3
"""
Patch script for misaki.cutlet to use GenericTagger instead of Tagger.
"""

import os
import sys
from pathlib import Path

def patch_misaki():
    """Patch misaki.cutlet to use GenericTagger instead of Tagger."""
    try:
        # Find the misaki package
        import misaki
        misaki_path = Path(misaki.__file__).parent
        cutlet_path = misaki_path / "cutlet.py"

        if not cutlet_path.exists():
            print(f"Error: Could not find {cutlet_path}")
            return False

        # Read the cutlet.py file
        with open(cutlet_path, "r") as f:
            content = f.read()

        # Check if the file has already been patched
        if "from fugashi import GenericTagger" in content:
            print("misaki.cutlet is already patched.")
            return True

        # Replace "from fugashi import Tagger" with "from fugashi import GenericTagger, Tagger"
        content = content.replace(
            "from fugashi import Tagger",
            "from fugashi import GenericTagger, Tagger"
        )

        # Replace the Cutlet.__init__ method to accept a tagger parameter
        content = content.replace(
            "    def __init__(self):",
            "    def __init__(self, tagger=None):"
        )

        # Replace "self.tagger = Tagger()" with code that uses the provided tagger or creates a new one
        content = content.replace(
            "        self.tagger = Tagger()",
            "        if tagger is not None:\n"
            "            self.tagger = tagger\n"
            "        else:\n"
            "            try:\n"
            "                self.tagger = Tagger()\n"
            "            except RuntimeError:\n"
            "                print('Using GenericTagger with ipadic-utf8 dictionary')\n"
            "                self.tagger = GenericTagger('-d /var/lib/mecab/dic/ipadic-utf8')"
        )

        # Write the patched file
        with open(cutlet_path, "w") as f:
            f.write(content)

        print(f"Successfully patched {cutlet_path}")
        return True

    except Exception as e:
        print(f"Error patching misaki.cutlet: {e}")
        return False

if __name__ == "__main__":
    if patch_misaki():
        print("Patch successful!")
        sys.exit(0)
    else:
        print("Patch failed!")
        sys.exit(1)
