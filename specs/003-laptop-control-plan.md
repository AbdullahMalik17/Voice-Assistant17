# Feature Specification: Whole Laptop Control

**Feature Branch**: `003-laptop-control`
**Created**: 2026-01-05
**Status**: Draft
**Goal**: Enable the Voice Assistant to fully control the host laptop's system, applications, and files via voice commands.

## Overview

This specification outlines the roadmap to transform the Voice Assistant into a comprehensive system controller, moving beyond simple API queries to deep OS integration.

## Roadmap

### Phase 1: Basic System Control (Completed)
*Goal: Control hardware and global system state.*
- [x] **Volume Control**: Set specific levels, mute/unmute, up/down.
- [x] **Media Control**: Play/Pause, Next/Prev Track, Stop.
- [x] **Brightness Control**: Adjust screen brightness (Windows).
- [x] **Power Management**: Shutdown, Restart, Sleep, Lock Screen.

### Phase 2: Application Management (Next Priority)
*Goal: Launch, close, and manage window states of applications.*
- [ ] **Advanced Launching**: Robust fuzzy matching for app names (e.g., "Open VS Code" -> `code`).
- [ ] **Window Management**: Minimize, Maximize, Snap to sides, Switch focus.
- [ ] **Process Management**: "Kill Chrome", "How much RAM is Discord using?".
- [ ] **App-Specific Context**: Detect active window to contextually handle "Close this".

### Phase 3: File System Operations
*Goal: Manage files and folders without a mouse/keyboard.*
- [ ] **Navigation**: "Go to Downloads folder", "Open Documents".
- [ ] **Search**: "Find the file named 'budget.xlsx'", "Where is 'notes.txt'?".
- [ ] **Operations**: "Create a new folder called 'Project'", "Delete this file".
- [ ] **Content**: "Read the last log file", "Summarize this PDF".

### Phase 4: GUI Automation (Deep Control)
*Goal: Control applications that have no API.*
- [ ] **Click & Scroll**: "Click the blue button", "Scroll down".
- [ ] **Keyboard Input**: "Type 'Hello World'", "Press Enter".
- [ ] **Screen Vision**: Use VLM (Vision Language Model) or OCR to "See" the screen and understand "Click on the Send button".

## Implementation Plan

### Immediate Steps (Phase 2 & 3)

1.  **Enhance `LaunchAppTool`**:
    -   Scan Start Menu/Applications folder to build a dynamic index of installed apps.
    -   Use `fuzzywuzzy` or similar for better name matching.

2.  **Implement `FileSystemTools`**:
    -   Create `FileSearchTool` (using `os.walk` or Windows Search Index).
    -   Create `FileOpTool` (Copy, Move, Delete, Rename).

3.  **Integrate `pycaw` (Windows Audio)**:
    -   Replace PowerShell volume hacks with `pycaw` for precise application-specific volume control (e.g., "Mute Spotify only").

4.  **Add `pyautogui` / `pywinauto`**:
    -   For window management (Focus, Minimize, Maximize).

## Dependencies

- `pycaw` (Core Audio Windows) - For advanced audio.
- `pywin32` - For low-level Windows API access.
- `fuzzywuzzy` / `python-Levenshtein` - For app name matching.
