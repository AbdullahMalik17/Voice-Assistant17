'use client';

import { Moon, Sun } from 'lucide-react';
import { useEffect, useState } from 'react';

export function ThemeToggle() {
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');
  const [mounted, setMounted] = useState(false);

  // Only run on client side
  useEffect(() => {
    setMounted(true);

    // Get theme from document
    const isDark = document.documentElement.classList.contains('dark');
    setTheme(isDark ? 'dark' : 'light');
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);

    // Update document
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }

    // Save to localStorage
    localStorage.setItem('theme', newTheme);
  };

  if (!mounted) {
    // Return a placeholder with the same dimensions to prevent layout shift
    return (
      <div className="w-10 h-10 rounded-full" aria-hidden="true" />
    );
  }

  return (
    <button
      onClick={toggleTheme}
      className="relative p-2 rounded-full transition-all duration-300 hover:scale-110 btn-hover group"
      aria-label="Toggle theme"
    >
      <div className="relative w-6 h-6">
        {/* Sun icon (visible in dark mode) */}
        <Sun
          className={`absolute inset-0 w-6 h-6 text-neon-blue transition-all duration-500 ${
            theme === 'dark'
              ? 'rotate-0 scale-100 opacity-100'
              : 'rotate-90 scale-0 opacity-0'
          }`}
        />

        {/* Moon icon (visible in light mode) */}
        <Moon
          className={`absolute inset-0 w-6 h-6 text-gray-700 transition-all duration-500 ${
            theme === 'light'
              ? 'rotate-0 scale-100 opacity-100'
              : '-rotate-90 scale-0 opacity-0'
          }`}
        />
      </div>

      {/* Glow effect on hover (dark mode only) */}
      <div className="absolute inset-0 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300 dark:neon-glow" />
    </button>
  );
}
