Okay, this is an exciting integration! Gemini Live Mode is designed for exactly the kind of low-latency, interactive experience your Open LLM VTuber app aims to provide.

Here's a detailed implementation plan, breaking down the integration into manageable phases.

**Assumptions:**

*   You have a Google Cloud Project set up and the Gemini API enabled.
*   You have an API key for Gemini.
*   You are comfortable with Python `asyncio` as your backend is FastAPI and Gemini Live SDK is async.
*   Your primary goal is to use Gemini for both understanding user speech (ASR) and generating responses (LLM + TTS directly from Gemini).

**Core Idea:**

We will introduce a new "Gemini Live Agent" that conforms to your existing `AgentInterface`. This agent will manage the WebSocket connection to the Gemini Live API. When this agent is active, it will largely bypass your existing ASR and TTS modules, using Gemini's capabilities directly.

---

**Phase 0: Prerequisites & Configuration**

1.  **Install Gemini SDK:**
    ```bash
    pip install google-generativeai
    ```

2.  **API Key Management:**
    *   Decide how to store the Gemini API key securely (e.g., environment variable, `.env` file).
    *   Ensure your application can load this key.

3.  **Update Configuration (`conf.yaml` and `ConfigManager`):**
    *   **`open_llm_vtuber/config_manager/agent.py`:**
        *   Add a new Pydantic model for Gemini Live Agent settings:
            ```python
            class GeminiLiveConfig(I18nMixin, BaseModel):
                api_key: str = Field(..., alias="api_key")
                model_name: str = Field("gemini-2.0-flash-live-001", alias="model_name") # Or other Live API compatible models
                language_code: str = Field("en-US", alias="language_code") # e.g., "en-US", "ja-JP"
                voice_name: Optional[str] = Field("Kore", alias="voice_name") # e.g., Puck, Charon, Kore etc.
                system_instruction: Optional[str] = Field(None, alias="system_instruction") # For persona
                # Add VAD settings if you want to customize Gemini's VAD
                start_of_speech_sensitivity: Optional[Literal["START_SENSITIVITY_UNSPECIFIED", "START_SENSITIVITY_LOW", "START_SENSITIVITY_MEDIUM", "START_SENSITIVITY_HIGH"]] = Field(None, alias="start_of_speech_sensitivity")
                end_of_speech_sensitivity: Optional[Literal["END_SENSITIVITY_UNSPECIFIED", "END_SENSITIVITY_LOW", "END_SENSITIVITY_MEDIUM", "END_SENSITIVITY_HIGH"]] = Field(None, alias="end_of_speech_sensitivity")
                prefix_padding_ms: Optional[int] = Field(None, alias="prefix_padding_ms")
                silence_duration_ms: Optional[int] = Field(None, alias="silence_duration_ms")
                # Add other relevant Gemini Live settings as needed (e.g., session resumption, compression)

                DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
                    "api_key": Description(en="Gemini API Key", zh="Gemini API 密钥"),
                    "model_name": Description(en="Gemini Live Model Name", zh="Gemini Live 模型名称"),
                    "language_code": Description(en="Language code for speech (e.g., en-US, ja-JP)", zh="语音语言代码 (例如 en-US, ja-JP)"),
                    "voice_name": Description(en="Gemini voice name (e.g., Puck, Kore)", zh="Gemini 语音名称 (例如 Puck, Kore)"),
                    "system_instruction": Description(en="System instruction/persona for Gemini", zh="给 Gemini 的系统指令/角色设定"),
                    "start_of_speech_sensitivity": Description(en="VAD start of speech sensitivity", zh="VAD 语音开始敏感度"),
                    # ... other descriptions
                }
            ```
        *   Add `gemini_live_agent: Optional[GeminiLiveConfig]` to `AgentSettings`.
        *   Add `"gemini_live_agent"` to `Literal` in `conversation_agent_choice` of `AgentConfig`.
    *   **`conf.yaml` (Example Snippet):**
        ```yaml
        character_config:
          # ... existing character configs
          agent_config:
            conversation_agent_choice: "gemini_live_agent" # Or "basic_memory_agent"
            agent_settings:
              basic_memory_agent: # ...
              gemini_live_agent:
                api_key: "${GEMINI_API_KEY}" # Load from env
                model_name: "gemini-2.0-flash-live-001"
                language_code: "en-US"
                voice_name: "Kore"
                system_instruction: "You are a cheerful and helpful VTuber assistant named Shizuku. Respond concisely."
                # Optional VAD settings:
                # start_of_speech_sensitivity: "START_SENSITIVITY_MEDIUM"
                # end_of_speech_sensitivity: "END_SENSITIVITY_MEDIUM"
                # silence_duration_ms: 800
            llm_configs: # ... (may not be used by Gemini Live agent directly but keep for other agents)
        ```
    *   Update `read_yaml` and `validate_config` in `open_llm_vtuber/config_manager/utils.py` to handle the new configuration structure if necessary (Pydantic should handle most of it).

