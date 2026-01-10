# Comprehensive Testing Guide - Voice Assistant Enhancement

**Status**: Test Framework Ready
**Date**: 2026-01-10
**Coverage Target**: 80%+ for production code

---

## Testing Architecture

```
tests/
├── unit/                          # Unit tests (isolated components)
│   ├── services/
│   │   ├── test_slack_tools.py
│   │   ├── test_discord_tools.py
│   │   ├── test_notion_tools.py
│   │   ├── test_trello_tools.py
│   │   ├── test_llm_cache.py
│   │   ├── test_browser_automation.py
│   │   ├── test_entity_extractor.py
│   │   └── test_voice_commands.py
│   ├── agents/
│   │   └── test_tool_registry.py
│   └── memory/
│       └── test_conversation_summarizer.py
├── integration/                   # Integration tests (with real APIs)
│   ├── test_slack_integration.py
│   ├── test_discord_integration.py
│   ├── test_notion_integration.py
│   ├── test_trello_integration.py
│   ├── test_llm_caching_e2e.py
│   ├── test_streaming_e2e.py
│   ├── test_websocket_e2e.py
│   ├── test_browser_automation_e2e.py
│   └── test_summarization_e2e.py
├── performance/                   # Performance & load tests
│   ├── test_caching_performance.py
│   ├── test_websocket_load.py
│   ├── test_browser_automation_perf.py
│   └── test_concurrent_requests.py
├── conftest.py                    # Shared fixtures
└── requirements-test.txt          # Test dependencies
```

---

## Phase 1: Integration Tools Testing

### Unit Tests: Slack Tools

**File**: `tests/unit/services/test_slack_tools.py`

**Test Cases**:

```python
class TestSendSlackMessageTool:
    # ✅ Positive cases
    def test_send_message_to_channel(self):
        """Verify message sent to #channel"""
        # Setup: Mock token, channel
        # Execute: send_message(channel="#test", message="hello")
        # Assert: Returns success=True, message_ts set

    def test_send_message_to_user(self):
        """Verify direct message to user"""
        # Setup: Mock token, user_id
        # Execute: send_message(channel="@user123", message="hello")
        # Assert: message_ts is set, thread_ts None

    def test_send_threaded_reply(self):
        """Verify message sent to thread"""
        # Setup: Mock token, parent_ts
        # Execute: send_message(..., thread_ts="1234567.890")
        # Assert: message_ts set, in correct thread

    # ❌ Error cases
    def test_invalid_token_returns_error(self):
        """Verify error handling for bad token"""
        # Assert: Returns error, logs warning

    def test_channel_not_found(self):
        """Verify error handling for missing channel"""
        # Assert: Returns user-friendly error message

    def test_message_rate_limited(self):
        """Verify handling of rate limit errors"""
        # Assert: Raises retryable error

class TestListSlackChannelsTool:
    def test_list_all_channels(self):
        """Verify channel list includes required metadata"""
        # Assert: Returns list with name, id, topic, members_count

    def test_filter_by_keyword(self):
        """Verify channel filtering works"""
        # Setup: Channels: #general, #random, #engineering
        # Execute: list_channels(keyword="eng")
        # Assert: Returns #engineering only

class TestSearchSlackMessagesTool:
    def test_search_messages(self):
        """Verify message search works"""
        # Execute: search("python")
        # Assert: Returns matching messages with context

    def test_search_in_channel(self):
        """Verify channel filtering"""
        # Execute: search("test", channel="#dev")
        # Assert: Only matches from #dev
```

**Run Tests**:
```bash
pytest tests/unit/services/test_slack_tools.py -v
pytest tests/unit/services/test_slack_tools.py::TestSendSlackMessageTool -v
```

### Unit Tests: Discord Tools

**File**: `tests/unit/services/test_discord_tools.py`

**Test Cases**:

```python
class TestSendDiscordMessageTool:
    def test_send_to_text_channel(self):
        """Verify message sent to channel"""
        # Assert: webhook request made, correct format

    def test_send_with_rich_embed(self):
        """Verify embed formatting"""
        # Setup: title, description, color, fields
        # Assert: JSON structure correct

    def test_invalid_webhook_url(self):
        """Verify error handling"""
        # Assert: Returns clear error message

    def test_file_upload(self):
        """Verify file attachment works"""
        # Setup: file_path
        # Assert: multipart/form-data sent correctly
```

### Unit Tests: Notion Tools

**File**: `tests/unit/services/test_notion_tools.py`

