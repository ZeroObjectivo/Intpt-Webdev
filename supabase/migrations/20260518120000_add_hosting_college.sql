-- Migration to add hosting_college to posts table
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS hosting_college text;

COMMENT ON COLUMN public.posts.hosting_college IS 'The specific college or institute hosting an event.';