---

**Phase 1: Implement the `GeminiLiveAgent`**

1.  **Create `open_llm_vtuber/agent/agents/gemini_live_agent.py`:**
    ```python
    import asyncio
    import wave
    import io
    from typing import AsyncIterator, Optional, List, Dict, Any
    from google import genai
    from google.genai import types as genai_types # To avoid conflict with your types.py
    from loguru import logger
    import numpy as np

    from .agent_interface import AgentInterface
    from ..output_types import AudioOutput, Actions, DisplayText # If Gemini provides audio directly
    # from ..output_types import SentenceOutput # If you want to process Gemini's text output through your existing TTS pipeline (less ideal for Live Mode)
    from ..input_types import BatchInput, TextData, TextSource
    from ...config_manager.agent import GeminiLiveConfig
    from ...chat_history_manager import get_history, store_message, get_metadata, update_metadate # For session resumption

    # Define a mapping from your string config to genai_types
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
        AGENT_TYPE = "gemini_live_agent"

        def __init__(self, config: GeminiLiveConfig, character_name: str, character_avatar: Optional[str] = None):
            self.client = genai.Client(api_key=config.api_key)
            self.model_name = config.model_name
            self.character_name = character_name
            self.character_avatar = character_avatar

            self.session_config = {
                "response_modalities": ["AUDIO"], # Prioritize Gemini's direct audio output for low latency
                # "response_modalities": ["TEXT"], # Alternative: Get text and use your TTS
                "speech_config": genai_types.SpeechConfig(
                    language_code=config.language_code,
                    voice_config=genai_types.VoiceConfig(
                        prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name=config.voice_name)
                    ) if config.voice_name else None
                ),
                "output_audio_transcription": {} # Get transcription of what Gemini says
            }
            if config.system_instruction:
                self.session_config["system_instruction"] = genai_types.Content(
                    parts=[genai_types.Part(text=config.system_instruction)]
                )

            # VAD Configuration
            auto_vad_config = {}
            if config.start_of_speech_sensitivity:
                auto_vad_config["start_of_speech_sensitivity"] = START_SENSITIVITY_MAP.get(config.start_of_speech_sensitivity)
            if config.end_of_speech_sensitivity:
                auto_vad_config["end_of_speech_sensitivity"] = END_SENSITIVITY_MAP.get(config.end_of_speech_sensitivity)
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
            self.active_audio_stream = False # To track if we need to send audio_stream_end

            self.history_conf_uid: Optional[str] = None
            self.history_history_uid: Optional[str] = None
            self.session_resumption_handle: Optional[str] = None


        async def _ensure_session(self):
            if self.gemini_session is None or self.gemini_session._conn is None or self.gemini_session._conn.closed: # type: ignore
                logger.info("Gemini Live session not active or closed. Connecting...")
                session_config_copy = self.session_config.copy()

                if self.session_resumption_handle:
                    logger.info(f"Attempting to resume Gemini session with handle: {self.session_resumption_handle}")
                    session_config_copy["session_resumption"] = genai_types.SessionResumptionConfig(
                        handle=self.session_resumption_handle
                    )
                else: # If no handle, ensure session_resumption is configured to get one
                    session_config_copy["session_resumption"] = genai_types.SessionResumptionConfig()


                self.gemini_session = await self.client.aio.live.connect(
                    model=self.model_name,
                    config=session_config_copy
                )
                logger.info("Connected to Gemini Live.")
                self.is_interrupted = False # Reset interruption flag on new session

        def set_memory_from_history(self, conf_uid: str, history_uid: str) -> None:
            logger.debug(f"GeminiLiveAgent: Setting memory from history: conf_uid={conf_uid}, history_uid={history_uid}")
            self.history_conf_uid = conf_uid
            self.history_history_uid = history_uid

            # Check metadata for a session resumption handle
            metadata = get_metadata(conf_uid, history_uid)
            agent_type = metadata.get("agent_type")
            resume_id = metadata.get("resume_id") # For Gemini Live, this would be the session_resumption_handle

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
            await self._ensure_session()
            if self.gemini_session is None: # Should not happen if _ensure_session works
                logger.error("Failed to establish Gemini session.")
                yield AudioOutput(
                    audio_path=None, # Represent as silent audio or error sound
                    display_text=DisplayText(text="Error: Could not connect to Gemini."),
                    transcript="Error: Could not connect to Gemini.",
                    actions=Actions()
                )
                return

            self.is_interrupted = False # Reset per chat turn

            # If it's a new session or history wasn't sent yet
            if not self.session_resumption_handle or (self.history_conf_uid and self.history_history_uid): # Heuristic: if resuming, assume history is part of session
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
                        turn_complete=False # Keep turn open for potential audio
                    )
                    if self.history_conf_uid and self.history_history_uid:
                         store_message(
                            conf_uid=self.history_conf_uid, history_uid=self.history_history_uid,
                            role="human", content=text_to_send
                        )


            # Handle audio input (this is the primary mode for Gemini Live)
            # Your WebSocketHandler will send audio chunks here as part of `BatchInput.texts` (hacky)
            # or ideally, BatchInput would have a dedicated audio field.
            # For now, let's assume audio comes in as a special BatchInput or is managed by WebSocketHandler
            # This part needs to be integrated with how your WebSocketHandler._handle_audio_data and _handle_conversation_trigger work.
            # The `send_realtime_input` is what Gemini Live expects for streaming audio.

            # ---- This part is conceptual and needs integration with your audio chunking ----
            # if batch_input.audio_chunk: # Assuming BatchInput gets an audio_chunk field
            #     await self.gemini_session.send_realtime_input(
            #         audio=genai_types.Blob(data=batch_input.audio_chunk, mime_type="audio/pcm;rate=16000")
            #     )
            #     self.active_audio_stream = True
            # elif self.active_audio_stream: # If no audio chunk but stream was active, mark end
            #     await self.gemini_session.send_realtime_input(audio_stream_end=True)
            #     self.active_audio_stream = False
            # ---- End conceptual ----

            # Mark the user's turn as complete if no audio is expected to follow immediately
            if not self.active_audio_stream and text_to_send : # if only text was sent
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
                            self.is_interrupted = True # Ensure we break
                            break # Stop processing this turn

                        if response.server_content.model_turn and response.server_content.model_turn.parts:
                            for part in response.server_content.model_turn.parts:
                                if part.inline_data and part.inline_data.mime_type.startswith("audio/"):
                                    audio_data = part.inline_data.data
                                    # Assuming output_audio_transcription is enabled
                                    transcript_text = ""
                                    if response.server_content.output_transcription:
                                        transcript_text = response.server_content.output_transcription.text
                                        accumulated_transcript += transcript_text # Only append if new
                                        logger.debug(f"Gemini audio transcript part: {transcript_text}")

                                    # Save audio to a temporary file (your cache mechanism)
                                    # For simplicity, directly yield bytes. Your app needs to handle this.
                                    # In a real scenario, you'd save to a file and pass the path.
                                    # Here, we'll use a BytesIO object and then convert to a path-like string if necessary.
                                    # Or, adapt AudioOutput to handle raw bytes.
                                    temp_audio_file = io.BytesIO(audio_data)
                                    # This is a placeholder; you'll need a proper path for your existing system.
                                    # For now, let's assume AudioOutput can take raw bytes or your `prepare_audio_payload` handles it.
                                    # We'll make AudioOutput's audio_path accept bytes too.
                                    logger.debug(f"Yielding audio data ({len(audio_data)} bytes) with transcript: '{transcript_text}'")
                                    yield AudioOutput(
                                        audio_path=audio_data, # HACK: Sending bytes, adapt consumer
                                        display_text=DisplayText(text=transcript_text, name=self.character_name, avatar=self.character_avatar),
                                        transcript=transcript_text,
                                        actions=Actions() # TODO: Extract actions if Gemini can be prompted for them
                                    )

                        if response.server_content.generation_complete:
                            logger.info("Gemini indicated generation complete.")
                            if self.history_conf_uid and self.history_history_uid and accumulated_transcript:
                                store_message(
                                    conf_uid=self.history_conf_uid, history_uid=self.history_history_uid,
                                    role="ai", content=accumulated_transcript,
                                    name=self.character_name, avatar=self.character_avatar
                                )
                            break # End of this turn's response

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
                     if self.gemini_session and not self.gemini_session._conn.closed: #type: ignore
                        try:
                            await self.gemini_session.send_realtime_input(audio_stream_end=True)
                        except Exception as e_stream_end:
                            logger.warning(f"Could not send audio_stream_end: {e_stream_end}")
                     self.active_audio_stream = False


        # This new method will be called by WebSocketHandler when it receives raw audio chunks
        async def stream_audio_chunk(self, audio_chunk: bytes):
            await self._ensure_session()
            if self.gemini_session and not self.is_interrupted:
                try:
                    logger.trace(f"Sending audio chunk to Gemini: {len(audio_chunk)} bytes")
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

        # This new method will be called by WebSocketHandler when mic audio ends
        async def end_audio_stream(self):
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
            logger.info("GeminiLiveAgent: Interruption signal received.")
            self.is_interrupted = True
            # Gemini handles its own generation cancellation when it detects user speech.
            # We mainly use this flag to stop processing further responses from Gemini for the current turn.
            # Store the heard response if history is enabled
            if self.history_conf_uid and self.history_history_uid and heard_response:
                store_message(
                    conf_uid=self.history_conf_uid, history_uid=self.history_history_uid,
                    role="ai", content=heard_response + "...", # Mark as partial
                    name=self.character_name, avatar=self.character_avatar
                )
                store_message(
                    conf_uid=self.history_conf_uid, history_uid=self.history_history_uid,
                    role="system", content="[Interrupted by user]"
                )

        async def close_session(self):
            if self.gemini_session:
                logger.info("Closing Gemini Live session.")
                await self.gemini_session.close()
                self.gemini_session = None
    ```

