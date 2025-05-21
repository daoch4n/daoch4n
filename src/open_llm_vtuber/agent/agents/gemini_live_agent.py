import asyncio
import io
import re
import wave
import os
import pathlib
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
from ...utils.emotion_maps import EMOTION_NAME_TO_EMOJI_MAP

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
        self.use_dual_prompt_system = config.use_dual_prompt_system

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
                # Read DAOKO.MD file for character information
                daoko_md_path = pathlib.Path(os.getcwd()) / "DAOKO.MD"
                if daoko_md_path.exists():
                    try:
                        with open(daoko_md_path, "r", encoding="utf-8") as f:
                            daoko_info = f.read()
                        logger.info("Successfully read DAOKO.MD file for character information")

                        # Combine DAOKO.MD content with basic system instruction
                        base_instruction = config.system_instruction or "You are a cheerful and helpful VTuber assistant named Daoko."
                        modified_instruction = f"{base_instruction}\n\n# Character Information\n{daoko_info}"
                    except Exception as e:
                        logger.error(f"Error reading DAOKO.MD file: {e}")
                        modified_instruction = config.system_instruction
                else:
                    logger.warning("DAOKO.MD file not found, using default system instruction")
                    modified_instruction = config.system_instruction

                self.session_config["system_instruction"] = genai_types.Content(
                    parts=[genai_types.Part(text=modified_instruction)]
                )
                logger.info("Added enhanced system instruction to not speak emotion tags")

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

        self.gemini_session = None
        self.live_connect_ctx = None  # Store the context manager to keep it alive
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
                # We need to store this context manager to keep it alive
                self.live_connect_ctx = self.client.aio.live.connect(
                    model=self.model_name,
                    config=session_config_copy
                )

                # Enter the context manager to get the actual session
                # We'll store both the context manager and the session
                self.gemini_session = await self.live_connect_ctx.__aenter__()

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

    async def _extract_emotions_from_planning(self, user_message: str) -> str:
        """
        First step of the two-step approach: Ask the model to plan a response with emotion tags.

        Args:
            user_message: The user's message to respond to

        Returns:
            A response with emotion tags that will be used for facial expressions
        """
        if not self.gemini_session:
            logger.error("No active Gemini session for emotion planning")
            return ""

        try:
            logger.info("Requesting emotion-tagged planning response...")

            # Create a planning prompt that asks for emotion tags
            planning_prompt = (
                f"The user said: \"{user_message}\"\n\n"
                "You are in a planning phase. Plan your response. Indicate the emotional tone by including appropriate emojis directly in the planned text. "
                "To indicate intensity in your plan, repeat the SAME emoji: "
                "Use one emoji for subtle intensity (e.g., 😊 for slight joy). "
                "Use two of the same emoji for medium intensity (e.g., 😊😊 for medium joy). "
                "Use three of the same emoji for high intensity (e.g., 😊😊😊 for strong joy). "
                "Do NOT use bracketed emotion tags like [joy]. Use emojis with repetition for intensity instead. "
                "This planned text with emojis is for internal use to determine facial expressions based on the emoji and its repetition count. The final spoken response will be generated separately and should be natural, without these emojis being literally described or spoken."
            )

            # Send the planning prompt
            await self.gemini_session.send_client_content(
                turns={"role": "user", "parts": [{"text": planning_prompt}]},
                turn_complete=True
            )

            # Process the planning response to extract emotion tags
            planning_response = ""
            async for response in self.gemini_session.receive():
                if response.server_content and response.server_content.model_turn and response.server_content.model_turn.parts:
                    for part in response.server_content.model_turn.parts:
                        if hasattr(part, 'text') and part.text:
                            planning_response += part.text

                if response.server_content and response.server_content.generation_complete:
                    break

            logger.info(f"Received planning response with emotion tags: {planning_response}")
            return planning_response

        except Exception as e:
            logger.error(f"Error during emotion planning phase: {e}")
            return ""

    async def _generate_clean_response(self, user_message: str, planning_response: str) -> AsyncIterator[AudioOutput]:
        """
        Second step of the two-step approach: Generate a clean spoken response without emotion tags.

        Args:
            user_message: The original user message
            planning_response: The planning response with emotion tags

        Returns:
            An async iterator of AudioOutput objects
        """
        if not self.gemini_session:
            logger.error("No active Gemini session for clean response generation")
            yield AudioOutput(
                audio_path=None,
                display_text=DisplayText(text="Error: Could not connect to Gemini."),
                transcript="Error: Could not connect to Gemini.",
                actions=Actions()
            )
            return

        try:
            # Extract emotion tags from planning response for facial expressions
            actions = Actions()
            if self.live2d_model and planning_response:
                expression_tuples = self.live2d_model.extract_emotion(planning_response)
                if expression_tuples:
                    interpolated_expressions = [
                        self.live2d_model.get_interpolated_expression(idx, intensity)
                        for idx, intensity in expression_tuples
                    ]
                    actions.expressions = interpolated_expressions
                    logger.info(f"Extracted expressions: {expression_tuples}")

            # Create a clean prompt that explicitly asks for no emotion tags
            clean_prompt = (
                f"The user said: \"{user_message}\"\n\n"
                "Respond naturally to the user without using or mentioning any emotion tags or square brackets. "
                "Just give a normal conversational response as if you're speaking directly to them."
            )

            # Send the clean prompt
            await self.gemini_session.send_client_content(
                turns={"role": "user", "parts": [{"text": clean_prompt}]},
                turn_complete=True
            )

            # Process the clean response and yield audio outputs
            accumulated_transcript = ""
            async for response in self.gemini_session.receive():
                if self.is_interrupted:
                    logger.info("Gemini Live: Interruption acknowledged, stopping response processing.")
                    break

                if response.server_content and response.server_content.model_turn and response.server_content.model_turn.parts:
                    # Extract all text content from model_turn.parts
                    model_turn_text = self._extract_text_from_parts(response.server_content.model_turn.parts)

                    # Process audio parts
                    for part in response.server_content.model_turn.parts:
                        if part.inline_data and part.inline_data.mime_type.startswith("audio/"):
                            audio_data = part.inline_data.data

                            # Find transcript from various possible locations
                            transcript_text = ""

                            # Try various locations for transcript (same as before)
                            if hasattr(response.server_content, 'output_transcription') and response.server_content.output_transcription:
                                if hasattr(response.server_content.output_transcription, 'text'):
                                    transcript_text = response.server_content.output_transcription.text

                            if not transcript_text and hasattr(response, 'output_transcription') and response.output_transcription:
                                if hasattr(response.output_transcription, 'text'):
                                    transcript_text = response.output_transcription.text

                            if not transcript_text and hasattr(response, 'text') and response.text:
                                transcript_text = response.text

                            if not transcript_text and hasattr(part, 'text') and part.text:
                                transcript_text = part.text

                            if not transcript_text and hasattr(response.server_content.model_turn, 'text') and response.server_content.model_turn.text:
                                transcript_text = response.server_content.model_turn.text

                            if not transcript_text and hasattr(response.server_content, 'transcript') and response.server_content.transcript:
                                transcript_text = response.server_content.transcript

                            if not transcript_text and model_turn_text:
                                transcript_text = model_turn_text

                            # If we found a transcript, use it
                            if transcript_text:
                                # For display, combine the clean transcript with emotion tags from planning
                                # This gives us the best of both worlds - clean speech but emotional display
                                display_transcript = self._process_emotion_tags_for_display(transcript_text)

                                # Add the planning response's emotion tags to the history for future reference
                                if self.history_conf_uid and self.history_history_uid and planning_response:
                                    store_message(
                                        conf_uid=self.history_conf_uid, history_uid=self.history_history_uid,
                                        role="system", content=f"Emotion planning: {planning_response}"
                                    )

                                # Save audio to a temporary file
                                temp_audio_path = f"cache/gemini_live_{id(audio_data)}.wav"
                                with wave.open(temp_audio_path, "wb") as wf:
                                    wf.setnchannels(1)  # Mono
                                    wf.setsampwidth(2)  # 16-bit
                                    wf.setframerate(24000)  # Gemini's output sample rate
                                    wf.writeframes(audio_data)

                                logger.debug(f"Saved audio to {temp_audio_path}")
                                logger.debug(f"Display transcript: '{display_transcript}'")

                                # For display, we'll use the clean transcript but with the actions from the planning phase
                                yield AudioOutput(
                                    audio_path=temp_audio_path,
                                    display_text=DisplayText(text=display_transcript, name=self.character_name, avatar=self.character_avatar),
                                    transcript=display_transcript,
                                    actions=actions
                                )

                                accumulated_transcript += display_transcript

                if response.server_content and response.server_content.generation_complete:
                    logger.info("Gemini indicated generation complete.")
                    if self.history_conf_uid and self.history_history_uid and accumulated_transcript:
                        store_message(
                            conf_uid=self.history_conf_uid, history_uid=self.history_history_uid,
                            role="ai", content=accumulated_transcript,
                            name=self.character_name, avatar=self.character_avatar
                        )
                    break

        except Exception as e:
            logger.error(f"Error during clean response generation: {e}")
            yield AudioOutput(
                audio_path=None,
                display_text=DisplayText(
                    text=f"Error generating response: {str(e)}",
                    name=self.character_name,
                    avatar=self.character_avatar
                ),
                transcript=f"Error generating response: {str(e)}",
                actions=Actions()
            )

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
        if self.gemini_session and self.live_connect_ctx:
            # Schedule closing, don't await here
            asyncio.create_task(self.close_session())
            self.gemini_session = None
            self.live_connect_ctx = None

    async def _send_history_to_gemini(self):
        """Send conversation history to Gemini if available."""
        # Only proceed if we have history and a session
        if self.history_conf_uid and self.history_history_uid and self.gemini_session:
            messages = get_history(self.history_conf_uid, self.history_history_uid)
            if messages:
                # For simplicity, we'll just send the last user message if there is one
                last_user_msg = None
                for msg in reversed(messages):
                    if msg["role"] == "human":
                        last_user_msg = msg["content"]
                        break

                if last_user_msg:
                    logger.debug(f"Sending last user message to Gemini: {last_user_msg}")
                    try:
                        # Send just the last user message to avoid complexity
                        await self.gemini_session.send_client_content(
                            turns={"role": "user", "parts": [{"text": last_user_msg}]},
                            turn_complete=True
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send history to Gemini: {e}")

    async def chat(self, batch_input: BatchInput) -> AsyncIterator[AudioOutput]:
        """
        Chat with the Gemini Live agent using either a single prompt or dual prompt approach.

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
                logger.debug(f"User message: {text_to_send}")

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

        try:
            # Choose between dual prompt system and single prompt approach based on configuration
            if self.use_dual_prompt_system:
                logger.info("Using dual prompt system for emotion tag handling")
                # STEP 1: Get a planning response with emotion tags
                planning_response = await self._extract_emotions_from_planning(text_to_send)

                # STEP 2: Generate a clean spoken response without emotion tags
                async for audio_output in self._generate_clean_response(text_to_send, planning_response):
                    yield audio_output
            else:
                logger.info("Using single prompt approach for emotion tag handling")
                # Use the single prompt approach
                async for audio_output in self._extract_emotions_and_generate_response(text_to_send):
                    yield audio_output

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
                try:
                    await self.close_session()
                except:
                    pass
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

    def _extract_text_from_parts(self, parts) -> str:
        """
        Extract text content from model_turn.parts array.

        Args:
            parts: List of parts from model_turn.parts

        Returns:
            Concatenated text from all text parts
        """
        extracted_text = ""

        for i, part in enumerate(parts):
            # Log the attributes of each part for debugging
            if logger.level == "DEBUG":
                part_attrs = [attr for attr in dir(part) if not attr.startswith('_')]
                logger.debug(f"Part {i} attributes: {part_attrs}")

                # Log the type of the part
                if hasattr(part, 'type'):
                    logger.debug(f"Part {i} type: {part.type}")

                # Log the mime_type if it's inline_data
                if hasattr(part, 'inline_data') and part.inline_data:
                    if hasattr(part.inline_data, 'mime_type'):
                        logger.debug(f"Part {i} mime_type: {part.inline_data.mime_type}")

            # Extract text from text parts
            if hasattr(part, 'text') and part.text:
                extracted_text += part.text
                logger.debug(f"Found text in part {i}: {part.text}")

            # Check for text in other attributes
            if hasattr(part, 'content') and part.content:
                logger.debug(f"Found content in part {i}: {part.content}")

            if hasattr(part, 'transcript') and part.transcript:
                logger.debug(f"Found transcript in part {i}: {part.transcript}")

        return extracted_text

    # Use the centralized map
    EMOTION_TO_EMOJI_MAP = EMOTION_NAME_TO_EMOJI_MAP

    def _process_emotion_tags_for_display(self, text: str) -> str:
        """
        Replaces emotion tags in text with corresponding emojis for display.

        Args:
            text: Text with potential emotion tags.

        Returns:
            Text with emotion tags replaced by emojis.
        """
        if not text:
            return ""

        # Regular expression to match both formats: [emotion] and [emotion:intensity]
        emotion_pattern = r'\[\s*([a-zA-Z_]+)(?:\s*:\s*([0-9]*\.?[0-9]+))?\s*\]'

        def replace_with_emoji(match):
            emotion_name = match.group(1).lower()
            emoji = self.EMOTION_TO_EMOJI_MAP.get(emotion_name, "")
            logger.debug(f"Emotion tag found: '{match.group(0)}', extracted emotion: '{emotion_name}', replaced with emoji: '{emoji}'")
            return emoji

        logger.debug(f"Original text before emotion tag processing: '{text}'")

        # Replace emotion tags with emojis
        processed_text = re.sub(emotion_pattern, replace_with_emoji, text)

        # Clean up any extra spaces (including multiple spaces, newlines, etc.) that might result from removal
        processed_text = re.sub(r'\s+', ' ', processed_text).strip()

        logger.debug(f"Processed text after emotion tag replacement: '{processed_text}'")

        if processed_text != text:
            logger.info("Replaced emotion tags with emojis for display.")

        return processed_text

    async def _extract_emotions_and_generate_response(self, user_message: str) -> AsyncIterator[AudioOutput]:
        """
        Single prompt approach: Generate a response that may include emotion tags,
        extract emotions for facial expressions, and remove tags from displayed text.

        Args:
            user_message: The user's message to respond to

        Returns:
            An async iterator of AudioOutput objects
        """
        if not self.gemini_session:
            logger.error("No active Gemini session for response generation")
            yield AudioOutput(
                audio_path=None,
                display_text=DisplayText(text="Error: Could not connect to Gemini."),
                transcript="Error: Could not connect to Gemini.",
                actions=Actions()
            )
            return

        try:
            # Create a prompt that instructs the LLM to use emojis for emotion indication
            prompt = (
                f"The user said: \"{user_message}\"\n\n"
                "Respond naturally to the user. Indicate your emotional tone by including appropriate emojis directly in your text response. "
                "To indicate intensity, repeat the SAME emoji: "
                "Use one emoji for subtle intensity (e.g., 😊 for slight joy). "
                "Use two of the same emoji for medium intensity (e.g., 😊😊 for medium joy). "
                "Use three of the same emoji for high intensity (e.g., 😊😊😊 for strong joy). "
                "Example: 'That's good news 😊', 'That's great news 😊😊', 'That's fantastic news 😊😊😊'.\n"
                "Do NOT use bracketed emotion tags like [joy]. Use emojis with repetition for intensity instead. "
                "CRITICAL INSTRUCTION: These emojis (and their repetitions) will control facial expressions. They should appear in the text transcript but MUST NOT be spoken aloud by the voice (e.g., for 'I am happy 😊', speak 'I am happy')."
            )

            # Send the prompt
            await self.gemini_session.send_client_content(
                turns={"role": "user", "parts": [{"text": prompt}]},
                turn_complete=True
            )

            # Process the response
            accumulated_transcript = ""
            actions = Actions()

            async for response in self.gemini_session.receive():
                if self.is_interrupted:
                    logger.info("Gemini Live: Interruption acknowledged, stopping response processing.")
                    break

                if response.server_content and response.server_content.model_turn and response.server_content.model_turn.parts:
                    # Extract all text content from model_turn.parts
                    model_turn_text = self._extract_text_from_parts(response.server_content.model_turn.parts)

                    # Extract emotion tags for facial expressions if we have text and a Live2D model
                    if model_turn_text and self.live2d_model and not actions.expressions:
                        expression_tuples = self.live2d_model.extract_emotion(model_turn_text)
                        if expression_tuples:
                            interpolated_expressions = [
                                self.live2d_model.get_interpolated_expression(idx, intensity)
                                for idx, intensity in expression_tuples
                            ]
                            actions.expressions = interpolated_expressions
                            logger.info(f"Extracted expressions: {expression_tuples}")

                    # Process audio parts
                    for part in response.server_content.model_turn.parts:
                        if part.inline_data and part.inline_data.mime_type.startswith("audio/"):
                            audio_data = part.inline_data.data

                            # Find transcript from various possible locations
                            transcript_text = ""

                            # Try various locations for transcript
                            if hasattr(response.server_content, 'output_transcription') and response.server_content.output_transcription:
                                if hasattr(response.server_content.output_transcription, 'text'):
                                    transcript_text = response.server_content.output_transcription.text

                            if not transcript_text and hasattr(response, 'output_transcription') and response.output_transcription:
                                if hasattr(response.output_transcription, 'text'):
                                    transcript_text = response.output_transcription.text

                            if not transcript_text and hasattr(response, 'text') and response.text:
                                transcript_text = response.text

                            if not transcript_text and hasattr(part, 'text') and part.text:
                                transcript_text = part.text

                            if not transcript_text and hasattr(response.server_content.model_turn, 'text') and response.server_content.model_turn.text:
                                transcript_text = response.server_content.model_turn.text

                            if not transcript_text and hasattr(response.server_content, 'transcript') and response.server_content.transcript:
                                transcript_text = response.server_content.transcript

                            if not transcript_text and model_turn_text:
                                transcript_text = model_turn_text

                            # If we found a transcript, use it
                            if transcript_text:
                                # For display, we'll use the transcript but remove emotion tags
                                display_transcript = self._process_emotion_tags_for_display(model_turn_text if model_turn_text else transcript_text)

                                # Save audio to a temporary file
                                temp_audio_path = f"cache/gemini_live_{id(audio_data)}.wav"
                                with wave.open(temp_audio_path, "wb") as wf:
                                    wf.setnchannels(1)  # Mono
                                    wf.setsampwidth(2)  # 16-bit
                                    wf.setframerate(24000)  # Gemini's output sample rate
                                    wf.writeframes(audio_data)

                                logger.debug(f"Saved audio to {temp_audio_path}")
                                logger.debug(f"Display transcript: '{display_transcript}'")

                                yield AudioOutput(
                                    audio_path=temp_audio_path,
                                    display_text=DisplayText(text=display_transcript, name=self.character_name, avatar=self.character_avatar),
                                    transcript=display_transcript,
                                    actions=actions
                                )

                                accumulated_transcript += display_transcript

                if response.server_content and response.server_content.generation_complete:
                    logger.info("Gemini indicated generation complete.")
                    if self.history_conf_uid and self.history_history_uid and accumulated_transcript:
                        store_message(
                            conf_uid=self.history_conf_uid, history_uid=self.history_history_uid,
                            role="ai", content=accumulated_transcript,
                            name=self.character_name, avatar=self.character_avatar
                        )
                    break

        except Exception as e:
            logger.error(f"Error during response generation: {e}")
            yield AudioOutput(
                audio_path=None,
                display_text=DisplayText(
                    text=f"Error generating response: {str(e)}",
                    name=self.character_name,
                    avatar=self.character_avatar
                ),
                transcript=f"Error generating response: {str(e)}",
                actions=Actions()
            )

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

    async def _process_tool_calls(self, tool_calls: List[Any]) -> None:
        """Process tool calls from Gemini.

        Args:
            tool_calls: List of tool calls to process (can be dict or object)
        """
        if not tool_calls or not self.gemini_session:
            return

        for tool_call in tool_calls:
            try:
                # Handle different tool call formats based on SDK version
                if isinstance(tool_call, dict):
                    # Old format: dictionary with tool type as key
                    tool_type = next(iter(tool_call.keys()), None)
                    tool_data = tool_call.get(tool_type, {})
                elif hasattr(tool_call, 'function_call'):
                    # New format: object with function_call attribute
                    tool_type = 'function'
                    tool_data = {
                        'name': tool_call.function_call.name if hasattr(tool_call.function_call, 'name') else '',
                        'args': tool_call.function_call.args if hasattr(tool_call.function_call, 'args') else {}
                    }
                elif hasattr(tool_call, 'code_execution'):
                    # New format: object with code_execution attribute
                    tool_type = 'code_execution'
                    tool_data = tool_call.code_execution
                elif hasattr(tool_call, 'google_search'):
                    # New format: object with google_search attribute
                    tool_type = 'google_search'
                    tool_data = tool_call.google_search
                else:
                    logger.warning(f"Unknown tool call format: {tool_call}")
                    continue

                if tool_type not in self.tool_handlers:
                    logger.warning(f"Unknown tool type: {tool_type}")
                    continue

                # Get the handler for this tool type
                handler = self.tool_handlers[tool_type]

                # Call the handler with the tool call data
                response = await handler(tool_data)

                # Send the response back to Gemini
                # For new SDK, we need to use function_response format
                if hasattr(genai_types, 'FunctionResponse') and tool_type == 'function':
                    # New SDK format for function responses
                    function_response = genai_types.FunctionResponse(
                        name=tool_data.get('name', ''),
                        response=response.get('response', {})
                    )
                    await self.gemini_session.send_tool_response(function_responses=[function_response])
                else:
                    # Fall back to old format
                    await self.gemini_session.send_tool_response({
                        tool_type: response
                    })

                logger.info(f"Sent {tool_type} response to Gemini")
            except Exception as e:
                logger.error(f"Error processing tool call: {e}")
                # Send error response if possible
                if self.gemini_session:
                    try:
                        if hasattr(genai_types, 'FunctionResponse') and tool_type == 'function':
                            # New SDK format for function error responses
                            function_response = genai_types.FunctionResponse(
                                name=tool_data.get('name', ''),
                                error=str(e)
                            )
                            await self.gemini_session.send_tool_response(function_responses=[function_response])
                        else:
                            # Fall back to old format
                            await self.gemini_session.send_tool_response({
                                tool_type: {"error": str(e)}
                            })
                    except Exception as e2:
                        logger.error(f"Error sending tool error response: {e2}")

    async def close_session(self):
        """Close the Gemini Live session."""
        if self.gemini_session and self.live_connect_ctx:
            logger.info("Closing Gemini Live session.")
            try:
                # Properly exit the context manager
                await self.live_connect_ctx.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing Gemini Live session: {e}")
            finally:
                self.gemini_session = None
                self.live_connect_ctx = None