**Test Cases**:

```python
class TestCreateNotionPageTool:
    def test_create_page_in_database(self):
        """Verify page creation with properties"""
        # Setup: database_id, title, properties
        # Assert: Returns page_id, url

    def test_property_type_handling(self):
        """Verify different property types"""
        # Test: Text, Select, Multi-select, Date, Checkbox
        # Assert: All types correctly formatted

    def test_invalid_database_id(self):
        """Verify error for bad database"""
        # Assert: Returns 404 error

class TestQueryNotionDatabaseTool:
    def test_query_with_filter(self):
        """Verify database filtering"""
        # Setup: filter conditions
        # Assert: Returns matching results

    def test_sorting(self):
        """Verify sort ordering"""
        # Execute: sort by date descending
        # Assert: Results in correct order
```

### Unit Tests: Trello Tools

**File**: `tests/unit/services/test_trello_tools.py`

**Test Cases**:

```python
class TestCreateTrelloCardTool:
    def test_create_card_with_description(self):
        """Verify card creation"""
        # Setup: list_id, name, description
        # Assert: Returns card_id, url

    def test_add_labels(self):
        """Verify label assignment"""
        # Execute: create_card(..., labels=["bug", "urgent"])
        # Assert: Labels appear on card

    def test_invalid_list_id(self):
        """Verify error handling"""
        # Assert: Returns meaningful error
```

---

## Phase 2: Performance & Optimization Testing

### Unit Tests: LLM Caching

**File**: `tests/unit/services/test_llm_cache.py`

**Test Cases**:

```python
class TestLLMCache:
    def test_cache_hit_returns_cached_response(self):
        """Verify cache hit logic"""
        # Setup: Cache with entry
        # Execute: get(query) -> should return cached
        # Assert: Response identical, timestamp fresh

    def test_cache_miss_returns_none(self):
        """Verify cache miss"""
        # Execute: get(query) with no entry
        # Assert: Returns None

    def test_ttl_expiration(self):
        """Verify entries expire"""
        # Setup: Entry with TTL=1s
        # Wait: 2 seconds
        # Execute: get(query)
        # Assert: Returns None (expired)

    def test_context_aware_caching(self):
        """Verify context impacts cache key"""
        # Setup: Same query, different contexts
        # Assert: Two separate cache entries

    def test_redis_backend(self):
        """Verify Redis integration"""
        # Setup: Redis backend
        # Execute: set/get with Redis
        # Assert: Data persists across processes

    def test_statistics_tracking(self):
        """Verify metrics collection"""
        # Setup: Multiple cache operations
        # Assert: Hit rate, miss count accurate
```

**Run Tests**:
```bash
pytest tests/unit/services/test_llm_cache.py -v
pytest tests/unit/services/test_llm_cache.py::TestLLMCache::test_cache_hit_returns_cached_response -v
```

### Performance Tests: Caching

**File**: `tests/performance/test_caching_performance.py`

**Test Cases**:

```python
def test_cache_hit_latency():
    """Verify cache hit speed <100ms"""
    # Setup: Warm cache with 1000 entries
    # Execute: get() for cached entry
    # Measure: Time to return
    # Assert: <100ms

def test_cache_miss_latency():
    """Verify cache miss overhead <10ms"""
    # Execute: get() for non-existent entry
    # Measure: Time to return None
    # Assert: <10ms

def test_concurrent_cache_access():
    """Verify thread-safe concurrent access"""
    # Execute: 100 threads accessing cache
    # Assert: No race conditions, correct values

def test_cache_eviction_under_memory_pressure():
    """Verify LRU eviction works"""
    # Setup: MAX_ENTRIES=1000
    # Execute: Add 1500 entries
    # Assert: Only 1000 remain, oldest removed

def test_redis_cache_performance():
    """Verify Redis latency acceptable"""
    # Execute: get/set with Redis
    # Measure: Latency
    # Assert: <50ms for redis operations
```

**Run Tests**:
```bash
pytest tests/performance/test_caching_performance.py -v --benchmark
```

### Integration Tests: Streaming

**File**: `tests/integration/test_streaming_e2e.py`

**Test Cases**:

