'use client';

export function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 px-4 py-3 max-w-4xl animate-slide-up">
      {/* AI Avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-neon-blue via-neon-purple to-neon-pink p-[2px] animate-pulse-glow">
        <div className="w-full h-full rounded-full bg-dark-bg dark:bg-black flex items-center justify-center">
          <span className="text-xs font-bold bg-gradient-to-r from-neon-blue to-neon-purple bg-clip-text text-transparent">
            AI
          </span>
        </div>
      </div>

      {/* Typing animation */}
      <div className="flex-1">
        <div className="inline-flex items-center gap-1.5 px-4 py-3 rounded-2xl glass border dark:border-neon-blue/20 card-shadow">
          <div className="flex gap-1">
            <div className="w-2 h-2 rounded-full bg-neon-blue animate-bounce" style={{ animationDelay: '0ms' }} />
            <div className="w-2 h-2 rounded-full bg-neon-purple animate-bounce" style={{ animationDelay: '150ms' }} />
            <div className="w-2 h-2 rounded-full bg-neon-pink animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
          <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">Thinking...</span>
        </div>
      </div>
    </div>
  );
}
