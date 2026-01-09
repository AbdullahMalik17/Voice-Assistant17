-- Conversation Turns Table
-- Stores individual conversation turns (user input + assistant response)

CREATE TABLE IF NOT EXISTS public.conversation_turns (
  turn_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES public.conversation_sessions(session_id) ON DELETE CASCADE,
  user_input TEXT NOT NULL,
  assistant_response TEXT NOT NULL,
  intent TEXT,
  intent_confidence REAL DEFAULT 0.0,
  entities JSONB DEFAULT '{}'::jsonb,
  metadata JSONB DEFAULT '{}'::jsonb,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE public.conversation_turns ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Users can only access turns from their own sessions
CREATE POLICY "Users can view own turns"
  ON public.conversation_turns
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.conversation_sessions
      WHERE session_id = conversation_turns.session_id
      AND user_id = auth.uid()
    )
  );

CREATE POLICY "Users can create own turns"
  ON public.conversation_turns
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.conversation_sessions
      WHERE session_id = conversation_turns.session_id
      AND user_id = auth.uid()
    )
  );

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversation_turns_session_id
  ON public.conversation_turns(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_turns_timestamp
  ON public.conversation_turns(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_turns_intent
  ON public.conversation_turns(intent);

-- Full-text search index for user_input and assistant_response
CREATE INDEX IF NOT EXISTS idx_conversation_turns_search
  ON public.conversation_turns
  USING gin(to_tsvector('english', user_input || ' ' || assistant_response));

-- Grant permissions
GRANT ALL ON public.conversation_turns TO postgres, service_role;
GRANT SELECT, INSERT ON public.conversation_turns TO authenticated;
