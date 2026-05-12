-- Migration to implement automated "Internet Etiquette" filtering
-- Created for the Database Lead to enforce community standards globally

-- 1. Create the dictionary table for forbidden words
CREATE TABLE IF NOT EXISTS public.forbidden_words (
    word text PRIMARY KEY,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now())
);

-- 2. Add some initial sample words (Team can expand this list via Supabase UI)
INSERT INTO public.forbidden_words (word) VALUES 
('spam'), 
('scam'), 
('offensive1')
ON CONFLICT (word) DO NOTHING;

-- 3. The Sanitization Function
-- Scans content and replaces forbidden words with asterisks
CREATE OR REPLACE FUNCTION public.sanitize_etiquette()
RETURNS TRIGGER AS $$
DECLARE
    bad_regex text;
BEGIN
    -- Combine all forbidden words into one regex pattern: 'word1|word2|word3'
    -- In PostgreSQL regex, \y matches a word boundary
    SELECT string_agg('\y' || word || '\y', '|') INTO bad_regex FROM public.forbidden_words;

    -- If there are forbidden words defined, perform the replacement
    IF bad_regex IS NOT NULL THEN
        -- 'gi' flags: g = global (all occurrences), i = case insensitive
        NEW.content := regexp_replace(NEW.content, bad_regex, '****', 'gi');
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 4. Create trigger for the 'posts' table
DROP TRIGGER IF EXISTS trigger_sanitize_posts ON public.posts;
CREATE TRIGGER trigger_sanitize_posts
BEFORE INSERT OR UPDATE ON public.posts
FOR EACH ROW EXECUTE FUNCTION public.sanitize_etiquette();

-- 5. Create trigger for the 'comments' table
DROP TRIGGER IF EXISTS trigger_sanitize_comments ON public.comments;
CREATE TRIGGER trigger_sanitize_comments
BEFORE INSERT OR UPDATE ON public.comments
FOR EACH ROW EXECUTE FUNCTION public.sanitize_etiquette();
