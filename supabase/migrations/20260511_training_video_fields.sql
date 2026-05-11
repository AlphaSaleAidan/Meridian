-- Add video tracking columns to training_lessons.
-- Run in Supabase SQL Editor after Aidan Pierce approval.

DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'training_lessons') THEN
    ALTER TABLE training_lessons ADD COLUMN IF NOT EXISTS video_url text;
    ALTER TABLE training_lessons ADD COLUMN IF NOT EXISTS video_duration_seconds integer;
    ALTER TABLE training_lessons ADD COLUMN IF NOT EXISTS has_video boolean DEFAULT false;
    ALTER TABLE training_lessons ADD COLUMN IF NOT EXISTS video_generated_at timestamptz;
    ALTER TABLE training_lessons ADD COLUMN IF NOT EXISTS video_model text;
    ALTER TABLE training_lessons ADD COLUMN IF NOT EXISTS video_soul_id text;
    ALTER TABLE training_lessons ADD COLUMN IF NOT EXISTS video_thumbnail_url text;

    CREATE INDEX IF NOT EXISTS idx_training_lessons_has_video
      ON training_lessons(has_video);
  END IF;
END $$;

-- If training_lessons table doesn't exist yet, create it.
CREATE TABLE IF NOT EXISTS training_lessons (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  lesson_id text NOT NULL,
  module_id text NOT NULL,
  title text NOT NULL,
  content text,
  key_takeaways text,
  portal_context text DEFAULT 'both',
  video_url text,
  video_duration_seconds integer,
  has_video boolean DEFAULT false,
  video_generated_at timestamptz,
  video_model text,
  video_soul_id text,
  video_thumbnail_url text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_training_lessons_lesson_id
  ON training_lessons(lesson_id);

CREATE INDEX IF NOT EXISTS idx_training_lessons_has_video
  ON training_lessons(has_video);

-- RLS: authenticated users can read training lessons
ALTER TABLE training_lessons ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Anyone can read training lessons" ON training_lessons;
CREATE POLICY "Anyone can read training lessons"
  ON training_lessons FOR SELECT
  USING (true);

DROP POLICY IF EXISTS "Service role can manage training lessons" ON training_lessons;
CREATE POLICY "Service role can manage training lessons"
  ON training_lessons FOR ALL
  USING (auth.uid() IS NOT NULL);

-- Supabase storage bucket for training videos
-- NOTE: Run this separately in Supabase dashboard or via API:
-- Create bucket: training-videos
-- Public: true
-- File size limit: 500MB
-- Allowed mime types: video/mp4, video/webm
