-- Migration to add event_title to posts table
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS event_title text;

COMMENT ON COLUMN public.posts.event_title IS 'Title/Name of the event for posts in the Events category.';
