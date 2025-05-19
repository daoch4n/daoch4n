# Gemini Live User Guide

## Introduction

Welcome to the Gemini Live integration for the Live2D VTuber application! This guide will help you set up and use the Gemini Live agent to create more natural and responsive VTuber interactions.

Gemini Live is Google's real-time conversational AI model that supports streaming audio input and output. This integration allows your VTuber to respond more naturally, with lower latency and more interactive conversations.

## Getting Started

### Prerequisites

Before you can use the Gemini Live integration, you'll need:

1. A Google AI Studio account
2. A Gemini API key
3. The Live2D VTuber application installed and configured

### Obtaining a Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/)
2. Sign in with your Google account
3. Navigate to the API Keys section
4. Create a new API key
5. Copy the API key for use in your configuration

### Basic Configuration

1. Open your character configuration file (or create a new one)
2. Set the `conversation_agent_choice` to `gemini_live_agent`
3. Configure the Gemini Live agent with your API key and preferences:

```yaml
character_config:
  conf_name: 'Gemini Live Character'
  conf_uid: 'gemini-live-character-001'
  live2d_model_name: 'your-model-name'
  character_name: 'Gemini'
  avatar: 'gemini.png'
  human_name: 'Human'

  agent_config:
    conversation_agent_choice: 'gemini_live_agent'
    
    agent_settings:
      gemini_live_agent:
        api_key: 'YOUR_GEMINI_API_KEY'
        model_name: 'gemini-2.0-flash-live-001'
        language_code: 'en-US'
        voice_name: 'Kore'
        system_instruction: |
          You are a cheerful and helpful VTuber assistant named Gemini.
          You should respond in a friendly, conversational manner.
          Keep your responses concise and engaging.
```

### Starting the Application

1. Start the Live2D VTuber application
2. Select your Gemini Live character configuration
3. Wait for the application to connect to Gemini Live
4. Start interacting with your VTuber!

## Basic Usage

### Voice Interaction

1. Click the microphone button or press the configured hotkey to start recording
2. Speak clearly into your microphone
3. Release the button or press the hotkey again to stop recording
4. Wait for your VTuber to respond

### Text Interaction

1. Type your message in the text input field
2. Press Enter or click the send button
3. Wait for your VTuber to respond

### Interrupting

You can interrupt your VTuber while it's speaking by:

1. Clicking the microphone button or pressing the hotkey
2. Speaking into your microphone
3. The VTuber will stop its current response and listen to you

## Advanced Configuration

### Voice Selection

Gemini Live offers several voice options:

- **Puck**: Friendly, youthful voice
- **Charon**: Deep, mature voice
- **Kore**: Warm, natural voice
- **Fenrir**: Energetic, dynamic voice
- **Aoede**: Melodic, gentle voice
- **Leda**: Clear, articulate voice
- **Orus**: Authoritative, confident voice
- **Zephyr**: Soft, calming voice

Configure your preferred voice:

```yaml
voice_name: 'Kore'  # Choose from available voices
```

### Language Selection

Gemini Live supports multiple languages. Configure your preferred language:

```yaml
language_code: 'en-US'  # English (US)
# Other options: 'ja-JP' (Japanese), 'es-ES' (Spanish), etc.
```

### System Instructions

The system instruction defines your VTuber's personality and behavior. Create a detailed instruction:

```yaml
system_instruction: |
  You are a cheerful and helpful VTuber assistant named Gemini.
  You should respond in a friendly, conversational manner.
  Keep your responses concise and engaging.
  
  Express emotions in your responses using emotion tags like [joy:0.7] or [surprise:0.3].
  Available emotions: neutral, joy, sadness, anger, fear, surprise, disgust, smirk.
  The number after the colon represents intensity from 0.0 to 1.0.
  
  Example: "I'm [joy:0.8] so happy to meet you! What can I help you with today?"
```

### Voice Activity Detection (VAD)

Configure how Gemini detects the start and end of speech:

```yaml
# Voice Activity Detection settings
start_of_speech_sensitivity: "START_SENSITIVITY_MEDIUM"  # Options: LOW, MEDIUM, HIGH
end_of_speech_sensitivity: "END_SENSITIVITY_MEDIUM"      # Options: LOW, MEDIUM, HIGH
silence_duration_ms: 800  # How long of silence before considering speech ended
prefix_padding_ms: 200    # How much audio to include before speech starts
```

For more control, you can disable automatic VAD:

```yaml
# Manual VAD control
disable_automatic_vad: true
```

### Tool Integration

