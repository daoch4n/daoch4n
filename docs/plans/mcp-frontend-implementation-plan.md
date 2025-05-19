# MCP Frontend Implementation Plan

This document outlines the detailed plan for implementing the frontend components required for the Model Context Protocol (MCP) integration in the Open LLM Vtuber project. This implementation focuses on enabling the frontend to handle MCP tool invocations, user consent dialogs, and Live2D model interactions.

## Overview

The frontend implementation will enable the Vtuber application to:

1. Parse MCP tool invocations from LLM responses
2. Display user consent dialogs for tool execution
3. Handle tool execution results
4. Update the Live2D model based on expression and motion tools
5. Display information from external data sources

## Implementation Components

### 1. WebSocket Message Handlers

#### 1.1 MCP Tool Invocation Handler

Create handlers for the new WebSocket message types:

- `mcp-tool-result`: Receive tool execution results
- `mcp-consent-request`: Receive requests for user consent

```typescript
// src/renderer/src/services/websocket-service.tsx

// Add to MessageEvent interface
export interface MessageEvent {
  // ... existing fields
  tool_name?: string;
  parameters?: any;
  request_id?: string;
  result?: any;
  error?: string;
}

// Update onMessage handler to handle MCP-related messages
private handleMessage(message: MessageEvent) {
  switch (message.type) {
    // ... existing cases
    case 'mcp-consent-request':
      this.handleConsentRequest(message);
      break;
    case 'mcp-tool-result':
      this.handleToolResult(message);
      break;
  }
}

private handleConsentRequest(message: MessageEvent) {
  // Display consent dialog and handle user response
  // Will be implemented in the UI components section
}

private handleToolResult(message: MessageEvent) {
  // Process tool execution results
  // Will be implemented in the tool handlers section
}
```

### 2. UI Components

#### 2.1 Consent Dialog Component

Create a modal dialog component for user consent:

```typescript
// src/renderer/src/components/mcp/ConsentDialog.tsx
import React from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  Button,
  Text,
} from '@chakra-ui/react';
import { useWebSocket } from '@/context/websocket-context';

interface ConsentDialogProps {
  isOpen: boolean;
  onClose: () => void;
  toolName: string;
  parameters: any;
  requestId: string;
}

export const ConsentDialog: React.FC<ConsentDialogProps> = ({
  isOpen,
  onClose,
  toolName,
  parameters,
  requestId,
}) => {
  const { sendMessage } = useWebSocket();

  const handleApprove = () => {
    sendMessage({
      type: 'mcp-tool-invoke',
      tool_name: toolName,
      parameters: parameters,
      request_id: requestId,
      consent: true,
    });
    onClose();
  };

  const handleDeny = () => {
    sendMessage({
      type: 'mcp-tool-invoke',
      tool_name: toolName,
      parameters: parameters,
      request_id: requestId,
      consent: false,
    });
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Tool Execution Request</ModalHeader>
        <ModalBody>
          <Text>
            The AI assistant wants to use the tool: <strong>{toolName}</strong>
          </Text>
          <Text mt={2}>Parameters:</Text>
          <pre>{JSON.stringify(parameters, null, 2)}</pre>
          <Text mt={2}>Do you allow this action?</Text>
        </ModalBody>
        <ModalFooter>
          <Button colorScheme="red" mr={3} onClick={handleDeny}>
            Deny
          </Button>
          <Button colorScheme="green" onClick={handleApprove}>
            Allow
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
```

#### 2.2 MCP Context Provider

Create a context provider to manage MCP state:

```typescript
// src/renderer/src/context/mcp-context.tsx
import React, { createContext, useContext, useState, useCallback } from 'react';
import { useWebSocket } from './websocket-context';
import { ConsentDialog } from '@/components/mcp/ConsentDialog';

interface MCPContextType {
  isConsentDialogOpen: boolean;
  currentToolRequest: {
    toolName: string;
    parameters: any;
    requestId: string;
  } | null;
}

const MCPContext = createContext<MCPContextType | null>(null);

export const MCPProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { onMessage } = useWebSocket();
  const [isConsentDialogOpen, setIsConsentDialogOpen] = useState(false);
  const [currentToolRequest, setCurrentToolRequest] = useState<{
    toolName: string;
    parameters: any;
    requestId: string;
  } | null>(null);

  // Subscribe to WebSocket messages
  React.useEffect(() => {
    const subscription = onMessage((message) => {
      if (message.type === 'mcp-consent-request') {
        setCurrentToolRequest({
          toolName: message.tool_name || '',
          parameters: message.parameters || {},
          requestId: message.request_id || '',
        });
        setIsConsentDialogOpen(true);
      }
    });

    return () => subscription.unsubscribe();
  }, [onMessage]);

  const closeConsentDialog = useCallback(() => {
    setIsConsentDialogOpen(false);
  }, []);

  return (
    <MCPContext.Provider
      value={{
        isConsentDialogOpen,
        currentToolRequest,
      }}
    >
      {children}
      {currentToolRequest && (
        <ConsentDialog
          isOpen={isConsentDialogOpen}
          onClose={closeConsentDialog}
          toolName={currentToolRequest.toolName}
          parameters={currentToolRequest.parameters}
          requestId={currentToolRequest.requestId}
        />
      )}
    </MCPContext.Provider>
  );
};

export const useMCP = () => {
  const context = useContext(MCPContext);
  if (!context) {
    throw new Error('useMCP must be used within an MCPProvider');
  }
  return context;
};
```