2.  **Update `open_llm_vtuber/agent/agent_factory.py`:**
    ```python
    # ... existing imports
    from .agents.gemini_live_agent import GeminiLiveAgent # Add this
    from ...config_manager.agent import GeminiLiveConfig # Add this

    class AgentFactory:
        @staticmethod
        def create_agent(
            conversation_agent_choice: str,
            agent_settings: dict,
            llm_configs: dict, # May not be used by GeminiLiveAgent
            system_prompt: str, # For BasicMemoryAgent, GeminiLiveAgent gets it from its own config
            live2d_model=None,
            tts_preprocessor_config=None,
            character_name: Optional[str] = "AI", # Pass character name
            character_avatar: Optional[str] = None, # Pass character avatar
            **kwargs,
        ) -> AgentInterface: # Ensure AgentInterface is imported
            # ... existing agent creations

            elif conversation_agent_choice == "gemini_live_agent":
                gemini_config_data = agent_settings.get("gemini_live_agent")
                if not gemini_config_data:
                    raise ValueError("Gemini Live Agent settings not found in configuration.")
                # Validate with Pydantic model
                gemini_live_config = GeminiLiveConfig(**gemini_config_data)

                # Gemini system_prompt is part of its own config, not the generic one
                return GeminiLiveAgent(
                    config=gemini_live_config,
                    character_name=character_name,
                    character_avatar=character_avatar
                )
            # ...
            else:
                raise ValueError(f"Unsupported agent type: {conversation_agent_choice}")
    ```
    *   Modify `ServiceContext.init_agent` to pass `character_config.character_name` and `character_config.avatar` to `AgentFactory.create_agent`.