Enable tools to give your VTuber additional capabilities:

```yaml
# Tool configurations
enable_function_calling: true
function_declarations:
  - name: "get_weather"
    description: "Get the current weather for a location"
    parameters:
      type: "object"
      properties:
        location:
          type: "string"
          description: "The city and state, e.g., San Francisco, CA"
      required: ["location"]
enable_code_execution: true
enable_google_search: true
```

### Context Window Compression

Configure context window compression for longer conversations:

```yaml
# Context window compression
enable_context_compression: true
compression_window_size: 10        # Number of turns to include
compression_token_threshold: 4000  # Token count that triggers compression
```

### Audio Transcription

Enable transcription of user audio:

```yaml
# Audio transcription
enable_input_audio_transcription: true
```

## Tips and Best Practices

### Creating an Effective System Instruction

1. **Be Specific**: Clearly define your VTuber's personality, knowledge, and limitations
2. **Include Examples**: Provide examples of how your VTuber should respond
3. **Define Emotion Usage**: Explain how and when to use emotion tags
4. **Set Boundaries**: Define topics your VTuber should avoid
5. **Keep it Concise**: Focus on the most important aspects of your VTuber's character

### Optimizing Voice Interaction

1. **Use a Good Microphone**: A clear audio input improves recognition
2. **Speak Clearly**: Enunciate words clearly for better understanding
3. **Adjust VAD Settings**: Fine-tune sensitivity based on your environment
4. **Use Manual VAD**: For noisy environments, manual VAD may work better
5. **Test Different Voices**: Try different voices to find the best match for your VTuber

### Managing Long Conversations

1. **Enable Context Compression**: This allows for longer conversations
2. **Adjust Compression Settings**: Fine-tune based on your conversation style
3. **Monitor Token Usage**: Keep an eye on token usage for cost management
4. **Use Session Resumption**: This allows conversations to continue across sessions
5. **Clear History When Needed**: Start fresh when changing topics significantly

## Troubleshooting

### Common Issues

#### Connection Problems

**Symptoms**: Unable to connect to Gemini Live, error messages about API key or connection

**Solutions**:
- Verify your API key is correct
- Check your internet connection
- Ensure you have sufficient quota in your Google AI Studio account
- Restart the application

#### Audio Not Working

**Symptoms**: VTuber doesn't respond to voice, or you can't hear responses

**Solutions**:
- Check microphone permissions
- Verify audio input/output devices in your system settings
- Adjust VAD sensitivity settings
- Try using text input to verify the agent is working

#### High Latency

**Symptoms**: Long delays between your input and the VTuber's response

**Solutions**:
- Check your internet connection speed
- Reduce the system instruction length
- Adjust VAD settings for quicker detection
- Try manual VAD control
- Use a region closer to your location if possible

#### Unexpected Responses

**Symptoms**: VTuber responds inappropriately or out of character

**Solutions**:
- Refine your system instruction
- Provide more examples in the system instruction
- Be more specific about the VTuber's personality
- Check if the conversation history is too long or confusing

### Getting Help

If you encounter issues not covered in this guide:

1. Check the application logs for error messages
2. Consult the technical documentation
3. Visit the project's GitHub repository for known issues
4. Contact support with detailed information about your problem

## Advanced Topics

### Creating Custom Tools

You can create custom tools for your VTuber by defining function declarations:

```yaml
function_declarations:
  - name: "get_character_info"
    description: "Get information about a character in the story"
    parameters:
      type: "object"
      properties:
        character_name:
          type: "string"
          description: "The name of the character"
      required: ["character_name"]
```

The backend will need to implement handlers for these functions.

### Multi-modal Interactions

While primarily focused on voice, Gemini Live can also handle:

1. **Text Input**: Type messages instead of speaking
2. **Image Input**: Show images to your VTuber (if configured)
3. **Combined Input**: Use voice while showing images

### Performance Optimization

For better performance:

1. **Reduce System Instruction**: Keep it concise but effective
2. **Optimize VAD Settings**: Find the right balance for your environment
3. **Use Context Compression**: Enable and configure appropriately
4. **Monitor Token Usage**: Keep track of usage to optimize costs
5. **Close Sessions When Idle**: Don't leave sessions open unnecessarily

## Conclusion

The Gemini Live integration provides a powerful way to create more natural and responsive VTuber interactions. By following this guide, you can configure and optimize your VTuber for the best possible experience.

Remember that Gemini Live is continuously improving, so check for updates and new features regularly. Enjoy creating engaging VTuber experiences with Gemini Live!
