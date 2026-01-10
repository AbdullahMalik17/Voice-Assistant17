import { chromium, Browser, Page } from 'playwright';

export interface BrowserAction {
  type: 'navigate' | 'click' | 'type' | 'screenshot' | 'search' | 'scroll' | 'extract';
  url?: string;
  selector?: string;
  text?: string;
  query?: string;
  scrollAmount?: number;
}

export interface BrowserActionResult {
  success: boolean;
  data?: string | Record<string, any>;
  error?: string;
  screenshot?: string; // base64 encoded
}

class BrowserManager {
  private browser: Browser | null = null;
  private page: Page | null = null;

  async initialize(): Promise<void> {
    if (!this.browser) {
      this.browser = await chromium.launch({
        headless: true,
      });
    }
  }

  async getPage(): Promise<Page> {
    if (!this.browser) {
      await this.initialize();
    }

    if (!this.page) {
      this.page = await this.browser!.newPage();
      this.page.setViewportSize({ width: 1280, height: 720 });
    }

    return this.page;
  }

  async navigate(url: string): Promise<BrowserActionResult> {
    try {
      const page = await this.getPage();
      await page.goto(url, { waitUntil: 'networkidle' });
      return { success: true, data: `Navigated to ${url}` };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Navigation failed',
      };
    }
  }

  async click(selector: string): Promise<BrowserActionResult> {
    try {
      const page = await this.getPage();
      await page.click(selector);
      return { success: true, data: `Clicked element: ${selector}` };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Click failed',
      };
    }
  }

  async type(selector: string, text: string): Promise<BrowserActionResult> {
    try {
      const page = await this.getPage();
      await page.fill(selector, text);
      return { success: true, data: `Typed text: ${text}` };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Type failed',
      };
    }
  }

  async screenshot(): Promise<BrowserActionResult> {
    try {
      const page = await this.getPage();
      const buffer = await page.screenshot();
      const base64 = buffer.toString('base64');
      return { success: true, screenshot: base64 };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Screenshot failed',
      };
    }
  }

  async search(query: string): Promise<BrowserActionResult> {
    try {
      const page = await this.getPage();
      // Search on Google
      await page.goto(`https://www.google.com/search?q=${encodeURIComponent(query)}`, {
        waitUntil: 'networkidle',
      });

      // Extract search results
      const results = await page.locator('[data-sokoban-container] div[data-result-container]').allTextContents();

      return { success: true, data: { query, resultsCount: results.length } };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Search failed',
      };
    }
  }

  async scroll(scrollAmount: number): Promise<BrowserActionResult> {
    try {
      const page = await this.getPage();
      await page.evaluate((amount) => {
        window.scrollBy(0, amount);
      }, scrollAmount);
      return { success: true, data: `Scrolled by ${scrollAmount}px` };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Scroll failed',
      };
    }
  }

  async extractContent(selector?: string): Promise<BrowserActionResult> {
    try {
      const page = await this.getPage();
      let content: string;

      if (selector) {
        content = await page.locator(selector).textContent() || '';
      } else {
        content = await page.textContent('body') || '';
      }

      return { success: true, data: content };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Extract failed',
      };
    }
  }

  async execute(action: BrowserAction): Promise<BrowserActionResult> {
    switch (action.type) {
      case 'navigate':
        return this.navigate(action.url || '');
      case 'click':
        return this.click(action.selector || '');
      case 'type':
        return this.type(action.selector || '', action.text || '');
      case 'screenshot':
        return this.screenshot();
      case 'search':
        return this.search(action.query || '');
      case 'scroll':
        return this.scroll(action.scrollAmount || 300);
      case 'extract':
        return this.extractContent(action.selector);
      default:
        return { success: false, error: 'Unknown action type' };
    }
  }

  async close(): Promise<void> {
    if (this.page) {
      await this.page.close();
      this.page = null;
    }
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
    }
  }
}

// Singleton instance
let browserManager: BrowserManager | null = null;

export function getBrowserManager(): BrowserManager {
  if (!browserManager) {
    browserManager = new BrowserManager();
  }
  return browserManager;
}

export async function executeBrowserAction(action: BrowserAction): Promise<BrowserActionResult> {
  const manager = getBrowserManager();
  return manager.execute(action);
}
