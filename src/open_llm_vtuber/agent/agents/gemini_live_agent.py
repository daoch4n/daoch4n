import asyncio
import io
import wave
from typing import AsyncIterator, Optional, List, Dict, Any, Literal
from loguru import logger
import numpy as np

from google import genai
from google.genai import types as genai_types  # To avoid conflict with your types.py

from .agent_interface import AgentInterface
from ..output_types import AudioOutput, Actions, DisplayText
from ..input_types import BatchInput, TextData, TextSource
from ...config_manager.agent import GeminiLiveConfig
from ...chat_history_manager import get_history, store_message, get_metadata, update_metadate

# Define a mapping from string config to genai_types
START_SENSITIVITY_MAP = {
    "START_SENSITIVITY_LOW": genai_types.StartSensitivity.START_SENSITIVITY_LOW,
    "START_SENSITIVITY_MEDIUM": genai_types.StartSensitivity.START_SENSITIVITY_MEDIUM,
    "START_SENSITIVITY_HIGH": genai_types.StartSensitivity.START_SENSITIVITY_HIGH,
}
END_SENSITIVITY_MAP = {
    "END_SENSITIVITY_LOW": genai_types.EndSensitivity.END_SENSITIVITY_LOW,
    "END_SENSITIVITY_MEDIUM": genai_types.EndSensitivity.END_SENSITIVITY_MEDIUM,
    "END_SENSITIVITY_HIGH": genai_types.EndSensitivity.END_SENSITIVITY_HIGH,
}


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
        self.client = genai.Client(api_key=config.api_key)
        self.model_name = config.model_name
        self.character_name = character_name
        self.character_avatar = character_avatar
        self.live2d_model = live2d_model

        # Configure the session for Gemini Live
        self.session_config = {
            "response_modalities": ["AUDIO"],  # Prioritize Gemini's direct audio output for low latency
            "speech_config": genai_types.SpeechConfig(
                language_code=config.language_code,
                voice_config=genai_types.VoiceConfig(
                    prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name=config.voice_name)
                ) if config.voice_name else None
            ),
            "output_audio_transcription": {}  # Get transcription of what Gemini says
        }
        
        # Add system instruction if provided
        if config.system_instruction:
            self.session_config["system_instruction"] = genai_types.Content(
                parts=[genai_types.Part(text=config.system_instruction)]
            )

        # VAD Configuration
        auto_vad_config = {}
        if config.start_of_speech_sensitivity:
            auto_vad_config["start_of_speech_sensitivity"] = START_SENSITIVITY_MAP.get(
                config.start_of_speech_sensitivity
            )
        if config.end_of_speech_sensitivity:
            auto_vad_config["end_of_speech_sensitivity"] = END_SENSITIVITY_MAP.get(
                config.end_of_speech_sensitivity
            )
        if config.prefix_padding_ms is not None:
            auto_vad_config["prefix_padding_ms"] = config.prefix_padding_ms
        if config.silence_duration_ms is not None:
            auto_vad_config["silence_duration_ms"] = config.silence_duration_ms

        if auto_vad_config:
            self.session_config["realtime_input_config"] = {
                "automatic_activity_detection": auto_vad_config
            }

        self.gemini_session: Optional[genai.LiveSession] = None
        self.current_turn_audio_buffer = bytearray()
        self.is_interrupted = False
        self.active_audio_stream = False  # To track if we need to send audio_stream_end

        # For session resumption and history
        self.history_conf_uid: Optional[str] = None
        self.history_history_uid: Optional[str] = None
        self.session_resumption_handle: Optional[str] = None

    async def _ensure_session(self):
        """Ensure that a Gemini Live session is active and connected."""
        if self.gemini_session is None or self.gemini_session._conn is None or self.gemini_session._conn.closed:  # type: ignore
            logger.info("Gemini Live session not active or closed. Connecting...")
            session_config_copy = self.session_config.copy()

            if self.session_resumption_handle:
                logger.info(f"Attempting to resume Gemini session with handle: {self.session_resumption_handle}")
                session_config_copy["session_resumption"] = genai_types.SessionResumptionConfig(
                    handle=self.session_resumption_handle
                )
            else:  # If no handle, ensure session_resumption is configured to get one
                session_config_copy["session_resumption"] = genai_types.SessionResumptionConfig()

            self.gemini_session = await self.client.aio.live.connect(
                model=self.model_name,
                config=session_config_copy
            )
            logger.info("Connected to Gemini Live.")
            self.is_interrupted = False  # Reset interruption flag on new session

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
                    await self.gemini_session.send_client_content(turns=turns, turn_complete=False)

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

        # If it's a new session or history wasn't sent yet
        if not self.session_resumption_handle or (self.history_conf_uid and self.history_history_uid):
            await self._send_history_to_gemini()

        # Handle text input first (if any)
        # For Gemini Live, audio is the primary input method.
        # Text input can be used to kick off the conversation or send explicit commands.
        text_to_send = None
        if batch_input.texts:
            # Concatenate all text parts. Gemini Live expects a single text input per turn.
            full_text_input = " ".join([text.content for text in batch_input.texts if text.content])
            if full_text_input:
                text_to_send = full_text_input
                logger.debug(f"Sending text to Gemini: {text_to_send}")
                await self.gemini_session.send_client_content(
                    turns={"role": "user", "parts": [{"text": text_to_send}]},
                    turn_complete=False  # Keep turn open for potential audio
                )
                if self.history_conf_uid and self.history_history_uid:
                    store_message(
                        conf_uid=self.history_conf_uid, history_uid=self.history_history_uid,
                        role="human", content=text_to_send
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
                    if response.server_content.interrupted:
                        logger.info("Gemini indicated generation was interrupted.")
                        self.is_interrupted = True  # Ensure we break
                        break  # Stop processing this turn

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
                    if self.gemini_session:
                        await self.gemini_session.close()
                    self.gemini_session = None
                    break
        except Exception as e:
            logger.error(f"Error during Gemini Live chat: {e}")
            yield AudioOutput(
                audio_path=None,
                display_text=DisplayText(text=f"Error: {str(e)}", name=self.character_name, avatar=self.character_avatar),
                transcript=f"Error: {str(e)}",
                actions=Actions()
            )
        finally:
            logger.debug("Exiting Gemini chat loop for this turn.")
            # Ensure active audio stream is properly ended if not interrupted by user's speech
            if self.active_audio_stream and not self.is_interrupted:
                if self.gemini_session and not self.gemini_session._conn.closed:  # type: ignore
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
        await self._ensure_session()
        if self.gemini_session and not self.is_interrupted:
            try:
                logger.debug(f"Sending audio chunk to Gemini: {len(audio_chunk)} bytes")
                await self.gemini_session.send_realtime_input(
                    audio=genai_types.Blob(data=audio_chunk, mime_type="audio/pcm;rate=16000")
                )
                self.active_audio_stream = True
            except Exception as e:
                logger.error(f"Error sending audio chunk to Gemini: {e}")
                # Potentially close session or mark as needing reconnection
                if self.gemini_session:
                    await self.gemini_session.close()
                self.gemini_session = None
        else:
            logger.warning("Gemini session not available or interrupted, cannot stream audio chunk.")

    async def end_audio_stream(self):
        """Signal the end of the audio stream to Gemini Live."""
        if self.gemini_session and self.active_audio_stream and not self.is_interrupted:
            try:
                logger.debug("Sending audio_stream_end to Gemini.")
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

    async def close_session(self):
        """Close the Gemini Live session."""
        if self.gemini_session:
            logger.info("Closing Gemini Live session.")
            await self.gemini_session.close()
            self.gemini_session = None