```python
def test_streaming_response_chunks():
    """Verify chunks arrive correctly"""
    # Execute: Stream LLM response
    # Collect: All chunks
    # Assert: Chunks arrive in order, complete

def test_first_token_latency():
    """Verify first token latency <500ms"""
    # Measure: Time to first chunk
    # Assert: <500ms

def test_streaming_with_cache():
    """Verify streaming respects cache"""
    # Setup: Cached query
    # Execute: Request stream
    # Assert: Cached response yielded, not streamed

def test_streaming_error_handling():
    """Verify stream handles errors gracefully"""
    # Simulate: LLM error mid-stream
    # Assert: Error chunk sent, stream closed cleanly

def test_concurrent_streams():
    """Verify multiple concurrent streams"""
    # Execute: 10 simultaneous stream requests
    # Assert: All complete without interference
```

---

## Phase 3: Memory & Voice Commands Testing

### Unit Tests: Conversation Summarization

**File**: `tests/unit/memory/test_conversation_summarizer.py`

**Test Cases**:

```python
class TestConversationSummarizer:
    def test_extract_key_topics(self):
        """Verify topic extraction"""
        # Setup: Conversation turns with clear topics
        # Execute: extract_key_topics()
        # Assert: Contains "weather", "scheduling", etc.

    def test_extract_action_items(self):
        """Verify action identification"""
        # Setup: Turns mentioning send, create, schedule
        # Execute: extract_action_items()
        # Assert: Lists identified actions

    def test_summarization_threshold(self):
        """Verify summarize only when needed"""
        # Setup: 19 turns
        # Execute: should_summarize() with threshold=20
        # Assert: Returns False

        # Add 1 more turn -> 20 total
        # Assert: Returns True

    def test_llm_summarization(self):
        """Verify LLM-based summary generation"""
        # Setup: Mock LLM service
        # Execute: summarize_with_llm()
        # Assert: Summary is coherent, captures context

    def test_fallback_summarization(self):
        """Verify fallback when LLM unavailable"""
        # Setup: No LLM service
        # Execute: summarize_with_llm()
        # Assert: Uses _summarize_fallback(), returns valid summary

    def test_compressed_context_generation(self):
        """Verify context compression for prompts"""
        # Setup: 50 turns (25 old, 25 recent)
        # Execute: get_compressed_context(recent_turns_count=10)
        # Assert: Contains summary + last 10 turns
```

### Unit Tests: Entity Extraction

**File**: `tests/unit/services/test_entity_extractor.py`

**Test Cases**:

```python
class TestEnhancedEntityExtractor:
    def test_email_extraction(self):
        """Verify email detection"""
        text = "Contact john@example.com for help"
        entities = extractor.extract(text)
        assert entities[EntityType.EMAIL] == ["john@example.com"]

    def test_phone_extraction(self):
        """Verify phone number detection"""
        text = "Call me at (555) 123-4567"
        entities = extractor.extract(text)
        assert len(entities[EntityType.PHONE]) == 1

    def test_date_extraction(self):
        """Verify date parsing"""
        text = "Meeting on January 15, 2026"
        entities = extractor.extract(text)
        assert "January 15" in str(entities[EntityType.DATE])

    def test_spacy_ner(self):
        """Verify spaCy-based NER"""
        text = "John Smith works at Google in San Francisco"
        entities = extractor.extract(text)
        assert "John Smith" in entities[EntityType.PERSON]
        assert "Google" in entities[EntityType.ORGANIZATION]
        assert "San Francisco" in entities[EntityType.LOCATION]

    def test_fallback_when_spacy_unavailable(self):
        """Verify regex fallback works"""
        # Setup: SPACY_AVAILABLE = False
        # Execute: extract()
        # Assert: Still extracts emails, phones, URLs via regex

    def test_duplicate_removal(self):
        """Verify no duplicate entities"""
        text = "Email: test@example.com, contact: test@example.com"
        entities = extractor.extract(text)
        assert len(entities[EntityType.EMAIL]) == 1
```

### Unit Tests: Voice Commands

**File**: `tests/unit/services/test_voice_commands.py`

**Test Cases**:

