-- Migration to ensure forbidden_words table and policies exist
-- Date: May 14, 2026

CREATE TABLE IF NOT EXISTS public.forbidden_words (
    word text PRIMARY KEY,
    created_at timestamp with time zone DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.forbidden_words ENABLE ROW LEVEL SECURITY;

-- Allow admins to view forbidden words
DROP POLICY IF EXISTS "Admins can view forbidden words" ON public.forbidden_words;
CREATE POLICY "Admins can view forbidden words" ON public.forbidden_words
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND role IN ('admin', 'super_admin', 'content_moderator')
        )
    );

-- Allow admins to manage forbidden words
DROP POLICY IF EXISTS "Admins can manage forbidden words" ON public.forbidden_words;
CREATE POLICY "Admins can manage forbidden words" ON public.forbidden_words
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND role IN ('admin', 'super_admin')
        )
    );
