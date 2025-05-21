import asyncio
import json
from typing import Dict, Optional, Callable, Union, List, Any

import numpy as np
from fastapi import WebSocket
from loguru import logger

from ..agent.agents.gemini_live_agent import GeminiLiveAgent

from ..chat_group import ChatGroupManager
from ..chat_history_manager import store_message
from ..service_context import ServiceContext
from .single_conversation import process_single_conversation
from .conversation_utils import send_conversation_start_signals, finalize_conversation_turn
from .types import WebSocketSend
from ..agent.input_types import BatchInput, TextData, TextSource
from ..utils.stream_audio import prepare_audio_payload


async def handle_conversation_trigger(
    msg_type: str,
    data: dict,
    client_uid: str,
    context: ServiceContext,
    websocket: WebSocket,
    client_contexts: Dict[str, ServiceContext],
    client_connections: Dict[str, WebSocket],
    chat_group_manager: ChatGroupManager,
    received_data_buffers: Dict[str, np.ndarray],
    current_conversation_tasks: Dict[str, Optional[asyncio.Task]],
    broadcast_to_group: Callable,
) -> None:
    """Handle triggers that start a conversation"""
    # Special handling for Gemini Live Agent when audio ends
    if msg_type == "mic-audio-end" and isinstance(context.agent_engine, GeminiLiveAgent):
        # Signal the end of audio stream to Gemini Live
        await context.agent_engine.end_audio_stream()

        # For Gemini Live, we'll create a special conversation task that just processes responses
        # from the already-streaming audio
        current_conversation_tasks[client_uid] = asyncio.create_task(
            process_gemini_live_conversation(
                context=context,
                websocket_send=websocket.send_text,
                client_uid=client_uid,
                images=data.get("images")
            )
        )
        # Return early as we've already set up the task
        return

    # Standard handling for other agents or message types
    if msg_type == "ai-speak-signal":
        user_input = ""
        await websocket.send_text(
            json.dumps(
                {
                    "type": "full-text",
                    "text": "AI wants to speak something...",
                }
            )
        )
    elif msg_type == "text-input":
        user_input = data.get("text", "")
    else:  # mic-audio-end for non-Gemini agents
        user_input = received_data_buffers[client_uid]
        received_data_buffers[client_uid] = np.array([])

    images = data.get("images")
    session_emoji = np.random.choice(EMOJI_LIST)

    current_conversation_tasks[client_uid] = asyncio.create_task(
        process_single_conversation(
            context=context,
            websocket_send=websocket.send_text,
            client_uid=client_uid,
            user_input=user_input,
            images=images,
            session_emoji=session_emoji,
        )
    )


async def handle_individual_interrupt(
    client_uid: str,
    current_conversation_tasks: Dict[str, Optional[asyncio.Task]],
    context: ServiceContext,
    heard_response: str,
):
    if client_uid in current_conversation_tasks:
        task = current_conversation_tasks[client_uid]
        if task and not task.done():
            task.cancel()
            logger.info("🛑 Conversation task was successfully interrupted")

        try:
            context.agent_engine.handle_interrupt(heard_response)
        except Exception as e:
            logger.error(f"Error handling interrupt: {e}")

        if context.history_uid:
            store_message(
                conf_uid=context.character_config.conf_uid,
                history_uid=context.history_uid,
                role="ai",
                content=heard_response,
                name=context.character_config.character_name,
                avatar=context.character_config.avatar,
            )
            store_message(
                conf_uid=context.character_config.conf_uid,
                history_uid=context.history_uid,
                role="system",
                content="[Interrupted by user]",
            )


async def process_gemini_live_conversation(
    context: ServiceContext,
    websocket_send: WebSocketSend,
    client_uid: str,
    images: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Process a conversation with Gemini Live agent.

    This function is specifically for handling the Gemini Live agent's responses
    after audio has been streamed to it. It doesn't need to send audio to Gemini
    as that's already been done through the stream_audio_chunk method.

    Args:
        context: Service context containing all configurations and engines
        websocket_send: WebSocket send function
        client_uid: Client unique identifier
        images: Optional list of image data
    """
    try:
        # Send initial signals
        await send_conversation_start_signals(websocket_send)
        logger.info(f"Gemini Live conversation started for {client_uid}!")

        # Create a minimal batch input with any images
        # The text content isn't important as Gemini already has the audio
        batch_input = BatchInput(
            texts=[TextData(source=TextSource.INPUT, content="")],
            images=images
        )

        # Process Gemini Live responses
        gemini_agent = context.agent_engine
        full_response = ""

        try:
            async for output in gemini_agent.chat(batch_input):
                # AudioOutput contains audio_path, display_text, transcript, and actions
                audio_payload = prepare_audio_payload(
                    audio_path=output.audio_path,
                    display_text=output.display_text,
                    actions=output.actions.to_dict() if output.actions else None,
                )
                await websocket_send(json.dumps(audio_payload))
                full_response += output.transcript
        except asyncio.CancelledError:
            logger.info(f"Gemini Live conversation for {client_uid} cancelled.")
            raise
        except Exception as e:
            logger.error(f"Error in Gemini Live conversation: {e}")
            await websocket_send(json.dumps({"type": "error", "message": str(e)}))
            raise

        # Signal that backend synthesis is complete
        await websocket_send(json.dumps({"type": "backend-synth-complete"}))
        await websocket_send(json.dumps({"type": "force-new-message"}))
        await websocket_send(json.dumps({"type": "control", "text": "conversation-chain-end"}))

        # Store the conversation in history if available
        if context.history_uid and full_response:
            store_message(
                conf_uid=context.character_config.conf_uid,
                history_uid=context.history_uid,
                role="ai",
                content=full_response,
                name=context.character_config.character_name,
                avatar=context.character_config.avatar,
            )
            logger.info(f"AI response: {full_response}")

            # Update chat history resource in MCP client if available
            if context.mcp_client:
                try:
                    from ..mcp.default_resources import create_chat_history_resource
                    from ..chat_history_manager import get_history

                    # Get updated history
                    history = get_history(
                        context.character_config.conf_uid,
                        context.history_uid,
                    )

                    # Create and register updated chat history resource
                    chat_history_resource = create_chat_history_resource(history)
                    context.mcp_client.register_resource(chat_history_resource)
                    logger.debug("Updated chat history resource in MCP client")
                except Exception as e:
                    logger.error(f"Error updating chat history resource: {e}")

    except asyncio.CancelledError:
        logger.info(f"Gemini Live conversation for {client_uid} cancelled because interrupted.")
        raise
    except Exception as e:
        logger.error(f"Error in Gemini Live conversation: {e}")
        await websocket_send(json.dumps({"type": "error", "message": f"Conversation error: {str(e)}"}))
        raise