```python
class TestAdvancedVoiceCommandParser:
    def test_search_command_parsing(self):
        """Verify search intent detection"""
        parsed = parser.parse("search for python tutorials")
        assert parsed.intent == CommandIntent.SEARCH
        assert parsed.parameters["query"] == "python tutorials"
        assert parsed.confidence > 0.9

    def test_send_message_parsing(self):
        """Verify message intent"""
        parsed = parser.parse("send a message to #general: Hello everyone")
        assert parsed.intent == CommandIntent.SEND_MESSAGE
        assert parsed.parameters["recipient"] == "#general"
        assert parsed.parameters["message"] == "Hello everyone"

    def test_fuzzy_matching(self):
        """Verify typo tolerance"""
        parsed = parser.parse("serch for python")  # typo: serch
        assert parsed.intent == CommandIntent.SEARCH
        assert parsed.confidence > 0.7

    def test_typo_correction(self):
        """Verify typo handling"""
        text = parser.handle_typos("serch for something")
        assert "search" in text.lower()

    def test_entity_extraction_from_command(self):
        """Verify parameter extraction"""
        parsed = parser.parse("send message to john@example.com: hello")
        entities = parser.extract_entities_from_command(parsed)
        assert "john@example.com" in entities["parameters"]

    def test_unknown_command(self):
        """Verify fallback for unmatched commands"""
        parsed = parser.parse("qwerty asdfgh zxcvbn")
        assert parsed.intent == CommandIntent.UNKNOWN
        assert parsed.confidence < 0.5

    def test_alternatives_tracking(self):
        """Verify alternative interpretations"""
        parsed = parser.parse("what is python", return_alternatives=True)
        assert len(parsed.alternatives) > 0
        assert parsed.alternatives[0][0] in CommandIntent.__members__.values()

    def test_parser_statistics(self):
        """Verify stats collection"""
        stats = parser.get_stats()
        assert stats["total_intents"] >= 7
        assert stats["total_patterns"] > 0
```

---

## Integration Testing

### End-to-End Tests: Full Workflow

**File**: `tests/integration/test_e2e_workflow.py`

**Scenario 1: Slack Message Workflow**

```python
def test_voice_command_to_slack_message():
    """Test: Listen → Parse → Send to Slack"""
    # 1. Voice input: "Send a message to #team: Project complete"
    # 2. Parse command → SEND_MESSAGE intent
    # 3. Extract entities → #team, "Project complete"
    # 4. Execute SendSlackMessageTool
    # 5. Verify message appears in Slack

    # Setup
    voice_input = "Send a message to #team: Project complete"

    # Parse
    parsed = voice_parser.parse(voice_input)
    assert parsed.intent == CommandIntent.SEND_MESSAGE

    # Execute
    result = slack_tool.execute(
        channel=parsed.parameters["recipient"],
        message=parsed.parameters["message"]
    )

    # Verify
    assert result["success"] == True
    assert result["message_ts"]
```

**Scenario 2: Browser Automation Workflow**

```python
def test_browser_automation_form_filling():
    """Test: Navigate → Extract Form → Fill → Submit"""
    # 1. Navigate to login page
    # 2. Wait for form elements (with retry/cache)
    # 3. Fill email field
    # 4. Fill password field
    # 5. Click submit button
    # 6. Wait for navigation to dashboard

    # Navigate (cached)
    result = browser.navigate("https://example.com/login")
    assert result["success"]

    # Fill form
    filled = browser.fill_form({
        "email": "test@example.com",
        "password": "secure123"
    })
    assert filled["success"]

    # Submit and verify navigation
    submitted = browser.wait_for_navigation()
    assert submitted["url"].contains("dashboard")
```

**Scenario 3: Conversation Summarization**

```python
def test_long_conversation_summarization():
    """Test: 25-turn conversation → auto-summarized"""
    # 1. Record 20 turns (no action)
    # 2. Turn 21 triggers summarization
    # 3. Summary generated and stored
    # 4. Recent turns kept in memory
    # 5. Old turns compressed into summary

    # Add 25 turns
    for i in range(25):
        summarizer.add_turn(
            user_input=f"Question {i}",
            assistant_response=f"Answer {i}"
        )

    # Check summary created at turn 20
    assert len(summarizer.summaries) >= 1
    latest_summary = summarizer.summaries[-1]
    assert latest_summary.turns_covered >= 20

    # Verify compression
    context = summarizer.get_compressed_context(all_turns)
    assert "Previous context:" in context  # Summary is there
    assert "Recent conversation:" in context  # Recent turns are there
```

---

## Load & Stress Testing

### WebSocket Load Test

**File**: `tests/performance/test_websocket_load.py`

