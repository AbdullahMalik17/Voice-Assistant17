# Audio Examples & Voice Commands

## Supported Voice Commands

This document provides examples of voice commands the assistant can understand and execute.

## Wake Word

**Default**: `"Hey Assistant"` or `"OK Assistant"`

To activate the assistant, say the wake word followed by your command:

```
"Hey Assistant, what's the weather today?"
"OK Assistant, open Spotify"
```

## Command Categories

### 1. System Control

#### Launch Applications

```
"Open Spotify"
"Launch Chrome"
"Start Calculator"
"Open Word"
"Launch Instagram"
"Open Photos app"
```

**How it works**:
- Intent: TASK_BASED / LAUNCH_APP
- Entity: APP_NAME ("Spotify", "Chrome", etc.)
- Action: Launches the specified application

#### System Information

```
"Check my CPU usage"
"How much memory am I using?"
"What's my disk space?"
"Show battery status"
"Check system temperature"
"What's my computer status?"
```

**How it works**:
- Intent: TASK_BASED / SYSTEM_STATUS
- Entity: STATUS_TYPE ("cpu", "memory", "disk", "battery")
- Action: Returns system metrics

### 2. Time & Productivity

#### Timers

```
"Set a timer for 5 minutes"
"Start a 30 second countdown"
"Timer for 1 hour"
"Set a cooking timer for 15 minutes"
```

**How it works**:
- Intent: TASK_BASED / SET_TIMER
- Entities: DURATION ("5 minutes" → 300 seconds)
- Slots: duration_seconds, label (optional)

#### Reminders

```
"Remind me to call mom tomorrow at 3pm"
"Set a reminder for my meeting in 1 hour"
"Remind me to take medicine at 9am"
```

**How it works**:
- Intent: TASK_BASED / SET_REMINDER
- Entities: DATETIME, TASK
- Slots: task, datetime

### 3. Email (Gmail Integration)

#### Check Email

```
"Check my email"
"Do I have any new messages?"
"Show my inbox"
"Read my latest email"
```

**How it works**:
- Intent: TASK_BASED / EMAIL_ACCESS
- Action: Lists recent emails from Gmail

#### Send Email

```
"Send email to john@example.com"
"Email my manager"
```

**Multi-turn dialogue example**:
```
User: "Send an email"
Assistant: "Who should I send this email to?"
User: "john@example.com"
Assistant: "What should the subject be?"
User: "Meeting Follow-up"
Assistant: "What should the email say?"
User: "Thanks for the meeting. Looking forward to our next discussion."
Assistant: "I'll send an email to john@example.com with subject 'Meeting Follow-up'. Is that okay?"
User: "Yes"
Assistant: "Email sent successfully."
```

#### Search Email

```
"Find emails from Sarah"
"Search for project alpha emails"
"Show emails about budget"
```

#### Schedule Email

```
"Schedule an email to john@example.com for tomorrow at 3pm"
"Send email to sarah@example.com next Monday at 9am"
"Schedule a follow-up email for Friday afternoon"
```

**Multi-turn dialogue example**:
```
User: "Schedule an email"
Assistant: "Who should I send this email to?"
User: "john@example.com"
Assistant: "When should I send this email?"
User: "Tomorrow at 3pm"
Assistant: "What should the subject be?"
User: "Project Update"
Assistant: "What should the email say?"
User: "Here's the latest status on the project. We're on track for the deadline."
Assistant: "I'll schedule an email to john@example.com with subject 'Project Update' to be sent tomorrow at 3pm. A calendar reminder has been created. Is that okay?"
User: "Yes"
Assistant: "Email scheduled successfully. You'll receive a calendar notification 10 minutes before it's sent."
```

**How it works**:
- Intent: TASK_BASED / EMAIL_SCHEDULE
- Entities: EMAIL, DATETIME, TASK
- Action: Creates calendar event and schedules email
- Background worker processes scheduled emails automatically
- Supports cancellation via "Cancel scheduled email to [recipient]"

**List scheduled emails**:
```
"Show my scheduled emails"
"What emails do I have scheduled?"
"List pending email schedules"
```

**Cancel scheduled email**:
```
"Cancel the email scheduled for john@example.com"
"Remove the scheduled email about project update"
```

### 4. Google Drive

#### Access Files

```
"Show my Google Drive files"
"List my documents"
"Open my Drive"
```

#### Search Files

```
"Find presentation files"
"Search for contract document"
"Show PDFs about marketing"
```

#### Download Files

```
"Download my resume"
"Get the budget spreadsheet"
```

### 5. Web Browsing

#### Navigate

```
"Navigate to google.com"
"Go to github.com"
"Open wikipedia.org"
"Browse to youtube.com"
```

**How it works**:
- Intent: TASK_BASED / BROWSER_AUTOMATION
- Entity: URL or site name
- Action: Opens browser and navigates

#### Search

```
"Search for Python tutorials"
"Look up weather in Tokyo"
"Google machine learning"
"Find information about AI"
```

**How it works**:
- Intent: TASK_BASED / WEB_SEARCH or INFORMATIONAL
- Entity: QUERY
- Action: Performs web search

