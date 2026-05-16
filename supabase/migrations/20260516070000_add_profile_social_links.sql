-- Add profile social links table for public profile linktree support
CREATE TABLE IF NOT EXISTS public.profile_social_links (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    platform text NOT NULL CHECK (platform IN ('facebook', 'instagram')),
    url text NOT NULL,
    position integer NOT NULL CHECK (position BETWEEN 1 AND 3),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT profile_social_links_profile_url_key UNIQUE (profile_id, url),
    CONSTRAINT profile_social_links_profile_position_key UNIQUE (profile_id, position)
);

CREATE INDEX IF NOT EXISTS profile_social_links_profile_id_idx
    ON public.profile_social_links (profile_id);

CREATE OR REPLACE TRIGGER set_updated_at_profile_social_links
    BEFORE UPDATE ON public.profile_social_links
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

ALTER TABLE public.profile_social_links ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Social links are viewable by everyone"
    ON public.profile_social_links
    FOR SELECT
    USING (true);

CREATE POLICY "Users can insert their own social links"
    ON public.profile_social_links
    FOR INSERT
    WITH CHECK (auth.uid() = profile_id);

CREATE POLICY "Users can update their own social links"
    ON public.profile_social_links
    FOR UPDATE
    USING (auth.uid() = profile_id);

CREATE POLICY "Users can delete their own social links"
    ON public.profile_social_links
    FOR DELETE
    USING (auth.uid() = profile_id);
