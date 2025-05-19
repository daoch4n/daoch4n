"""
Custom JAG2P class for Japanese text processing.
"""

import os
import sys
from pathlib import Path
from loguru import logger

try:
    from fugashi import GenericTagger
    from misaki.ja import JAG2P as OriginalJAG2P
    from misaki.cutlet import Cutlet
except ImportError:
    logger.error("Failed to import required modules. Please install them with: pip install fugashi[unidic-lite] misaki")
    sys.exit(1)

class CustomCutlet(Cutlet):
    """
    Custom Cutlet class that uses a GenericTagger.
    """
    
    def __init__(self):
        """
        Initialize the Cutlet with a GenericTagger.
        """
        # Initialize the parent class
        super().__init__()
        
        # Replace the tagger with a GenericTagger
        try:
            # Try to find the MeCab dictionary
            mecabrc = "/usr/local/etc/mecabrc"
            if os.path.exists(mecabrc):
                with open(mecabrc, 'r') as f:
                    for line in f:
                        if line.startswith('dicdir'):
                            dicdir = line.split('=')[1].strip()
                            logger.info(f"Using MeCab dictionary: {dicdir}")
                            self.tagger = GenericTagger(f'-d {dicdir}')
                            return
            
            # Fallback to ipadic-utf8
            logger.info("Using fallback MeCab dictionary: /var/lib/mecab/dic/ipadic-utf8")
            self.tagger = GenericTagger('-d /var/lib/mecab/dic/ipadic-utf8')
        except Exception as e:
            logger.error(f"Failed to create GenericTagger: {e}")
            raise

class CustomJAG2P(OriginalJAG2P):
    """
    Custom JAG2P class that uses a CustomCutlet.
    """
    
    def __init__(self):
        """
        Initialize the JAG2P with a CustomCutlet.
        """
        # Initialize the parent class
        super().__init__()
        
        # Replace the cutlet with a CustomCutlet
        self.cutlet = CustomCutlet()
        
        logger.info("Initialized CustomJAG2P with CustomCutlet")

# Monkey patch the JAG2P class
def patch_jag2p():
    """
    Patch the JAG2P class to use our CustomJAG2P.
    """
    try:
        from misaki import ja
        
        # Save the original class
        original_jag2p = ja.JAG2P
        
        # Replace the class with our custom class
        ja.JAG2P = CustomJAG2P
        
        logger.info("Successfully patched JAG2P class")
        return True
    except Exception as e:
        logger.error(f"Failed to patch JAG2P class: {e}")
        return False
