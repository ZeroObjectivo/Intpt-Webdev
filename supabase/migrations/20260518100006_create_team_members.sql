-- Team members table for the landing page "Meet the Team" section
CREATE TABLE IF NOT EXISTS public.team_members (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name text NOT NULL,
    role text NOT NULL DEFAULT '',
    photo_url text,
    display_order integer NOT NULL DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Allow service role full access
ALTER TABLE public.team_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role can manage team members"
    ON public.team_members
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Anyone can view team members"
    ON public.team_members
    FOR SELECT
    USING (true);
