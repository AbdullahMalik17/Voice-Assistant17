'use client';

import { useState } from 'react';
import { ConversationHistory } from './ConversationHistory';
import { ConversationSearch } from './ConversationSearch';

interface ConversationSidebarProps {
  userId?: string;
  onSelectConversation?: (sessionId: string) => void;
  currentSessionId?: string;
  isOpen: boolean;
  onClose: () => void;
}

type TabType = 'history' | 'search';

export function ConversationSidebar({
  userId = 'default',
  onSelectConversation,
  currentSessionId,
  isOpen,
  onClose,
}: ConversationSidebarProps) {
  const [activeTab, setActiveTab] = useState<TabType>('history');

  if (!isOpen) {
    return null;
  }

  return (
    <>
      {/* Overlay for mobile */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
        onClick={onClose}
      />

      {/* Sidebar */}
      <div className="fixed lg:relative inset-y-0 left-0 w-full sm:w-80 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 z-50 flex flex-col">
        {/* Header with Close Button */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold">History</h2>
          <button
            onClick={onClose}
            className="lg:hidden text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setActiveTab('history')}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === 'history'
                ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
            }`}
          >
            <div className="flex items-center justify-center gap-2">
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span>History</span>
            </div>
          </button>

          <button
            onClick={() => setActiveTab('search')}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === 'search'
                ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
            }`}
          >
            <div className="flex items-center justify-center gap-2">
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <span>Search</span>
            </div>
          </button>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'history' ? (
            <ConversationHistory
              userId={userId}
              onSelectConversation={onSelectConversation}
              currentSessionId={currentSessionId}
            />
          ) : (
            <ConversationSearch
              userId={userId}
              onSelectResult={onSelectConversation}
            />
          )}
        </div>
      </div>
    </>
  );
}
