import { NextRequest, NextResponse } from 'next/server';
import { executeBrowserAction, BrowserAction } from '@/lib/browser';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action, url, selector, text, query, scrollAmount } = body as BrowserAction & Record<string, any>;

    if (!action) {
      return NextResponse.json(
        { error: 'Action type is required' },
        { status: 400 }
      );
    }

    const browserAction: BrowserAction = {
      type: action,
      url,
      selector,
      text,
      query,
      scrollAmount,
    };

    const result = await executeBrowserAction(browserAction);

    return NextResponse.json(result);
  } catch (error) {
    console.error('Browser API error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Browser action failed' },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  return NextResponse.json({
    available_actions: [
      'navigate - Navigate to a URL',
      'click - Click an element by selector',
      'type - Type text in an input field',
      'screenshot - Take a screenshot',
      'search - Perform a Google search',
      'scroll - Scroll the page',
      'extract - Extract text content',
    ],
  });
}
