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

    def test_emojis_only(self):
        input_str = "Hello 😊, what a 😮 day!"
        expected = [(0, 1.0), (1, 1.0)] # joy, surprise
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

    def test_mixed_emojis_and_tags_different_emotions(self):
        input_str = "I am 😊 and also [anger:0.7]."
        expected = [(0, 1.0), (3, 0.7)] # joy, anger
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_emoji_and_tag_same_emotion_tag_intensity_preferred(self):
        input_str1 = "This is great 😊 [joy:0.3]!"
        expected1 = [(0, 0.3)] # joy
        result1 = self.model.extract_emotion(input_str1)
        self.assertEmotionListsEqual(result1, expected1, "Failed for: emoji then tag with intensity")

        input_str2 = "This is great [joy:0.3] 😊!"
        expected2 = [(0, 0.3)] # joy
        result2 = self.model.extract_emotion(input_str2)
        self.assertEmotionListsEqual(result2, expected2, "Failed for: tag with intensity then emoji")
        
        input_str3 = "This is great [joy] 😊!" # Tag without intensity, and emoji
        expected3 = [(0, 1.0)] # joy, intensity from tag (default 1.0)
        result3 = self.model.extract_emotion(input_str3)
        self.assertEmotionListsEqual(result3, expected3, "Failed for: tag no intensity then emoji")

    def test_unknown_emojis_and_tags(self):
        input_str = "Hello 👽 [unknown_emotion] world."
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

    def test_emoji_and_tag_same_emotion_tag_no_intensity_emoji_first(self):
        # Added based on a potential ambiguity in precedence rules from previous prompt
        # If tag has no intensity, it defaults to 1.0. Emoji also defaults to 1.0.
        # Tag still takes precedence.
        input_str = "This is great 😊 [joy]!" 
        expected = [(0, 1.0)] # joy, intensity from tag (default 1.0)
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected, "Failed for: emoji then tag no intensity")

    def test_multiple_tags_and_emojis_complex(self):
        input_str = "[sadness] I am 😢 but also [joy:0.1] and a bit 😊, maybe 😮 [surprise:0.9]."
        # sadness tag (2, 1.0)
        # sadness emoji (😢) - ignored due to sadness tag
        # joy tag (0, 0.1) - takes precedence
        # joy emoji (😊) - ignored due to joy tag
        # surprise tag (1, 0.9) - takes precedence
        # surprise emoji (😮) - ignored due to surprise tag
        expected = [(2, 1.0), (0, 0.1), (1, 0.9)]
        result = self.model.extract_emotion(input_str)
        self.assertEmotionListsEqual(result, expected)

    def test_intensity_clamping(self):
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
