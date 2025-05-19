"""
Custom wrapper for the Kokoro TTS engine to use the GenericTagger.
"""

import os
import sys
from pathlib import Path
from loguru import logger

# Try to import the required modules
try:
    from fugashi import GenericTagger
    from kokoro import KPipeline
except ImportError:
    logger.error("Failed to import required modules. Please install them with: pip install fugashi[unidic-lite] kokoro")
    sys.exit(1)

class KokoroWrapper:
    """
    Wrapper for the Kokoro TTS engine to use the GenericTagger.
    """
    
    def __init__(self, voice="jf_alpha", language="ja", device="cpu", repo_id=None, cache_dir="cache"):
        """
        Initialize the Kokoro TTS wrapper.
        
        Args:
            voice (str): The voice to use.
            language (str): The language to use.
            device (str): The device to use (cpu or cuda).
            repo_id (str): The repository ID for the Kokoro model.
            cache_dir (str): The cache directory for the Kokoro model.
        """
        self.voice = voice
        self.language = language
        self.device = device
        self.repo_id = repo_id
        self.cache_dir = cache_dir
        
        # Create the tagger with the correct dictionary
        self.tagger = self._create_tagger()
        
        # Initialize the Kokoro pipeline
        self._initialize_pipeline()
    
    def _create_tagger(self):
        """
        Create a tagger with the correct dictionary.
        
        Returns:
            GenericTagger: The tagger instance.
        """
        # Try to find the MeCab dictionary
        mecabrc = "/usr/local/etc/mecabrc"
        if os.path.exists(mecabrc):
            with open(mecabrc, 'r') as f:
                for line in f:
                    if line.startswith('dicdir'):
                        dicdir = line.split('=')[1].strip()
                        logger.info(f"Using MeCab dictionary: {dicdir}")
                        return GenericTagger(f'-d {dicdir}')
        
        # Fallback to ipadic-utf8
        logger.info("Using fallback MeCab dictionary: /var/lib/mecab/dic/ipadic-utf8")
        return GenericTagger('-d /var/lib/mecab/dic/ipadic-utf8')
    
    def _initialize_pipeline(self):
        """
        Initialize the Kokoro pipeline.
        """
        try:
            # Monkey patch the JAG2P class to use our tagger
            from misaki import ja
            
            # Save the original JAG2P.__init__ method
            original_init = ja.JAG2P.__init__
            
            # Define a new __init__ method that uses our tagger
            def new_init(self, *args, **kwargs):
                original_init(self, *args, **kwargs)
                from misaki.cutlet import Cutlet
                self.cutlet = Cutlet(tagger=KokoroWrapper.tagger)
            
            # Replace the JAG2P.__init__ method with our new method
            ja.JAG2P.__init__ = new_init
            
            # Set the tagger as a class variable
            KokoroWrapper.tagger = self.tagger
            
            # Initialize the Kokoro pipeline
            self.pipeline = KPipeline(
                voice=self.voice,
                language=self.language,
                device=self.device,
                repo_id=self.repo_id,
                cache_dir=self.cache_dir
            )
            
            logger.info(f"Initialized Kokoro pipeline with voice: {self.voice}")
        except Exception as e:
            logger.error(f"Failed to initialize Kokoro pipeline: {e}")
            raise
    
    def generate(self, text, output_path=None):
        """
        Generate speech from text.
        
        Args:
            text (str): The text to generate speech from.
            output_path (str): The path to save the generated audio to.
            
        Returns:
            str: The path to the generated audio file.
        """
        try:
            # Generate speech
            audio_path = self.pipeline(text, output_path)
            return audio_path
        except Exception as e:
            logger.error(f"Failed to generate speech: {e}")
            raise