3.  **Adapt `AudioOutput` (Optional but Recommended):**
    *   In `open_llm_vtuber/agent/output_types.py`, modify `AudioOutput`'s `audio_path` to accept `Union[str, bytes]`.
        ```python
        @dataclass
        class AudioOutput(BaseOutput):
            audio_path: Union[str, bytes] # Modified to accept bytes
            display_text: DisplayText
            transcript: str
            actions: Actions
        ```
    *   Update `prepare_audio_payload` in `open_llm_vtuber/utils/stream_audio.py` to handle `bytes` for `audio_path`. If it's bytes, assume it's WAV PCM 16-bit 24kHz (Gemini's output format) and base64 encode it directly. You'll also need to derive RMS from these bytes.
        ```python
        # In prepare_audio_payload
        if isinstance(audio_path, bytes): # audio_path is now audio_data_bytes
            audio_bytes = audio_path
            # Convert to AudioSegment to calculate RMS, assuming it's raw PCM 24kHz 16-bit mono
            # This might need pydub to load from raw data
            try:
                # Ensure correct parameters for AudioSegment.from_raw
                # Gemini outputs 24kHz, 16-bit, 1 channel (mono) PCM
                audio = AudioSegment(
                    data=audio_bytes,
                    sample_width=2, # 16-bit
                    frame_rate=24000, # Gemini's output sample rate
                    channels=1
                )
            except Exception as e:
                 raise ValueError(f"Error loading raw audio bytes into AudioSegment: {e}")
        elif audio_path is None: # No audio
            # ... (existing silent payload logic)
        else: # It's a file path string
            try:
                audio = AudioSegment.from_file(audio_path)
                audio_bytes = audio.export(format="wav").read()
            # ... (rest of existing file path logic)

        # ... then continue with base64 encoding and volume calculation
        if audio_bytes: # If audio_bytes were successfully obtained
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            volumes = _get_volume_by_chunks(audio, chunk_length_ms) # audio here is AudioSegment
        else: # For silent or error cases
            audio_base64 = None
            volumes = []

        # ... rest of the payload creation
        ```

---

**Phase 2: Backend WebSocketHandler Integration**

1.  **Modify `open_llm_vtuber/websocket_handler.py`:**
    *   **Audio Chunk Streaming:**
        *   The `_handle_audio_data` method currently buffers all audio. Change this. When `GeminiLiveAgent` is active, instead of buffering in `received_data_buffers`, directly stream these raw float32 chunks (converted to bytes PCM 16-bit 16kHz) to `GeminiLiveAgent.stream_audio_chunk()`.
            ```python
            # In WebSocketHandler._handle_audio_data
            async def _handle_audio_data(self, websocket: WebSocket, client_uid: str, data: WSMessage) -> None:
                context = self.client_contexts[client_uid]
                if isinstance(context.agent_engine, GeminiLiveAgent):
                    audio_floats = data.get("audio", [])
                    if audio_floats:
                        # Convert float32 audio from frontend (typically -1 to 1) to int16 bytes (PCM)
                        # Assuming frontend sends 16kHz audio
                        audio_np = np.array(audio_floats, dtype=np.float32)
                        audio_int16 = (audio_np * 32767).astype(np.int16)
                        audio_bytes = audio_int16.tobytes()
                        await context.agent_engine.stream_audio_chunk(audio_bytes)
                else: # Existing buffering logic for other agents
                    audio_data = data.get("audio", [])
                    if audio_data:
                        self.received_data_buffers[client_uid] = np.append(
                            self.received_data_buffers[client_uid],
                            np.array(audio_data, dtype=np.float32),
                        )
            ```
    *   **Conversation Trigger (`_handle_conversation_trigger`):**
        *   When `msg_type == "mic-audio-end"` and agent is `GeminiLiveAgent`:
            *   Call `context.agent_engine.end_audio_stream()` to signal Gemini that user finished speaking.
            *   The agent's `chat()` method will then be responsible for listening to Gemini's response.
            *   The `process_single_conversation` or `process_group_conversation` will need to be adapted or a new path created for GeminiLiveAgent, as it yields `AudioOutput` which might be raw bytes.
        *   For `text-input` or `ai-speak-signal` with `GeminiLiveAgent`:
            *   The `user_input` (text) will be passed to `GeminiLiveAgent.chat()`. The agent will send this text using `send_client_content`.

    *   **Revised `_handle_conversation_trigger` (Conceptual):**
        ```python
        # In WebSocketHandler._handle_conversation_trigger
        # ...
        if isinstance(context.agent_engine, GeminiLiveAgent):
            if msg_type == "mic-audio-end":
                await context.agent_engine.end_audio_stream() # Signal Gemini audio end
                # Now, the chat task for Gemini should start listening for Gemini's response
                # The existing process_single_conversation needs to be aware of GeminiLiveAgent
            # For text input, user_input (text) will be passed to the chat task
            # For ai-speak-signal, user_input is empty, GeminiLiveAgent should handle this if needed

        # The task creation part will need to handle GeminiLiveAgent differently
        # if its chat() has a different signature or yields different types directly.

        # Simplified Task Creation (conceptual):
        if client_uid not in self.current_conversation_tasks or self.current_conversation_tasks[client_uid].done():
            if isinstance(context.agent_engine, GeminiLiveAgent):
                # GeminiLiveAgent's chat might be simpler if audio streaming is handled separately
                # It might just take the initial text input and then yield responses
                # Or, it could take an async generator of audio chunks for more complex scenarios
                current_conversation_tasks[client_uid] = asyncio.create_task(
                    self._process_gemini_live_conversation(
                        context=context,
                        websocket_send=websocket.send_text,
                        client_uid=client_uid,
                        initial_text_input=user_input if isinstance(user_input, str) else "", # Pass text only
                        # Audio is streamed via stream_audio_chunk
                    )
                )
            else: # Existing logic
                current_conversation_tasks[client_uid] = asyncio.create_task(
                    process_single_conversation( # or group
                        # ...
                    )
                )
        ```
    *   **New method `_process_gemini_live_conversation` in `WebSocketHandler`:**
        This method will specifically iterate over the `GeminiLiveAgent.chat()` results and send them to the frontend.
        ```python
        # In WebSocketHandler
        async def _process_gemini_live_conversation(self, context: ServiceContext, websocket_send: Callable, client_uid: str, initial_text_input: str):
            try:
                agent_engine = cast(GeminiLiveAgent, context.agent_engine) # Cast for type hinting
                batch_input = create_batch_input(initial_text_input, images=None, from_name=context.character_config.human_name)

                async for output in agent_engine.chat(batch_input):
                    if isinstance(output, AudioOutput):
                        # Assuming output.audio_path now contains bytes
                        audio_payload = prepare_audio_payload(
                            audio_path=output.audio_path, # This is bytes
                            display_text=output.display_text,
                            actions=output.actions
                        )
                        await websocket_send(json.dumps(audio_payload))
                    # Handle other output types if necessary
                await websocket_send(json.dumps({"type": "backend-synth-complete"})) # Signal end of AI turn
                await websocket_send(json.dumps({"type": "force-new-message"}))
                await websocket_send(json.dumps({"type": "control", "text": "conversation-chain-end"}))

            except asyncio.CancelledError:
                logger.info(f"Gemini Live conversation for {client_uid} cancelled.")
                agent_engine.handle_interrupt("") # Notify agent
            except Exception as e:
                logger.error(f"Error in Gemini Live conversation for {client_uid}: {e}")
                await websocket_send(json.dumps({"type": "error", "message": str(e)}))
            finally:
                 # Reset agent's interrupt flag for the next turn
                if isinstance(context.agent_engine, GeminiLiveAgent):
                    context.agent_engine.is_interrupted = False
                logger.debug(f"Gemini Live conversation for {client_uid} finished processing.")

        ```

2.  **Handle Interruptions (`_handle_interrupt` in `WebSocketHandler`):**
    *   When the agent is `GeminiLiveAgent`, call `context.agent_engine.handle_interrupt(heard_response)`.
    *   The `GeminiLiveAgent`'s `chat` loop should check `self.is_interrupted` and break. Gemini server itself will also send an `interrupted: True` message if it detects speech during its output.

---

**Phase 3: Emotion and Live2D Synchronization**

1.  **Extracting Emotions from Gemini's Output:**
    *   Gemini Live Mode with `output_audio_transcription` enabled will provide text alongside the audio.
    *   You can process this transcript text using your existing `Live2dModel.extract_emotion()` and `EmotionMotionMapper` if you prompt Gemini to include your emotion tags `[emotion:intensity]` in its speech.
    *   Modify the `system_instruction` for Gemini in `conf.yaml` to instruct it to use these tags.
        *   Example: `"You are a cheerful VTuber. Express emotions using tags like [joy:0.7] or [surprise:0.3] in your speech."`
        *   Append the contents of `prompts/utils/live2d_expression_prompt.txt` to Gemini's system instruction.
    *   In `_process_gemini_live_conversation`, after receiving `AudioOutput`:
        ```python
        # Inside _process_gemini_live_conversation loop
        if isinstance(output, AudioOutput):
            actions = Actions()
            if output.transcript and context.live2d_model: # Ensure live2d_model is available
                expression_tuples = context.live2d_model.extract_emotion(output.transcript)
                if expression_tuples:
                    interpolated_expressions = [
                        context.live2d_model.get_interpolated_expression(idx, intensity)
                        for idx, intensity in expression_tuples
                    ]
                    actions.expressions = interpolated_expressions
                # You might also need EmotionMotionMapper here if not integrated into live2d_model
                # motion_mapper = EmotionMotionMapper() # Potentially initialize once per context
                # motions = [] etc. based on output.transcript

            audio_payload = prepare_audio_payload(
                audio_path=output.audio_path,
                display_text=output.display_text,
                actions=actions # Pass extracted actions
            )
            await websocket_send(json.dumps(audio_payload))
        ```

---

**Phase 4: Frontend Considerations (Minimal Changes Expected Initially)**

*   The frontend should continue to send audio chunks as it does now.
*   It will receive audio payloads (potentially with raw base64 audio if you adapt `prepare_audio_payload` correctly) and play them.
*   Live2D actions will be processed as usual.
*   A new option in the UI to select "Gemini Live Agent" if you support multiple agents.

---

**Phase 5: Testing and Refinement**

1.  **Incremental Testing:**
    *   Test configuration loading.
    *   Test `GeminiLiveAgent` connection to Gemini (can be done with a simple script first).
    *   Test text-only input to `GeminiLiveAgent`.
    *   Test audio streaming from `WebSocketHandler` to `GeminiLiveAgent` and then to Gemini.
    *   Test audio response from Gemini back to the frontend.
    *   Test emotion tag extraction and Live2D sync.
    *   Test interruption.
    *   Test session resumption with history.

2.  **Latency:**
    *   Measure end-to-end latency. Gemini Live Mode is designed for low latency, so this should be significantly better than separate ASR -> LLM -> TTS.

3.  **Error Handling:**
    *   Robustly handle API errors, connection drops, invalid API keys, etc. Provide clear feedback to the user.
    *   Gemini's `go_away` message should be handled to inform the user or attempt reconnection.

4.  **Token Usage & Cost:**
    *   Monitor token usage via `response.usage_metadata`. Be mindful of costs.

5.  **Refine Audio Chunking:**
    *   Ensure audio chunks sent to `GeminiLiveAgent.stream_audio_chunk` are in the correct format (PCM 16-bit, 16kHz). Your frontend already sends float32, so the conversion in `_handle_audio_data` is key.
    *   The sample rate for Gemini input audio is natively 16kHz. Output is 24kHz.

6.  **Session Management:**
    *   Implement proper session closing for the Gemini connection when the client disconnects from your backend or switches agents.
    *   Use `session_resumption_handle` to persist conversations across disconnects if desired and store it in your `chat_history_manager` metadata.

---

**Key Changes Summary:**

*   **New Agent:** `GeminiLiveAgent` handling communication with Gemini.
*   **Config:** New `GeminiLiveConfig` and updates to `conf.yaml`.
*   **WebSocketHandler:**
    *   Streams audio directly to `GeminiLiveAgent` if active.
    *   Calls `GeminiLiveAgent.end_audio_stream()` on `mic-audio-end`.
    *   New conversation processing logic for `GeminiLiveAgent`.
*   **Output:** `GeminiLiveAgent` yields `AudioOutput` (potentially with raw audio bytes). `prepare_audio_payload` adapted.
*   **Emotion/Live2D:** Prompt Gemini to use your tags; process its transcript.
*   **ASR/TTS Bypass:** Your existing ASR/TTS modules are bypassed when `GeminiLiveAgent` is active.

This is a significant integration. Take it step by step, testing thoroughly at each phase. Good luck!