### 3. LLM Response Parser

#### 3.1 MCP Tool Invocation Parser

Create a parser to detect and extract MCP tool invocations from LLM responses:

```typescript
// src/renderer/src/utils/mcp-parser.ts
interface MCPToolInvocation {
  toolName: string;
  parameters: any;
}

export const parseMCPToolInvocation = (text: string): MCPToolInvocation | null => {
  // Regular expression to match MCP tool invocation syntax
  // <mcp:tool name="tool_name" parameters={"param1": "value1", "param2": "value2"}>
  const mcpRegex = /<mcp:tool\s+name="([^"]+)"\s+parameters=(\{[^}]+\})>/;
  
  const match = text.match(mcpRegex);
  if (!match) return null;
  
  try {
    const toolName = match[1];
    const parameters = JSON.parse(match[2]);
    
    return {
      toolName,
      parameters,
    };
  } catch (error) {
    console.error('Error parsing MCP tool invocation:', error);
    return null;
  }
};
```

### 4. Live2D Model Integration

#### 4.1 Expression and Motion Handlers

Update the Live2D model hooks to handle expression and motion tool results:

```typescript
// src/renderer/src/hooks/canvas/use-live2d-model.ts

// Add handlers for MCP tool results
const handleMCPToolResult = useCallback((result: any) => {
  if (!result || !result.success) return;
  
  // Handle expression tool
  if (result.tool_name === 'set_expression' && result.result?.expression) {
    const { expression, duration = 3 } = result.result;
    setExpression(expression, duration);
  }
  
  // Handle motion tool
  if (result.tool_name === 'play_motion' && result.result?.motion) {
    const { motion, loop = false } = result.result;
    playMotion(motion, loop);
  }
}, [setExpression, playMotion]);

// Subscribe to WebSocket messages for tool results
useEffect(() => {
  const subscription = wsService.onMessage((message) => {
    if (message.type === 'mcp-tool-result') {
      handleMCPToolResult(message);
    }
  });
  
  return () => subscription.unsubscribe();
}, [handleMCPToolResult]);
```

### 5. External Data Display

#### 5.1 Weather and Search Result Components

Create components to display results from external data tools:

```typescript
// src/renderer/src/components/mcp/WeatherDisplay.tsx
import React from 'react';
import { Box, Text, Flex, Icon } from '@chakra-ui/react';
import { WiDaySunny, WiRain, WiCloudy, WiSnow } from 'react-icons/wi';

interface WeatherDisplayProps {
  weatherData: any;
}

export const WeatherDisplay: React.FC<WeatherDisplayProps> = ({ weatherData }) => {
  // Render weather information
  // Implementation details...
};

// src/renderer/src/components/mcp/SearchResults.tsx
import React from 'react';
import { Box, Text, Link, VStack } from '@chakra-ui/react';

interface SearchResultsProps {
  searchData: any;
}

export const SearchResults: React.FC<SearchResultsProps> = ({ searchData }) => {
  // Render search results
  // Implementation details...
};
```

## Integration Steps

### 1. Update App Component

Update the main App component to include the MCP Provider:

```typescript
// src/renderer/src/App.tsx
import { MCPProvider } from '@/context/mcp-context';

function App() {
  return (
    <ChakraProvider>
      {/* Other providers */}
      <MCPProvider>
        {/* App content */}
      </MCPProvider>
    </ChakraProvider>
  );
}
```

### 2. Update Chat Component

Modify the chat component to parse and handle MCP tool invocations:

```typescript
// src/renderer/src/components/chat/ChatMessage.tsx
import { parseMCPToolInvocation } from '@/utils/mcp-parser';
import { useWebSocket } from '@/context/websocket-context';

// Inside the component
const { sendMessage } = useWebSocket();

// Process message content for MCP tool invocations
const processMessageContent = (content: string) => {
  const toolInvocation = parseMCPToolInvocation(content);
  
  if (toolInvocation) {
    // Send tool invocation request
    sendMessage({
      type: 'mcp-tool-invoke',
      tool_name: toolInvocation.toolName,
      parameters: toolInvocation.parameters,
    });
    
    // Remove the tool invocation syntax from the displayed message
    return content.replace(/<mcp:tool[^>]+>/, '');
  }
  
  return content;
};
```

## Testing Plan

1. **Unit Tests**:
   - Test MCP tool invocation parser
   - Test WebSocket message handlers
   - Test UI components

2. **Integration Tests**:
   - Test end-to-end flow from LLM response to tool execution
   - Test user consent dialog flow
   - Test Live2D model expression and motion changes

3. **Manual Testing**:
   - Verify tool invocation with different LLM providers
   - Test with various tool parameters
   - Verify error handling

## Timeline

1. **Week 1**: Implement WebSocket handlers and UI components
2. **Week 2**: Implement LLM response parser and Live2D model integration
3. **Week 3**: Implement external data display components and testing
4. **Week 4**: Integration, bug fixes, and documentation

## Conclusion

This implementation plan provides a comprehensive approach to integrating MCP frontend components with the Open LLM Vtuber project. By following this plan, the frontend will be able to handle MCP tool invocations, display user consent dialogs, and update the Live2D model based on tool execution results.
