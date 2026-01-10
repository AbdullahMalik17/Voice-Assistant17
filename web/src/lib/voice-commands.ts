/**
 * Voice Command Handler Service
 * Processes voice commands and executes appropriate actions
 * (web search, browser automation, etc.)
 */

import axios from 'axios';
import { BrowserAction } from './browser';

export interface VoiceCommandContext {
  text: string;
  intent?: string;
  confidence?: number;
  timestamp?: Date;
}

export interface CommandResponse {
  status: 'success' | 'error';
  data?: any;
  message: string;
  action_type?: string;
}

// Keywords for detecting command types
const SEARCH_KEYWORDS = ['search', 'find', 'look up', 'what is', 'who is', 'tell me about'];
const BROWSE_KEYWORDS = ['open', 'go to', 'navigate', 'visit', 'take screenshot'];
const CLICK_KEYWORDS = ['click', 'press', 'tap'];
const TYPE_KEYWORDS = ['type', 'write', 'enter'];

export function detectCommandType(text: string): string {
  const lowerText = text.toLowerCase();

  if (SEARCH_KEYWORDS.some((k) => lowerText.includes(k))) {
    return 'search';
  }
  if (BROWSE_KEYWORDS.some((k) => lowerText.includes(k))) {
    return 'browse';
  }
  if (CLICK_KEYWORDS.some((k) => lowerText.includes(k))) {
    return 'click';
  }
  if (TYPE_KEYWORDS.some((k) => lowerText.includes(k))) {
    return 'type';
  }

  return 'unknown';
}

export async function executeWebSearch(query: string): Promise<CommandResponse> {
  try {
    const response = await axios.post('/api/search', { query });
    return {
      status: 'success',
      data: response.data,
      message: `Found ${response.data.results?.length || 0} results for "${query}"`,
      action_type: 'web_search',
    };
  } catch (error) {
    return {
      status: 'error',
      message: error instanceof Error ? error.message : 'Search failed',
      action_type: 'web_search',
    };
  }
}

export async function executeBrowserAction(action: BrowserAction): Promise<CommandResponse> {
  try {
    const response = await axios.post('/api/browser', action);

    if (!response.data.success) {
      return {
        status: 'error',
        message: response.data.error || 'Browser action failed',
        action_type: action.type,
      };
    }

    return {
      status: 'success',
      data: response.data,
      message: `Browser action completed: ${action.type}`,
      action_type: action.type,
    };
  } catch (error) {
    return {
      status: 'error',
      message: error instanceof Error ? error.message : 'Browser action failed',
      action_type: action.type,
    };
  }
}

/**
 * Process a voice command and execute appropriate action
 */
export async function processVoiceCommand(context: VoiceCommandContext): Promise<CommandResponse> {
  const commandType = detectCommandType(context.text);

  switch (commandType) {
    case 'search': {
      // Extract search query from text
      const query = extractSearchQuery(context.text);
      return executeWebSearch(query);
    }

    case 'browse': {
      const url = extractURL(context.text);
      if (!url) {
        return {
          status: 'error',
          message: 'Could not extract URL from command',
          action_type: 'browse',
        };
      }
      return executeBrowserAction({ type: 'navigate', url });
    }

    case 'click': {
      const selector = extractSelector(context.text);
      if (!selector) {
        return {
          status: 'error',
          message: 'Could not extract element selector from command',
          action_type: 'click',
        };
      }
      return executeBrowserAction({ type: 'click', selector });
    }

    case 'type': {
      const selector = extractSelector(context.text);
      const text = extractTypeText(context.text);
      if (!selector || !text) {
        return {
          status: 'error',
          message: 'Could not extract selector or text from command',
          action_type: 'type',
        };
      }
      return executeBrowserAction({ type: 'type', selector, text });
    }

    default:
      return {
        status: 'error',
        message: `Unknown command type: ${commandType}`,
        action_type: 'unknown',
      };
  }
}

// Helper functions to extract information from voice commands

function extractSearchQuery(text: string): string {
  const keywords = ['search for', 'search', 'find', 'look up', 'tell me about'];

  for (const keyword of keywords) {
    const index = text.toLowerCase().indexOf(keyword);
    if (index !== -1) {
      return text.substring(index + keyword.length).trim();
    }
  }

  return text;
}

function extractURL(text: string): string | null {
  // Try to extract URL patterns
  const urlPattern =
    /(?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:\/[^,\s]*)?\b/g;
  const matches = text.match(urlPattern);

  if (matches && matches.length > 0) {
    let url = matches[0];
    if (!url.startsWith('http')) {
      url = 'https://' + url;
    }
    return url;
  }

  // Try keywords like "open google", "go to facebook"
  const keywords = ['open', 'go to', 'visit', 'navigate'];
  for (const keyword of keywords) {
    const index = text.toLowerCase().indexOf(keyword);
    if (index !== -1) {
      const rest = text.substring(index + keyword.length).trim();
      const words = rest.split(/\s+/);
      if (words.length > 0) {
        return `https://${words[0]}.com`;
      }
    }
  }

  return null;
}

function extractSelector(text: string): string | null {
  // Look for quoted selectors like 'click "button.submit"'
  const quotedPattern = /"([^"]*)"/;
  const match = text.match(quotedPattern);

  if (match && match[1]) {
    return match[1];
  }

  // Try to find CSS-like patterns
  const selectorPattern = /(?:id|class|selector)?\s*["']?([#\.][a-zA-Z0-9-_]+)["']?/i;
  const selectorMatch = text.match(selectorPattern);

  if (selectorMatch && selectorMatch[1]) {
    return selectorMatch[1];
  }

  return null;
}

function extractTypeText(text: string): string | null {
  // Look for text after "type" or "write"
  const keywords = ['type', 'write', 'enter'];

  for (const keyword of keywords) {
    const index = text.toLowerCase().indexOf(keyword);
    if (index !== -1) {
      let extractedText = text.substring(index + keyword.length).trim();

      // Remove selector if present
      const selectorPattern = /^["']?[#\.][a-zA-Z0-9-_]+["']?\s*/;
      extractedText = extractedText.replace(selectorPattern, '');

      return extractedText;
    }
  }

  return null;
}

export function formatCommandResponse(response: CommandResponse): string {
  if (response.status === 'success') {
    return response.message;
  }
  return `Error: ${response.message}`;
}
