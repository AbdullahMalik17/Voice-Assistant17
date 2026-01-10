import { NextRequest, NextResponse } from 'next/server';
import { searchWithTavily, formatSearchResults } from '@/lib/tavily';

export async function POST(request: NextRequest) {
  try {
    const { query } = await request.json();

    if (!query || typeof query !== 'string') {
      return NextResponse.json(
        { error: 'Query parameter is required and must be a string' },
        { status: 400 }
      );
    }

    const results = await searchWithTavily(query);

    return NextResponse.json({
      success: true,
      query: results.query,
      answer: results.answer,
      results: results.results,
      formatted: formatSearchResults(results.results),
      images: results.images,
      follow_up_questions: results.follow_up_questions,
    });
  } catch (error) {
    console.error('Search API error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Search failed' },
      { status: 500 }
    );
  }
}