```python
@pytest.mark.load
def test_websocket_concurrent_connections():
    """Test: 100 concurrent WebSocket connections"""
    # Setup: 100 clients
    # Execute: Each sends 10 messages
    # Measure: Latency, error rate
    # Assert: <1% error rate, latency <500ms

    async def client_session(session_id, client_id):
        async with websockets.connect(WS_URL) as ws:
            for i in range(10):
                await ws.send(json.dumps({
                    "type": "text",
                    "content": f"Test message {i} from client {client_id}"
                }))
                response = await ws.recv()
                assert json.loads(response)["success"]

    # Run 100 clients in parallel
    async def run_load_test():
        tasks = [
            client_session(f"session-{i}", i)
            for i in range(100)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze
        errors = [r for r in results if isinstance(r, Exception)]
        error_rate = len(errors) / 100
        assert error_rate < 0.01  # <1% error

    asyncio.run(run_load_test())

@pytest.mark.benchmark
def test_message_throughput():
    """Test: Maximum messages/second"""
    # Execute: Measure WebSocket throughput
    # Assert: >1000 messages/sec for single connection
```

### Browser Automation Performance

**File**: `tests/performance/test_browser_automation_perf.py`

```python
def test_navigation_caching_performance():
    """Test: Cached navigation 20-30x faster"""
    # First navigation
    start = time.time()
    result1 = browser.navigate("https://example.com")
    time1 = time.time() - start

    # Cached navigation
    start = time.time()
    result2 = browser.navigate("https://example.com")
    time2 = time.time() - start

    # Verify speedup
    speedup = time1 / time2
    assert speedup > 20  # 20-30x faster

    # Verify from cache
    metrics = browser.get_performance_metrics()
    assert metrics["navigation"]["cache_hits"] == 1

def test_selector_retry_success_rate():
    """Test: Retry logic improves success"""
    # Without retry: 70% success rate
    # With retry (3 attempts): 99% success rate

    results = []
    for _ in range(100):
        result = browser.wait_for_selector_with_retry(
            selector=".dynamic-element",
            timeout=5000,
            retries=3
        )
        results.append(result["success"])

    success_rate = sum(results) / len(results)
    assert success_rate > 0.95  # 95%+ success with retries
```

---

## Test Execution Plans

### Daily Test Suite (5 minutes)

```bash
# Run fast unit tests only
pytest tests/unit/ -v --tb=short -x

# Quick sanity check
pytest tests/unit/ -q --tb=no
```

### Weekly Test Suite (30 minutes)

```bash
# All unit + integration tests
pytest tests/unit/ tests/integration/ -v --tb=short

# With coverage
pytest tests/unit/ tests/integration/ --cov=src --cov-report=term-missing
```

### Release Test Suite (2 hours)

```bash
# Full test suite: unit + integration + performance + stress
pytest tests/ -v --benchmark --load --tb=long

# Generate full report
pytest tests/ \
  --cov=src \
  --cov-report=html \
  --cov-report=term-missing \
  --junitxml=test-results.xml \
  -v
```

### Pre-Deployment Checklist

```bash
# 1. Run all tests
pytest tests/ -q

# 2. Check coverage (target: 80%+)
pytest tests/ --cov=src --cov-report=term-missing | grep TOTAL

# 3. Security audit
pip audit

# 4. Code quality
black --check src/
flake8 src/
mypy src/

# 5. Performance baseline
pytest tests/performance/ --benchmark

# 6. Integration health check
pytest tests/integration/ -k "not requires_api_key"
```

---

## Acceptance Criteria

### Phase 1 (Integration Tools)
- [ ] All Slack/Discord/Notion/Trello tools have >90% unit test coverage
- [ ] Integration tests pass with real API keys
- [ ] Error handling verified for invalid inputs
- [ ] Rate limiting doesn't affect functionality

### Phase 2 (Performance)
- [ ] Cache hit rate 20-30%
- [ ] Cached responses <100ms latency
- [ ] First token streaming latency <500ms
- [ ] WebSocket handles 100+ concurrent users
- [ ] Browser cache provides 20-30x speedup for repeated URLs

### Phase 3 (Memory & Voice)
- [ ] Summarization triggers at correct threshold (20 turns)
- [ ] Entity extraction accuracy >85%
- [ ] Fuzzy matching handles 70%+ of typos
- [ ] Voice commands parsed correctly 95%+ of time

---

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest tests/ -v --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          files: ./coverage.xml
```

---

## Support

For test failures:
1. Check logs: `tail -f logs/voice_assistant.log`
2. Run with verbose output: `pytest -vv --tb=long`
3. Run specific test: `pytest tests/unit/services/test_slack_tools.py::TestSendSlackMessageTool::test_send_message_to_channel -vv`
4. Debug mode: `pytest --pdb` (drops to debugger on failure)

---

**Status**: ✅ TEST FRAMEWORK COMPLETE

Ready to execute comprehensive test suite across all phases.
