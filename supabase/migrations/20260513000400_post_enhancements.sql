-- Migration for Post Enhancements and Community Features
-- 1. Add event_end_date to support event duration
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS event_end_date timestamp with time zone;

-- 2. Create reports table for flagging posts
CREATE TABLE IF NOT EXISTS public.reports (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    post_id uuid NOT NULL,
    reporter_id uuid NOT NULL,
    reason text NOT NULL,
    status text DEFAULT 'pending'::text,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
    CONSTRAINT reports_pkey PRIMARY KEY (id),
    CONSTRAINT reports_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.posts(id) ON DELETE CASCADE,
    CONSTRAINT reports_reporter_id_fkey FOREIGN KEY (reporter_id) REFERENCES public.profiles(id) ON DELETE CASCADE
);

-- Enable RLS on reports
ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to report
DROP POLICY IF EXISTS "Users can report posts" ON public.reports;
CREATE POLICY "Users can report posts" ON public.reports
FOR INSERT WITH CHECK (auth.uid() = reporter_id);

-- Only admins can view reports (assuming 'admin' or 'super_admin' roles)
DROP POLICY IF EXISTS "Admins can view reports" ON public.reports;
CREATE POLICY "Admins can view reports" ON public.reports
FOR SELECT USING (
    EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role IN ('admin', 'super_admin', 'content_moderator')
    )
);

-- 3. Comment on status cleanup for Buy & Sell
-- We don't need a migration for this as it's a frontend logic change, 
-- but we ensure the 'status' column exists and is flexible.
COMMENT ON COLUMN public.posts.status IS 'Status of the post (e.g., Available, Lost, Found). "Sold" removed from creation options per request.';
