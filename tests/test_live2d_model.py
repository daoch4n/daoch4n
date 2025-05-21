import unittest
from unittest.mock import patch, MagicMock
from open_llm_vtuber.live2d_model import Live2dModel

class TestLive2dModelExtractEmotion(unittest.TestCase):

    @patch('open_llm_vtuber.live2d_model.Live2dModel._lookup_model_info')
    def setUp(self, mock_lookup_model_info):
        # This mock function will be called when Live2dModel._lookup_model_info is accessed.
        # We make it assign a predefined model_info to the instance.
        # The Live2dModel's __init__ calls set_model, which calls _lookup_model_info.
        
        # Define the model_info that our mock should return
        mock_model_data = {
            "name": "test_model",
            "emotionMap": {
                "joy": 0,
                "surprise": 1,
                "sadness": 2,
                "anger": 3,
                "neutral": 4,
                "fear": 5,
                "disgust": 6,
                "smirk": 7
            }
            # Add other fields if Live2dModel's set_model strictly requires them,
            # but for extract_emotion, only emotionMap (via self.emo_map) is crucial.
        }
        mock_lookup_model_info.return_value = mock_model_data

        # Now, when Live2dModel is instantiated, its _lookup_model_info will use our mock
        self.model = Live2dModel(live2d_model_name="mocked_model_name")
        # After this, self.model.emo_map should be correctly populated based on mock_model_data

    def assertEmotionListsEqual(self, list1, list2, msg=None):
        """Helper to compare lists of tuples, ignoring order."""
        self.assertEqual(set(map(tuple, list1)), set(map(tuple, list2)), msg)

    def test_single_emoji_intensity(self): # Renamed and updated
        input_str = "Hello 😊, what a 😮 day!" # joy, surprise
        expected = [(0, 0.3), (1, 0.3)] 
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_two_consecutive_emojis_intensity(self): # New
        input_str = "Wow 😮😮" # surprise
        expected = [(1, 0.6)]
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_three_consecutive_emojis_intensity(self): # New
        input_str = "So sad 😢😢😢" # sadness
        expected = [(2, 0.9)]
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_four_consecutive_emojis_intensity(self): # New
        input_str = "Anger 😡😡😡😡" # anger
        expected = [(3, 0.9)] # Max intensity for 3+
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)
        
    def test_mixed_single_and_multiple_emojis_intensity(self): # New
        input_str = "😊 and 😮😮😮" # joy (0.3), surprise (0.9)
        expected = [(0, 0.3), (1, 0.9)]
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_tags_only_no_intensity(self):
        input_str = "This is [joy] and [sadness]."
        expected = [(0, 1.0), (2, 1.0)] # joy, sadness
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_tags_only_with_intensity(self):
        input_str = "Feeling [joy:0.5] and [anger:0.8]."
        expected = [(0, 0.5), (3, 0.8)] # joy, anger
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_mixed_emojis_and_tags_different_emotions_sequences(self): # Updated
        input_str = "I am 😊😊 and also [anger:0.7]." # joy (0.6), anger (0.7)
        expected = [(0, 0.6), (3, 0.7)] 
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    # New tests for tag precedence with new emoji intensity logic
    def test_tag_precedence_over_single_emoji(self): 
        input_str = "😊 [joy:0.7]" # joy emoji (0.3) vs joy tag (0.7)
        expected = [(0, 0.7)] # Tag intensity wins
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_tag_precedence_over_multiple_emojis(self): 
        input_str = "😊😊😊 [joy:0.2]" # joy emoji sequence (0.9) vs joy tag (0.2)
        expected = [(0, 0.2)] # Tag intensity wins
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_tag_default_intensity_precedence_over_single_emoji(self): 
        input_str = "😊 [joy]" # joy emoji (0.3) vs joy tag (default 1.0)
        expected = [(0, 1.0)] 
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_tag_default_intensity_precedence_over_multiple_emojis(self): 
        input_str = "😊😊😊 [joy]" # joy emoji sequence (0.9) vs joy tag (default 1.0)
        expected = [(0, 1.0)] 
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_emoji_sequence_with_tag_for_different_emotion(self): 
        input_str = "😊😊 [anger:0.5]" # joy (0.6), anger (0.5)
        expected = [(0, 0.6), (3, 0.5)]
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_unknown_emojis_and_tags(self): # Updated to include sequence
        input_str = "Hello 👽 [unknown_emotion] 👽👽 world." # Unknown emoji, unknown tag
        expected = []
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_empty_string(self):
        input_str = ""
        expected = []
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_text_but_no_relevant_emotions(self):
        input_str = "Just a normal sentence."
        expected = []
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_case_sensitivity_for_tags(self):
        input_str = "This is [JOY] and [SuRpRiSe:0.2]."
        expected = [(0, 1.0), (1, 0.2)] # joy, surprise
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    # This test is effectively covered by test_tag_default_intensity_precedence_over_multiple_emojis
    # and test_tag_default_intensity_precedence_over_single_emoji.
    # The old test_emoji_and_tag_same_emotion_tag_no_intensity_emoji_first is removed.

    def test_multiple_tags_and_emojis_complex_with_sequences(self): # Updated
        input_str = "[sadness:0.8] I am 😢😢 but also [joy:0.1] and a bit 😊😊😊, maybe 😮 [surprise]."
        # sadness tag (2, 0.8) - takes precedence over 😢😢 (0.6)
        # joy tag (0, 0.1) - takes precedence over 😊😊😊 (0.9)
        # surprise tag (1, 1.0) - takes precedence over 😮 (0.3)
        expected = [(2, 0.8), (0, 0.1), (1, 1.0)]
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)
    
    def test_non_consecutive_emojis_are_separate_longest_sequence_wins_for_type(self): # New name and clarified logic
        input_str = "Happy 😊 then sad 😢 then very happy 😊😊😊."
        # Longest sequence for joy is "😊😊😊" (0.9)
        # Longest sequence for sadness is "😢" (0.3)
        expected = [(0, 0.9), (2, 0.3)] 
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_intensity_clamping_for_tags(self): # Renamed for clarity
        input_str = "[joy:5.0] [sadness:-1.0] [anger:0.77]"
        # joy intensity should be clamped to 1.0
        # sadness intensity should be clamped to 0.0
        # anger intensity should remain 0.77 (already valid if not exactly 0.8 as in prompt, it just needs to be float)
        # For the purpose of this test, let's assume the value is used as is if valid, or clamped.
        # The problem description for extract_emotion says "clamp intensity to valid range [0.0, 1.0]"
        expected = [(0, 1.0), (2, 0.0), (3, 0.77)]
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

if __name__ == '__main__':
    unittest.main()