#### Take Screenshot

```
"Take a screenshot"
"Capture the screen"
"Screenshot this page"
```

### 6. Information Queries

#### Weather

```
"What's the weather today?"
"Weather in New York"
"How's the weather tomorrow?"
"Is it going to rain today?"
"Temperature outside?"
```

**How it works**:
- Intent: INFORMATIONAL / GET_WEATHER
- Entities: LOCATION (optional), DATE (optional)
- Action: Queries weather API

#### Time & Date

```
"What time is it?"
"What's today's date?"
"What day is it?"
```

#### Calculations

```
"What's 25 times 34?"
"Calculate 15% of 200"
"Convert 50 miles to kilometers"
```

### 7. Conversational

#### Greetings

```
"Hello"
"Hi, how are you?"
"Good morning"
"Hey there"
"Good evening"
"How's it going?"
```

#### Small Talk

```
"Tell me a joke"
"How are you doing?"
"What can you do?"
"Thank you"
"That's great"
```

#### Language Support

```
"Assalamu alaikum" (Arabic greeting)
"Namaste" (Hindi greeting)
"Bonjour" (French greeting)
"Kaise ho" (Hindi - how are you)
```

## Complex Multi-Step Commands

The assistant can handle complex commands that require multiple steps:

### Example 1: Research & Share

```
"Search for Python best practices and email me the results"
```

**Execution Plan**:
1. web_search(query="Python best practices")
2. send_email(recipient=user_email, body=search_results)
   - **Safety check**: Requires confirmation before sending

**Dialogue**:
```
User: "Search for Python best practices and email me the results"
Assistant: [Executes search]
Assistant: "I found information about Python best practices. I'll send an email to you@example.com with these results. Is that okay?"
User: "Yes"
Assistant: "Email sent with the search results."
```

### Example 2: System Check & Navigate

```
"Check my system status and open Task Manager"
```

**Execution Plan**:
1. system_status(info_type="all")
2. launch_app(app_name="Task Manager")

### Example 3: Conditional Actions

```
"If my CPU is over 80%, close Chrome"
```

**Execution Plan**:
1. system_status(info_type="cpu")
2. Conditional: IF cpu > 80% THEN close_app(app_name="Chrome")

## Understanding & Slot Filling

### Incomplete Commands

If you provide incomplete information, the assistant will ask clarifying questions:

```
User: "Set a timer"
Assistant: "How long should I set the timer for?"
User: "10 minutes"
Assistant: "Timer set for 10 minutes."
```

```
User: "Send an email"
Assistant: "Who should I send this email to?"
User: "john@example.com"
Assistant: "What should the subject be?"
User: "Meeting notes"
Assistant: "What should the email say?"
User: "Here are the notes from today's meeting"
Assistant: "I'll send an email to john@example.com with subject 'Meeting notes'. Is that okay?"
```

### Ambiguous Commands

If the intent is unclear, the assistant will ask for clarification:

```
User: "Open it"
Assistant: "I'm not sure what you want to do. Did you mean:
1. Launch an application
2. Open a file
3. Navigate to a website"
User: "Launch an application"
Assistant: "Which application should I open?"
```

## Voice Command Best Practices

### 1. Be Clear and Specific

✅ **Good**: "Set a timer for 5 minutes"
❌ **Avoid**: "Timer" (too vague)

✅ **Good**: "Send email to john@example.com about the meeting"
❌ **Avoid**: "Email" (missing details)

### 2. Use Natural Language

The assistant understands natural speech patterns:

```
"Open Spotify" ✅
"Launch Spotify" ✅
"Start Spotify" ✅
"Can you open Spotify please?" ✅
"I want to listen to music on Spotify" ✅
```

### 3. Provide Context

✅ **Good**: "Remind me to call mom tomorrow at 3pm"
❌ **Less Good**: "Reminder"

✅ **Good**: "Search for machine learning tutorials"
❌ **Less Good**: "Search" (what to search for?)

### 4. One Command at a Time

For complex tasks, break them into steps or let the assistant guide you:

```
Multi-step approach:
User: "Search for Python tutorials and email them to me"
Assistant: [Handles both steps with confirmation]

Guided approach:
User: "Send an email"
Assistant: "Who should I send this email to?"
User: "john@example.com"
[Continues dialogue...]
```

## Safety & Confirmations

Certain actions require confirmation for safety:

### High-Risk Actions (Always Confirm)

- **Sending emails/messages**
- **Deleting files/folders**
- **Sharing files**
- **Making purchases**
- **Posting on social media**

**Example**:
```
User: "Send this document to everyone on my team"
Assistant: "I'll send document.pdf to 15 team members. This is a sensitive action. To confirm, please say 'confirm send email'"
User: "confirm send email"
Assistant: "Document sent to all team members."
```

### Medium-Risk Actions (Detailed Confirmation)

- **Creating/modifying files**
- **Installing applications**
- **Changing system settings**

**Example**:
```
User: "Delete the temporary files"
Assistant: "I'm about to delete 47 temporary files (total 2.3GB). Is that okay?"
User: "Yes"
Assistant: "Files deleted successfully."
```

