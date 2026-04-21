'use client';

import React from 'react';
import { useTheme } from '@/context/ThemeContext';

/**
 * ThemeToggle Component
 * Allows users to manually toggle between light and dark modes
 */
export const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      className="theme-toggle"
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      title={`Current theme: ${theme}`}
    >
      {theme === 'light' ? '🌙' : '☀️'}
    </button>
  );
};

export default ThemeToggle;
