-- Migration to support multiple images per post
-- This script transitions from a single image_url (text) to image_urls (text array)

-- 1. Add the new image_urls column
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS image_urls text[] DEFAULT '{}';

-- 2. Migrate existing data if image_urls is empty and image_url exists
UPDATE public.posts 
SET image_urls = ARRAY[image_url] 
WHERE image_url IS NOT NULL 
AND (image_urls IS NULL OR array_length(image_urls, 1) IS NULL);

-- 3. Optionally drop the old column (commented out for safety until verified)
-- ALTER TABLE public.posts DROP COLUMN IF EXISTS image_url;
