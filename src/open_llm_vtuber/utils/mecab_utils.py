# -*- coding: utf-8 -*-
"""
Utilities for MeCab (Japanese morphological analyzer) setup, specifically for
initializing the Fugashi GenericTagger with appropriate dictionary paths.
"""
import os
from typing import Optional
from loguru import logger

try:
    from fugashi import GenericTagger
except ImportError:
    # This allows the module to be imported even if fugashi is not installed,
    # though get_mecab_tagger will fail if called.
    logger.error("Fugashi library not found. Please install it: pip install fugashi[unidic-lite]")
    GenericTagger = None


DEFAULT_MECABRC_PATH = "/usr/local/etc/mecabrc"
COMMON_IPADIC_UTF8_PATH = "/var/lib/mecab/dic/ipadic-utf8"

def get_mecab_tagger(
    mecabrc_path: str = DEFAULT_MECABRC_PATH,
    fallback_dic_path: Optional[str] = COMMON_IPADIC_UTF8_PATH
) -> Optional[GenericTagger]:
    """
    Creates a Fugashi GenericTagger, attempting to locate the MeCab dictionary.

    The method tries the following in order:
    1. Reads `mecabrc_path` (typically `/usr/local/etc/mecabrc`) to find `dicdir`.
    2. If `mecabrc` processing fails or `dicdir` tagger initialization fails,
       it attempts to use `fallback_dic_path` (typically `/var/lib/mecab/dic/ipadic-utf8`).
    3. If all attempts fail, logs errors and returns None.

    Args:
        mecabrc_path: Path to the mecabrc file.
        fallback_dic_path: A fallback dictionary path to try if mecabrc fails.
                           If None, no fallback path is tried.

    Returns:
        A GenericTagger instance if successful, otherwise None.
    """
    if GenericTagger is None:
        logger.error("Fugashi is not installed, cannot create MeCab tagger.")
        return None

    dicdir_param = None
    mecabrc_used = False

    if os.path.exists(mecabrc_path):
        logger.info(f"Attempting to read MeCab configuration from: {mecabrc_path}")
        try:
            with open(mecabrc_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('dicdir'):
                        # Extract the path, removing potential quotes and whitespace
                        dicdir_val = line.split('=', 1)[1].strip().strip('"').strip("'")
                        if os.path.isabs(dicdir_val):
                            dicdir_param = f'-d "{dicdir_val}"'  # Quote to handle spaces
                            logger.info(f"Found MeCab dicdir in {mecabrc_path}: {dicdir_val}")
                            mecabrc_used = True
                            break
                        else:
                            logger.warning(f"Found relative dicdir in {mecabrc_path}: '{dicdir_val}'. "
                                           "This might not work reliably. Consider using an absolute path in mecabrc.")
        except IOError as e:
            logger.warning(f"Could not read {mecabrc_path}: {e}. Will attempt fallback dictionary.")
    else:
        logger.info(f"{mecabrc_path} not found. Will attempt fallback dictionary path.")

    if dicdir_param:
        try:
            logger.info(f"Initializing GenericTagger with parameters from mecabrc: {dicdir_param}")
            tagger = GenericTagger(dicdir_param)
            logger.info("Successfully initialized GenericTagger using mecabrc.")
            return tagger
        except Exception as e:
            logger.warning(f"Failed to initialize GenericTagger with dicdir from mecabrc ({dicdir_param}): {e}. "
                           "Trying fallback dictionary path if available.")
            # Fall through to fallback

    if fallback_dic_path:
        logger.info(f"Attempting to use fallback MeCab dictionary path: {fallback_dic_path}")
        try:
            tagger = GenericTagger(f'-d "{fallback_dic_path}"')
            if mecabrc_used: # Only a warning if mecabrc was found but failed, info if mecabrc wasn't there
                logger.warning(f"Successfully initialized GenericTagger using fallback dictionary: {fallback_dic_path} (mecabrc processing failed).")
            else:
                logger.info(f"Successfully initialized GenericTagger using fallback dictionary: {fallback_dic_path}.")
            return tagger
        except Exception as e:
            logger.error(f"Failed to initialize GenericTagger with fallback dictionary ('{fallback_dic_path}'): {e}")
            # Fall through to final error
    else:
        logger.info("No fallback dictionary path provided or fallback already attempted.")


    logger.error("Failed to initialize MeCab/Fugashi GenericTagger with any method.")
    logger.error("Please ensure MeCab and its dictionaries (e.g., ipadic-utf8 or unidic-lite) "
                 "are correctly installed and accessible, or mecabrc points to a valid dictionary.")
    return None
