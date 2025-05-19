import asyncio
import io
import wave
from typing import AsyncIterator, Optional, List, Dict, Any, Literal, Union, Callable
from loguru import logger
import json

import google.genai as genai
from google.genai import types as genai_types  # To avoid conflict with your types.py

from .agent_interface import AgentInterface
from ..output_types import AudioOutput, Actions, DisplayText
from ..input_types import BatchInput, TextData, TextSource
from ...config_manager.agent import GeminiLiveConfig
from ...chat_history_manager import get_history, store_message, get_metadata, update_metadate

# Note: For VAD sensitivity, we use string values directly in the configuration
# Valid values for start_of_speech_sensitivity: START_SENSITIVITY_LOW, START_SENSITIVITY_MEDIUM, START_SENSITIVITY_HIGH
# Valid values for end_of_speech_sensitivity: END_SENSITIVITY_LOW, END_SENSITIVITY_MEDIUM, END_SENSITIVITY_HIGH


class GeminiLiveAgent(AgentInterface):
    """
    Gemini Live Agent that handles direct communication with Gemini's Live API.
    Uses AudioOutput type to provide audio responses with transcripts.
    """

    AGENT_TYPE = "gemini_live_agent"

    def __init__(
        self,
        config: GeminiLiveConfig,
        character_name: str,
        character_avatar: Optional[str] = None,
        live2d_model=None,
    ):
        """
        Initialize the Gemini Live Agent.

        Args:
            config: GeminiLiveConfig - Configuration for the Gemini Live agent
            character_name: str - Name of the character
            character_avatar: Optional[str] - Path to the character's avatar image
            live2d_model: Optional - Live2D model for expression extraction
        """
        # Create the Gemini client with the API key
        self.client = genai.Client(api_key=config.api_key)
        self.model_name = config.model_name
        self.character_name = character_name
        self.character_avatar = character_avatar
        self.live2d_model = live2d_model

        # We're using native Live API mode only (no compatibility mode)

        # Store the system instruction for use in generate_content calls
        self.system_instruction = config.system_instruction if config.system_instruction else ""

        # Configure the session for Gemini Live (full mode)
        try:
            # Try to import the necessary types for full mode
            self.session_config = {
                "response_modalities": ["AUDIO"],  # Prioritize Gemini's direct audio output for low latency
            }

            # Add speech config if the types are available
            if hasattr(genai_types, 'SpeechConfig'):
                self.session_config["speech_config"] = genai_types.SpeechConfig(
                    language_code=config.language_code,
                    voice_config=genai_types.VoiceConfig(
                        prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name=config.voice_name)
                    ) if config.voice_name else None
                )

            # Add transcription configs if available
            self.session_config["output_audio_transcription"] = {}  # Get transcription of what Gemini says
            if config.enable_input_audio_transcription:
                self.session_config["input_audio_transcription"] = {}

            # Add system instruction if provided
            if config.system_instruction and hasattr(genai_types, 'Content'):
                self.session_config["system_instruction"] = genai_types.Content(
                    parts=[genai_types.Part(text=config.system_instruction)]
                )

            # Add tool configurations if enabled
            tools = []

            # Add function calling if enabled
            if config.enable_function_calling and config.function_declarations:
                tools.append({"function_declarations": config.function_declarations})

            # Add code execution if enabled
            if config.enable_code_execution:
                tools.append({"code_execution": {}})

            # Add Google Search if enabled
            if config.enable_google_search:
                tools.append({"google_search": {}})

            # Add tools to session config if any are enabled
            if tools:
                self.session_config["tools"] = tools

            # Context window compression is not supported in the new SDK
            # Skipping context_window_compression configuration

            # VAD Configuration
            if config.disable_automatic_vad:
                # Use manual activity detection
                self.session_config["realtime_input_config"] = {
                    "automatic_activity_detection": {
                        "disabled": True
                    }
                }
                self.using_manual_vad = True
            else:
                # Use automatic VAD with configuration
                auto_vad_config = {"disabled": False}  # Explicitly set disabled to False

                # In the new SDK, sensitivity values need to be proper enum values
                # We'll skip these for now to avoid validation errors
                # Uncomment these if needed and use proper enum values
                # if config.prefix_padding_ms is not None:
                #     auto_vad_config["prefix_padding_ms"] = config.prefix_padding_ms
                # if config.silence_duration_ms is not None:
                #     auto_vad_config["silence_duration_ms"] = config.silence_duration_ms

                if auto_vad_config:
                    self.session_config["realtime_input_config"] = {
                        "automatic_activity_detection": auto_vad_config
                    }
                self.using_manual_vad = False

        except Exception as e:
            # If we encounter any errors setting up the full mode configuration,
            # log a warning and prepare for compatibility mode
            logger.warning(f"Error setting up full Gemini Live configuration: {e}")
            logger.warning("Will attempt to use compatibility mode as fallback")

            # Set up a minimal configuration for compatibility mode
            self.session_config = {}
            self.using_manual_vad = False

        self.gemini_session: Optional[genai.GenerativeModel] = None
        self.current_turn_audio_buffer = bytearray()
        self.is_interrupted = False
        self.active_audio_stream = False  # To track if we need to send audio_stream_end

        # For session resumption and history
        self.history_conf_uid: Optional[str] = None
        self.history_history_uid: Optional[str] = None
        self.session_resumption_handle: Optional[str] = None

        # For tool handling
        self.pending_tool_calls: List[Dict[str, Any]] = []
        self.tool_handlers: Dict[str, Callable] = self._setup_tool_handlers()

        # For token usage tracking
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_tokens: int = 0

        # For VAD control
        self.using_manual_vad: bool = False

    async def _ensure_session(self):
        """Ensure that a Gemini Live session is active and connected."""
        if self.gemini_session is None or getattr(self.gemini_session, '_conn', None) is None or getattr(getattr(self.gemini_session, '_conn', None), 'closed', True):
            logger.info("Gemini Live session not active or closed. Connecting...")
            session_config_copy = self.session_config.copy()

            try:
                # Set up session resumption if needed
                if self.session_resumption_handle:
                    logger.info(f"Attempting to resume Gemini session with handle: {self.session_resumption_handle}")
                    session_config_copy["session_resumption"] = genai_types.SessionResumptionConfig(
                        handle=self.session_resumption_handle
                    )
                else:
                    # If no handle, ensure session_resumption is configured to get one
                    session_config_copy["session_resumption"] = genai_types.SessionResumptionConfig()

                # Connect to the Gemini Live API
                # The Live API uses bidiGenerateContent under the hood
                # Models with 'live' in the name only support this method
                logger.info(f"Connecting to Gemini Live API with model {self.model_name}")
                logger.info(f"Using bidiGenerateContent method via WebSocket connection")

                # Create a context manager for the live connection
                live_connect = self.client.aio.live.connect(
                    model=self.model_name,
                    config=session_config_copy
                )

                # Enter the context manager to get the actual session
                async with live_connect as session:
                    self.gemini_session = session

                logger.info("Connected to Gemini Live API successfully.")
                self.is_interrupted = False  # Reset interruption flag on new session
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to connect to Gemini Live API: {error_msg}")

                # Provide more specific error information
                if "404" in error_msg and "not found" in error_msg:
                    logger.error(f"Model '{self.model_name}' not found. Check if the model name is correct.")
                    logger.error("Live API models should end with '-live-001', '-live-preview' or similar suffix.")
                elif "not supported for" in error_msg and "generateContent" in error_msg:
                    logger.error(f"Model '{self.model_name}' doesn't support the requested method.")
                    logger.error("Live API models only support bidiGenerateContent, not generateContent.")
                elif "API key" in error_msg or "authentication" in error_msg.lower():
                    logger.error("API key issue. Check if your Gemini API key is valid.")

                # Raise the exception to prevent continuing with a broken session
                raise

    def set_memory_from_history(self, conf_uid: str, history_uid: str) -> None:
        """
        Set the agent's memory from a history.

        Args:
            conf_uid: str - Configuration UID
            history_uid: str - History UID
        """
        logger.debug(f"GeminiLiveAgent: Setting memory from history: conf_uid={conf_uid}, history_uid={history_uid}")
        self.history_conf_uid = conf_uid
        self.history_history_uid = history_uid

        # Check metadata for a session resumption handle
        metadata = get_metadata(conf_uid, history_uid)
        agent_type = metadata.get("agent_type")
        resume_id = metadata.get("resume_id")  # For Gemini Live, this would be the session_resumption_handle

        if agent_type and agent_type != self.AGENT_TYPE:
            logger.warning(f"History {history_uid} was for agent {agent_type}, not {self.AGENT_TYPE}. Will start a new Gemini session.")
            self.session_resumption_handle = None
        elif resume_id:
            logger.info(f"Found Gemini session handle {resume_id} in history for {history_uid}.")
            self.session_resumption_handle = resume_id
        else:
            logger.info(f"No Gemini session handle found in history for {history_uid}. Will start a new session.")
            self.session_resumption_handle = None

        # Invalidate current session if it exists, so it reconnects with new history context
        if self.gemini_session:
            # Schedule closing, don't await here
            asyncio.create_task(self.gemini_session.close())
            self.gemini_session = None

    async def _send_history_to_gemini(self):
        """Send conversation history to Gemini if available."""
        # Only proceed if we have history and a session
        if self.history_conf_uid and self.history_history_uid and self.gemini_session:
            messages = get_history(self.history_conf_uid, self.history_history_uid)
            if messages:
                turns = []
                for msg in messages:
                    if msg["role"] == "human":
                        turns.append({"role": "user", "parts": [{"text": msg["content"]}]})
                    elif msg["role"] == "ai":
                        turns.append({"role": "model", "parts": [{"text": msg["content"]}]})
                    # Skipping system messages as Gemini's system_instruction is set at session start
                if turns:
                    logger.debug(f"Sending {len(turns)} history turns to Gemini.")
                    try:
                        # In the new SDK, we use send_client_content to send history
                        await self.gemini_session.send_client_content(turns=turns, turn_complete=False)
                    except Exception as e:
                        logger.warning(f"Failed to send history to Gemini: {e}")

    async def chat(self, batch_input: BatchInput) -> AsyncIterator[AudioOutput]:
        """
        Chat with the Gemini Live agent.

        Args:
            batch_input: BatchInput - User input data

        Returns:
            AsyncIterator[AudioOutput] - Stream of audio outputs
        """
        await self._ensure_session()
        if self.gemini_session is None:  # Should not happen if _ensure_session works
            logger.error("Failed to establish Gemini session.")
            yield AudioOutput(
                audio_path=None,  # Represent as silent audio or error sound
                display_text=DisplayText(text="Error: Could not connect to Gemini."),
                transcript="Error: Could not connect to Gemini.",
                actions=Actions()
            )
            return

        self.is_interrupted = False  # Reset per chat turn

        # Get text input from batch_input
        text_to_send = None
        if batch_input.texts:
            # Concatenate all text parts
            full_text_input = " ".join([text.content for text in batch_input.texts if text.content])
            if full_text_input:
                text_to_send = full_text_input
                logger.debug(f"Sending text to Gemini: {text_to_send}")

                # Store message in history if available
                if self.history_conf_uid and self.history_history_uid:
                    store_message(
                        conf_uid=self.history_conf_uid, history_uid=self.history_history_uid,
                        role="human", content=text_to_send
                    )

        # If no text was provided, use a default message
        if not text_to_send:
            text_to_send = "Hello"
            logger.debug("No text input provided, using default greeting")

        # Use the Live API
        try:
            # If it's a new session or history wasn't sent yet
            if not self.session_resumption_handle or (self.history_conf_uid and self.history_history_uid):
                await self._send_history_to_gemini()

            # Send the text input to Gemini
            if text_to_send:
                # In the new SDK, we use send_client_content to send user messages
                await self.gemini_session.send_client_content(
                    turns={"role": "user", "parts": [{"text": text_to_send}]},
                    turn_complete=False  # Keep turn open for potential audio
                )

            # Mark the user's turn as complete if no audio is expected to follow immediately
            if not self.active_audio_stream and text_to_send:  # if only text was sent
                await self.gemini_session.send_client_content(turn_complete=True)

            # Receive and process responses from Gemini
            accumulated_transcript = ""
            try:
                async for response in self.gemini_session.receive():
                    if self.is_interrupted:
                        logger.info("Gemini Live: Interruption acknowledged, stopping response processing.")
                        break

                    if response.session_resumption_update and response.session_resumption_update.new_handle:
                        self.session_resumption_handle = response.session_resumption_update.new_handle
                        logger.info(f"Received new Gemini session handle: {self.session_resumption_handle}")
                        if self.history_conf_uid and self.history_history_uid:
                            update_metadate(
                                self.history_conf_uid, self.history_history_uid,
                                {"resume_id": self.session_resumption_handle, "agent_type": self.AGENT_TYPE}
                            )

                    if response.server_content:
                        # Handle input audio transcription if available
                        if response.server_content.input_transcription and response.server_content.input_transcription.text:
                            user_transcript = response.server_content.input_transcription.text
                            logger.info(f"User audio transcription: {user_transcript}")

                            # Store the transcription in history if available
                            if self.history_conf_uid and self.history_history_uid and user_transcript:
                                # Check if we already stored this transcript (avoid duplicates)
                                history = get_history(self.history_conf_uid, self.history_history_uid)
                                last_msg = history[-1] if history else None

                                if not last_msg or last_msg.get("role") != "human" or last_msg.get("content") != user_transcript:
                                    store_message(
                                        conf_uid=self.history_conf_uid, history_uid=self.history_history_uid,
                                        role="human", content=user_transcript
                                    )

                        if response.server_content.interrupted:
                            logger.info("Gemini indicated generation was interrupted.")
                            self.is_interrupted = True  # Ensure we break
                            break  # Stop processing this turn

                        # Handle tool calls if any
                        if response.server_content.tool_calls:
                            logger.info(f"Received tool calls: {response.server_content.tool_calls}")
                            # Process tool calls in a separate task to avoid blocking the audio stream
                            asyncio.create_task(self._process_tool_calls(response.server_content.tool_calls))
                            # Yield a notification to the user that a tool is being used
                            yield AudioOutput(
                                audio_path=None,  # No audio for tool notification
                                display_text=DisplayText(
                                    text="Using tools to help answer your question...",
                                    name=self.character_name,
                                    avatar=self.character_avatar
                                ),
                                transcript="Using tools to help answer your question...",
                                actions=Actions()
                            )

                        if response.server_content.model_turn and response.server_content.model_turn.parts:
                            for part in response.server_content.model_turn.parts:
                                if part.inline_data and part.inline_data.mime_type.startswith("audio/"):
                                    audio_data = part.inline_data.data
                                    # Assuming output_audio_transcription is enabled
                                    transcript_text = ""
                                    if response.server_content.output_transcription:
                                        transcript_text = response.server_content.output_transcription.text
                                        accumulated_transcript += transcript_text  # Only append if new
                                        logger.debug(f"Gemini audio transcript part: {transcript_text}")

                                    # Extract expressions from transcript if Live2D model is available
                                    actions = Actions()
                                    if self.live2d_model and transcript_text:
                                        expression_tuples = self.live2d_model.extract_emotion(transcript_text)
                                        if expression_tuples:
                                            interpolated_expressions = [
                                                self.live2d_model.get_interpolated_expression(idx, intensity)
                                                for idx, intensity in expression_tuples
                                            ]
                                            actions.expressions = interpolated_expressions

                                    # Save audio to a temporary file
                                    temp_audio_path = f"cache/gemini_live_{id(audio_data)}.wav"
                                    with wave.open(temp_audio_path, "wb") as wf:
                                        wf.setnchannels(1)  # Mono
                                        wf.setsampwidth(2)  # 16-bit
                                        wf.setframerate(24000)  # Gemini's output sample rate
                                        wf.writeframes(audio_data)

                                    logger.debug(f"Saved audio to {temp_audio_path} with transcript: '{transcript_text}'")
                                    yield AudioOutput(
                                        audio_path=temp_audio_path,
                                        display_text=DisplayText(text=transcript_text, name=self.character_name, avatar=self.character_avatar),
                                        transcript=transcript_text,
                                        actions=actions
                                    )

                            # Track token usage if available
                        if response.server_content.usage_metadata:
                            prompt_tokens = response.server_content.usage_metadata.prompt_token_count or 0
                            completion_tokens = response.server_content.usage_metadata.candidates_token_count or 0
                            total_tokens = response.server_content.usage_metadata.total_token_count or 0

                            self.total_prompt_tokens += prompt_tokens
                            self.total_completion_tokens += completion_tokens
                            self.total_tokens += total_tokens

                            logger.info(f"Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
                            logger.info(f"Cumulative token usage - Prompt: {self.total_prompt_tokens}, Completion: {self.total_completion_tokens}, Total: {self.total_tokens}")

                            # Store token usage in metadata if history is enabled
                            if self.history_conf_uid and self.history_history_uid:
                                update_metadate(
                                    self.history_conf_uid, self.history_history_uid,
                                    {
                                        "token_usage": {
                                            "prompt_tokens": self.total_prompt_tokens,
                                            "completion_tokens": self.total_completion_tokens,
                                            "total_tokens": self.total_tokens
                                        }
                                    }
                                )

                        if response.server_content.generation_complete:
                            logger.info("Gemini indicated generation complete.")
                            if self.history_conf_uid and self.history_history_uid and accumulated_transcript:
                                store_message(
                                    conf_uid=self.history_conf_uid, history_uid=self.history_history_uid,
                                    role="ai", content=accumulated_transcript,
                                    name=self.character_name, avatar=self.character_avatar
                                )
                            break  # End of this turn's response

                    if response.go_away:
                        logger.warning(f"Gemini session go_away received: {response.go_away.message}. Time left: {response.go_away.time_left}")
                        # Store the time left for potential reconnection before timeout
                        time_left_seconds = response.go_away.time_left.seconds if response.go_away.time_left else 0

                        # If we have enough time left (more than 10 seconds), try to reconnect
                        if time_left_seconds > 10 and self.session_resumption_handle:
                            logger.info(f"Will attempt to reconnect with session handle before timeout ({time_left_seconds}s left)")
                            if self.gemini_session:
                                await self.gemini_session.close()
                            self.gemini_session = None
                            # Force reconnection on next interaction
                            await self._ensure_session()
                        else:
                            # Not enough time or no resumption handle, just close
                            if self.gemini_session:
                                await self.gemini_session.close()
                            self.gemini_session = None
                        break
            except Exception as e:
                logger.error(f"Error during Gemini Live chat: {e}")
                # Return an error message to the user
                yield AudioOutput(
                    audio_path=None,
                    display_text=DisplayText(
                        text=f"Error communicating with Gemini: {str(e)}",
                        name=self.character_name,
                        avatar=self.character_avatar
                    ),
                    transcript=f"Error communicating with Gemini: {str(e)}",
                    actions=Actions()
                )
            finally:
                logger.debug("Exiting Gemini chat loop for this turn.")
                # Ensure active audio stream is properly ended if not interrupted by user's speech
                if self.active_audio_stream and not self.is_interrupted:
                    if self.gemini_session and not getattr(self.gemini_session, '_conn', None) is None and not getattr(getattr(self.gemini_session, '_conn', None), 'closed', True):
                        try:
                            await self.gemini_session.send_realtime_input(audio_stream_end=True)
                        except Exception as e_stream_end:
                            logger.warning(f"Could not send audio_stream_end: {e_stream_end}")
                    self.active_audio_stream = False
        except Exception as e:
            logger.error(f"Error in Gemini Live chat: {e}")
            # Return an error message to the user
            yield AudioOutput(
                audio_path=None,
                display_text=DisplayText(
                    text=f"Error: {str(e)}",
                    name=self.character_name,
                    avatar=self.character_avatar
                ),
                transcript=f"Error: {str(e)}",
                actions=Actions()
            )

    async def stream_audio_chunk(self, audio_chunk: bytes):
        """
        Stream an audio chunk to Gemini Live.

        Args:
            audio_chunk: bytes - Raw audio data (PCM 16-bit, 16kHz)
        """
        # Stream the audio to Gemini Live
        await self._ensure_session()
        if self.gemini_session and not self.is_interrupted:
            try:
                logger.debug(f"Sending audio chunk to Gemini: {len(audio_chunk)} bytes")

                # If using manual VAD and this is the first chunk, send activity_start
                if self.using_manual_vad and not self.active_audio_stream:
                    logger.debug("Sending manual activity_start signal")
                    await self.gemini_session.send_realtime_input(activity_start=True)

                # Send the audio chunk
                await self.gemini_session.send_realtime_input(
                    audio={"data": audio_chunk, "mime_type": "audio/pcm;rate=16000"}
                )
                self.active_audio_stream = True
            except Exception as e:
                logger.error(f"Error sending audio chunk to Gemini: {e}")
                # Store the audio chunk in case we need it later
                self.current_turn_audio_buffer.extend(audio_chunk)
                self.active_audio_stream = True
                # Potentially close session or mark as needing reconnection
                if self.gemini_session:
                    try:
                        await self.gemini_session.close()
                    except:
                        pass
                self.gemini_session = None
        else:
            logger.warning("Gemini session not available or interrupted, cannot stream audio chunk.")

    async def end_audio_stream(self):
        """Signal the end of the audio stream to Gemini Live."""
        # Reset the audio buffer
        self.current_turn_audio_buffer = bytearray()

        # Signal the end of the audio stream
        if self.gemini_session and self.active_audio_stream and not self.is_interrupted:
            try:
                logger.debug("Sending audio_stream_end to Gemini.")

                # If using manual VAD, send activity_end before audio_stream_end
                if self.using_manual_vad:
                    logger.debug("Sending manual activity_end signal")
                    await self.gemini_session.send_realtime_input(activity_end=True)

                # Send audio_stream_end
                await self.gemini_session.send_realtime_input(audio_stream_end=True)

                # Also mark the user's turn as complete after audio
                await self.gemini_session.send_client_content(turn_complete=True)
            except Exception as e:
                logger.error(f"Error sending audio_stream_end to Gemini: {e}")
            finally:
                self.active_audio_stream = False
        else:
            # If there was no active audio stream, but we had text input earlier,
            # we might need to complete the turn.
            if self.gemini_session and not self.is_interrupted:
                try:
                    await self.gemini_session.send_client_content(turn_complete=True)
                    logger.debug("Sent turn_complete after non-audio input.")
                except Exception as e:
                    logger.warning(f"Failed to send turn_complete: {e}")

    def handle_interrupt(self, heard_response: str) -> None:
        """
        Handle an interruption signal.

        Args:
            heard_response: str - The response heard so far
        """
        logger.info("GeminiLiveAgent: Interruption signal received.")
        self.is_interrupted = True
        # Gemini handles its own generation cancellation when it detects user speech.
        # We mainly use this flag to stop processing further responses from Gemini for the current turn.
        # Store the heard response if history is enabled
        if self.history_conf_uid and self.history_history_uid and heard_response:
            store_message(
                conf_uid=self.history_conf_uid, history_uid=self.history_history_uid,
                role="ai", content=heard_response + "...",  # Mark as partial
                name=self.character_name, avatar=self.character_avatar
            )
            store_message(
                conf_uid=self.history_conf_uid, history_uid=self.history_history_uid,
                role="system", content="[Interrupted by user]"
            )

    def _setup_tool_handlers(self) -> Dict[str, Callable]:
        """Set up handlers for different tool types."""
        return {
            "function": self._handle_function_call,
            "code_execution": self._handle_code_execution,
            "google_search": self._handle_google_search
        }

    async def _handle_function_call(self, function_call: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a function call from Gemini.

        Args:
            function_call: Dict containing function call details

        Returns:
            Dict with function call response
        """
        function_name = function_call.get("name", "")
        function_args = function_call.get("args", {})

        logger.info(f"Function call received: {function_name} with args: {function_args}")

        # This is where you would implement actual function calling logic
        # For now, we'll return a simple response
        response = {
            "name": function_name,
            "response": {
                "content": f"Function {function_name} was called with arguments {json.dumps(function_args)}"
            }
        }

        return response

    async def _handle_code_execution(self, code_execution: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a code execution request from Gemini.

        Args:
            code_execution: Dict containing code execution details

        Returns:
            Dict with code execution response
        """
        code = code_execution.get("code", "")
        language = code_execution.get("language", "python")

        logger.info(f"Code execution requested in {language}: {code[:100]}...")

        # This is where you would implement actual code execution logic
        # For now, we'll return a simple response
        return {
            "output": f"Code execution for {language} is not implemented yet.",
            "error": None
        }

    async def _handle_google_search(self, search_query: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a Google Search request from Gemini.

        Args:
            search_query: Dict containing search query details

        Returns:
            Dict with search results
        """
        query = search_query.get("query", "")

        logger.info(f"Google Search requested for: {query}")

        # This is where you would implement actual Google Search logic
        # For now, we'll return a simple response
        return {
            "results": [
                {
                    "title": f"Search result for {query}",
                    "url": f"https://example.com/search?q={query}",
                    "snippet": f"This is a placeholder result for the search query: {query}"
                }
            ]
        }

    async def _process_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> None:
        """Process tool calls from Gemini.

        Args:
            tool_calls: List of tool calls to process
        """
        if not tool_calls or not self.gemini_session:
            return

        for tool_call in tool_calls:
            tool_type = next(iter(tool_call.keys()), None)
            if not tool_type or tool_type not in self.tool_handlers:
                logger.warning(f"Unknown tool type: {tool_type}")
                continue

            try:
                # Get the handler for this tool type
                handler = self.tool_handlers[tool_type]

                # Call the handler with the tool call data
                response = await handler(tool_call[tool_type])

                # Send the response back to Gemini
                await self.gemini_session.send_tool_response({
                    tool_type: response
                })

                logger.info(f"Sent {tool_type} response to Gemini")
            except Exception as e:
                logger.error(f"Error processing {tool_type} call: {e}")
                # Send error response if possible
                if self.gemini_session:
                    try:
                        await self.gemini_session.send_tool_response({
                            tool_type: {"error": str(e)}
                        })
                    except Exception as e2:
                        logger.error(f"Error sending tool error response: {e2}")

    async def close_session(self):
        """Close the Gemini Live session."""
        if self.gemini_session:
            logger.info("Closing Gemini Live session.")
            try:
                await self.gemini_session.close()
            except Exception as e:
                logger.warning(f"Error closing Gemini Live session: {e}")
            finally:
                self.gemini_session = None
