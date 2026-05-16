-- Expand profile social links to support per-link visibility and additional platforms
ALTER TABLE public.profile_social_links
    ADD COLUMN IF NOT EXISTS visibility text;

UPDATE public.profile_social_links
SET visibility = 'public'
WHERE visibility IS NULL;

ALTER TABLE public.profile_social_links
    ALTER COLUMN visibility SET DEFAULT 'public',
    ALTER COLUMN visibility SET NOT NULL;

ALTER TABLE public.profile_social_links
    DROP CONSTRAINT IF EXISTS profile_social_links_platform_check;

ALTER TABLE public.profile_social_links
    ADD CONSTRAINT profile_social_links_platform_check
    CHECK (platform IN ('facebook', 'instagram', 'tiktok', 'linkedin', 'discord'));

ALTER TABLE public.profile_social_links
    DROP CONSTRAINT IF EXISTS profile_social_links_visibility_check;

ALTER TABLE public.profile_social_links
    ADD CONSTRAINT profile_social_links_visibility_check
    CHECK (visibility IN ('public', 'only_me'));
