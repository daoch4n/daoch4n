import unittest
import asyncio
import logging
import os
import wave
import pathlib
from unittest.mock import patch, MagicMock, AsyncMock

from open_llm_vtuber.agent.agents.gemini_live_agent import GeminiLiveAgent
from open_llm_vtuber.config_manager.agent import GeminiLiveConfig
from open_llm_vtuber.agent.output_types import AudioOutput, DisplayText, Actions
from open_llm_vtuber.agent.input_types import BatchInput, TextData, TextSource
from open_llm_vtuber.live2d_model import Live2dModel
from open_llm_vtuber.utils.emotion_maps import EMOTION_NAME_TO_EMOJI_MAP, EMOJI_TO_EMOTION_NAME_MAP

# Set up basic logging for easier debugging
logging.basicConfig(level=logging.INFO)

class TestGeminiLiveAgentEmojiHandling(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.cache_dir = "cache"
        pathlib.Path(self.cache_dir).mkdir(exist_ok=True)

        self.mock_live2d_model = MagicMock(spec=Live2dModel)
        # Default mock, can be overridden in specific tests
        self.mock_live2d_model.extract_emotion = MagicMock(return_value=[(0, 0.3)]) # Default to single joy emoji
        self.mock_live2d_model.get_interpolated_expression = MagicMock(return_value={"expression_index": 0, "intensity": 0.3})

        self.base_config = MagicMock(spec=GeminiLiveConfig)
        self.base_config.api_key = "test_api_key"
        self.base_config.model_name = "gemini-test-model-live-001"
        self.base_config.language_code = "en-US"
        self.base_config.voice_name = None
        self.base_config.system_instruction = "You are a helpful assistant."
        self.base_config.enable_function_calling = False
        self.base_config.function_declarations = []
        self.base_config.enable_code_execution = False
        self.base_config.enable_google_search = False
        self.base_config.disable_automatic_vad = True
        self.base_config.enable_input_audio_transcription = False
        
        self.dummy_audio_data = b'\x00\x01\x02\x03\x04\x05'
        self.created_audio_files = []

    def tearDown(self):
        for f_path in self.created_audio_files:
            if os.path.exists(f_path):
                try:
                    os.remove(f_path)
                except Exception as e:
                    logging.error(f"Error deleting test audio file {f_path}: {e}")
        self.created_audio_files = []

    def _get_audio_output_with_audio(self, results: list[AudioOutput]) -> AudioOutput | None:
        for res in results:
            if res.audio_path:
                self.created_audio_files.append(res.audio_path) # Track for cleanup
                return res
        return None

    @patch('open_llm_vtuber.agent.agents.gemini_live_agent.genai.Client')
    @patch('open_llm_vtuber.agent.agents.gemini_live_agent.GeminiLiveAgent._process_emotion_tags_for_display')
    async def test_single_prompt_llm_outputs_emoji(self, mock_process_display, MockGenaiClient):
        # --- Config for Single Prompt Mode ---
        single_prompt_config = MagicMock(spec=GeminiLiveConfig)
        for attr, value in vars(self.base_config).items(): # Copy base attributes
            setattr(single_prompt_config, attr, value)
        single_prompt_config.use_dual_prompt_system = False


        # --- Agent Instantiation ---
        agent = GeminiLiveAgent(
            config=single_prompt_config,
            character_name="TestCharSingle",
            live2d_model=self.mock_live2d_model
        )
        agent.history_conf_uid = "test_conf_single" 
        agent.history_history_uid = "test_hist_single"

        # --- Test Data ---
        llm_response_text_with_emoji = "Hello world 😊😊" # Medium joy
        
        # Update mock for this specific test case based on "😊😊" -> joy, intensity 0.6
        self.mock_live2d_model.extract_emotion.return_value = [(0, 0.6)] # Joy, index 0
        self.mock_live2d_model.get_interpolated_expression.return_value = {"expression_index": 0, "intensity": 0.6}


        # --- Mock Gemini Client and Session ---
        mock_client_instance = MockGenaiClient.return_value
        mock_live_connect = AsyncMock()
        mock_client_instance.aio.live.connect = mock_live_connect
        mock_session = AsyncMock()
        mock_live_connect.return_value.__aenter__.return_value = mock_session
        mock_live_connect.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.send_client_content = AsyncMock()

        async def mock_receive_generator_single():
            mock_response_part = MagicMock()
            part_text = MagicMock(text=llm_response_text_with_emoji, inline_data=None)
            part_audio = MagicMock(text=None, inline_data=MagicMock(data=self.dummy_audio_data, mime_type="audio/wav"))
            model_turn_mock = MagicMock(parts=[part_text, part_audio])
            server_content_mock = MagicMock(model_turn=model_turn_mock, 
                                            output_transcription=MagicMock(text=llm_response_text_with_emoji),
                                            generation_complete=False)
            mock_response_part.server_content = server_content_mock
            yield mock_response_part
            
            mock_response_complete = MagicMock()
            server_content_complete_mock = MagicMock(model_turn=None, generation_complete=True)
            mock_response_complete.server_content = server_content_complete_mock
            yield mock_response_complete

        mock_session.receive.return_value = mock_receive_generator_single()
        
        # _process_emotion_tags_for_display is now expected to remove emojis for display text if they are not desired there
        # or pass them through if they are desired. Based on current implementation, it removes tags, and emojis pass through.
        # Let's assume it's called and we can check its input.
        mock_process_display.side_effect = lambda text: text # Pass through for this test's purpose

        # --- Call agent.chat ---
        batch_input = BatchInput(texts=[TextData(content="User says hi", source=TextSource.USER)])
        results = [output async for output in agent.chat(batch_input)]

        # --- Assertions ---
        audio_output_result = self._get_audio_output_with_audio(results)
        self.assertIsNotNone(audio_output_result, "No AudioOutput with audio_path found")

        self.mock_live2d_model.extract_emotion.assert_called_once_with(llm_response_text_with_emoji)
        self.assertEqual(audio_output_result.display_text.text, llm_response_text_with_emoji)
        self.assertEqual(audio_output_result.transcript, llm_response_text_with_emoji)
        
        # Check if _process_emotion_tags_for_display was called
        # The primary source of text for display is model_turn_text or transcript_text.
        # If LLM outputs emojis, these are in model_turn_text.
        # The logic `display_transcript = self._process_emotion_tags_for_display(model_turn_text if model_turn_text else transcript_text)`
        # means it will be called with the emoji-laden text.
        mock_process_display.assert_called_with(llm_response_text_with_emoji)


    @patch('open_llm_vtuber.agent.agents.gemini_live_agent.genai.Client')
    async def test_dual_prompt_llm_plans_emoji(self, MockGenaiClient):
        # --- Config for Dual Prompt Mode ---
        dual_prompt_config = MagicMock(spec=GeminiLiveConfig)
        for attr, value in vars(self.base_config).items():
            setattr(dual_prompt_config, attr, value)
        dual_prompt_config.use_dual_prompt_system = True

        # --- Agent Instantiation ---
        agent = GeminiLiveAgent(
            config=dual_prompt_config,
            character_name="TestCharDual",
            live2d_model=self.mock_live2d_model
        )
        agent.history_conf_uid = "test_conf_dual"
        agent.history_history_uid = "test_hist_dual"

        # --- Test Data ---
        planning_response_text_with_emoji = "Okay, I will help 😊😊😊" # High joy
        clean_response_text = "Okay, I will help"
        
        # Update mock for this specific test case's planning response
        # extract_emotion for "Okay, I will help 😊😊😊" should result in [(0, 0.9)] (joy index 0)
        self.mock_live2d_model.extract_emotion.return_value = [(0, 0.9)]
        self.mock_live2d_model.get_interpolated_expression.return_value = {"expression_index": 0, "intensity": 0.9}
        expected_actions = Actions(expressions=[{"expression_index": 0, "intensity": 0.9}])

        # --- Mock _extract_emotions_from_planning ---
        agent._extract_emotions_from_planning = AsyncMock(return_value=planning_response_text_with_emoji)

        # --- Mock Gemini Client and Session for _generate_clean_response ---
        mock_client_instance = MockGenaiClient.return_value
        mock_live_connect = AsyncMock() # This will be for the clean response
        mock_client_instance.aio.live.connect = mock_live_connect 
        
        mock_session_clean = AsyncMock() 
        # This is tricky. _ensure_session is called at the start of chat.
        # If we mock _extract_emotions_from_planning, that first session is implicitly used by it.
        # Then _generate_clean_response will use the *same* session.
        # So, we need the connect mock to cover both if we don't reset the session.
        # For simplicity, let's assume _ensure_session provides the same mock_session_clean for the second call
        # or that the session remains open. The test of _ensure_session itself is separate.
        # The first call to connect (for planning) is implicitly handled by agent._extract_emotions_from_planning being mocked.
        # The second call (for clean response) needs this setup:
        mock_live_connect.return_value.__aenter__.return_value = mock_session_clean
        mock_live_connect.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session_clean.send_client_content = AsyncMock()

        async def mock_receive_generator_clean():
            mock_response_part = MagicMock()
            part_text = MagicMock(text=clean_response_text, inline_data=None)
            part_audio = MagicMock(text=None, inline_data=MagicMock(data=self.dummy_audio_data, mime_type="audio/wav"))
            model_turn_mock = MagicMock(parts=[part_text, part_audio])
            server_content_mock = MagicMock(model_turn=model_turn_mock,
                                            output_transcription=MagicMock(text=clean_response_text),
                                            generation_complete=False)
            mock_response_part.server_content = server_content_mock
            yield mock_response_part

            mock_response_complete = MagicMock()
            server_content_complete_mock = MagicMock(model_turn=None, generation_complete=True)
            mock_response_complete.server_content = server_content_complete_mock
            yield mock_response_complete
        
        mock_session_clean.receive.return_value = mock_receive_generator_clean()

        # --- Call agent.chat ---
        batch_input = BatchInput(texts=[TextData(content="User asks for help", source=TextSource.USER)])
        results = [output async for output in agent.chat(batch_input)]

        # --- Assertions ---
        audio_output_result = self._get_audio_output_with_audio(results)
        self.assertIsNotNone(audio_output_result, "No AudioOutput with audio_path found")

        agent._extract_emotions_from_planning.assert_called_once() 
        self.mock_live2d_model.extract_emotion.assert_called_once_with(planning_response_text_with_emoji)
        
        # In dual prompt, display_text comes from the clean response, after _process_emotion_tags_for_display
        # If clean_response_text has no tags/emojis, _process_emotion_tags_for_display should be a no-op on it.
        self.assertEqual(audio_output_result.display_text.text, clean_response_text)
        self.assertEqual(audio_output_result.transcript, clean_response_text)
        
        self.assertEqual(audio_output_result.actions.expressions, expected_actions.expressions)
        self.mock_live2d_model.get_interpolated_expression.assert_called_once_with(0, 0.9)


if __name__ == '__main__':
    unittest.main()
