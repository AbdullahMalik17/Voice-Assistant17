import axios from 'axios';

export interface TavilySearchResult {
  title: string;
  url: string;
  content: string;
  score: number;
  raw_content?: string;
}

export interface TavilyResponse {
  answer: string;
  query: string;
  response_time: number;
  images: string[];
  results: TavilySearchResult[];
  follow_up_questions: string[];
}

const TAVILY_API_URL = 'https://api.tavily.com/search';

export async function searchWithTavily(query: string): Promise<TavilyResponse> {
  const apiKey = process.env.TAVILY_API_KEY;

  if (!apiKey) {
    throw new Error('TAVILY_API_KEY is not configured');
  }

  try {
    const response = await axios.post(TAVILY_API_URL, {
      api_key: apiKey,
      query: query,
      include_answer: true,
      include_raw_content: true,
      max_results: 5,
      topic: 'general',
    });

    return response.data as TavilyResponse;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(`Tavily API error: ${error.response?.status} ${error.response?.statusText}`);
    }
    throw error;
  }
}

export function formatSearchResults(results: TavilySearchResult[]): string {
  return results
    .map((result, index) => {
      return `
[${index + 1}] ${result.title}
URL: ${result.url}
Content: ${result.content}
---`;
    })
    .join('\n');
}