### Low-Risk Actions (No Confirmation)

- **Checking information**
- **Opening applications**
- **Setting timers**
- **Searching**

## Error Handling

### When Commands Fail

```
User: "Open Microsoft Excel"
Assistant: "I couldn't find Microsoft Excel. Did you mean:
1. Open Excel (if installed)
2. Open Google Sheets
3. Open another application"
```

### When APIs Are Down

```
User: "What's the weather?"
Assistant: "I'm unable to fetch weather information right now. The weather service is temporarily unavailable. Would you like me to try again in a moment?"
```

### When Permissions Are Missing

```
User: "Check my email"
Assistant: "I don't have permission to access your Gmail. Would you like to grant access? You'll need to authenticate with Google."
```

## Audio Quality Tips

For best recognition accuracy:

1. **Speak clearly** at a normal pace
2. **Reduce background noise** when possible
3. **Speak within 1-5 meters** of the microphone
4. **Avoid covering the microphone**
5. **Wait for the wake word confirmation** before speaking
6. **Pause briefly** after the wake word

### Good Environment

- Quiet room (background <40dB)
- 1-3 meters from microphone
- Clear enunciation
- Normal speaking pace

**Expected WER**: 3-5%

### Challenging Environment

- Moderate noise (50-60dB)
- 5+ meters from microphone
- Fast speaking or heavy accent
- Background music

**Expected WER**: 10-15%

With audio preprocessing enabled, WER improves by 6-7 percentage points in noisy environments.

## Example Conversations

### Conversation 1: Productivity

```
User: "Hey Assistant"
Assistant: [Wake word detected]

User: "Set a timer for 25 minutes and open Spotify"
Assistant: "Timer set for 25 minutes. Opening Spotify."

[25 minutes later]
Assistant: "Your 25-minute timer is complete."
```

### Conversation 2: Email Workflow

```
User: "Hey Assistant"
Assistant: [Wake word detected]

User: "Check my email"
Assistant: "You have 3 new emails:
1. From Sarah: Meeting Agenda
2. From john@example.com: Project Update
3. From LinkedIn: Weekly Job Alerts"

User: "Read the first one"
Assistant: "Email from Sarah, subject: Meeting Agenda.
Body: Hi team, here's the agenda for tomorrow's meeting..."

User: "Reply and say I'll be there"
Assistant: "I'll send a reply to Sarah saying 'I'll be there'. Is that okay?"

User: "Yes"
Assistant: "Reply sent successfully."
```

### Conversation 3: Research Task

```
User: "OK Assistant"
Assistant: [Wake word detected]

User: "I need information about TypeScript best practices"
Assistant: "I'll search for TypeScript best practices."
[Searches web]
Assistant: "I found several resources about TypeScript best practices. Would you like me to:
1. Summarize the key points
2. Email you the links
3. Open the top result in your browser"

User: "Summarize the key points"
Assistant: "Here are the key TypeScript best practices:
1. Use strict mode for type safety
2. Avoid using 'any' type
3. Leverage interfaces and type aliases
4. Use union types for flexibility
5. Enable strict null checks
Would you like more details on any of these?"

User: "Email me the full information"
Assistant: "I'll email you the complete TypeScript best practices information. Is that okay?"

User: "Yes"
Assistant: "Email sent to your address."
```

## Testing Voice Commands

To test the audio pipeline without the full assistant:

```bash
# Generate test audio files
python tests/fixtures/audio_fixtures.py

# Run integration tests
pytest tests/integration/test_audio_pipeline.py -v

# Test specific components
python -c "from src.services.entity_extractor import EntityExtractor; \
           e = EntityExtractor(); \
           print(e.extract('Set a timer for 5 minutes'))"
```

## Voice Command Reference Card

Keep this handy for quick reference:

| Category | Example Command |
|----------|----------------|
| **Apps** | "Open [app name]" |
| **System** | "Check my [cpu/memory/disk/battery]" |
| **Timer** | "Set a timer for [duration]" |
| **Email** | "Check my email", "Send email to [address]" |
| **Drive** | "Show my Drive files", "Find [filename]" |
| **Browser** | "Navigate to [url]", "Search for [query]" |
| **Weather** | "What's the weather in [location]?" |
| **Info** | "What's [question]?" |
| **Chat** | "Hello", "How are you?", "Tell me a joke" |

## Troubleshooting

### Command Not Recognized

**Symptom**: Assistant doesn't understand your command

**Solutions**:
1. Speak more clearly
2. Rephrase the command
3. Break into smaller steps
4. Check if the command is supported

### Low Confidence

**Symptom**: "I'm not sure what you want to do"

**Solutions**:
1. Be more specific
2. Provide more context
3. Use simpler phrasing
4. Reduce background noise

### Action Blocked

**Symptom**: "This action is not allowed"

**Solutions**:
1. Check safety guardrails
2. Verify permissions
3. Try an alternative approach
4. Contact administrator

For more help, see [troubleshooting.md](troubleshooting.md)
