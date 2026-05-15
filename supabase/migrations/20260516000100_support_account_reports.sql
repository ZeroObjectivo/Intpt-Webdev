-- Update reports table to support account reports
ALTER TABLE public.reports 
    ALTER COLUMN post_id DROP NOT NULL,
    ADD COLUMN IF NOT EXISTS reported_user_id uuid REFERENCES public.profiles(id) ON DELETE CASCADE;

-- Add a constraint to ensure either post_id or reported_user_id is provided, but not both or neither.
ALTER TABLE public.reports 
    ADD CONSTRAINT reports_target_check 
    CHECK (
        (post_id IS NOT NULL AND reported_user_id IS NULL) OR 
        (post_id IS NULL AND reported_user_id IS NOT NULL)
    );

-- Log the schema update
INSERT INTO public.admin_logs (action_type, details) 
VALUES ('schema_update', 'Updated reports table to support reporting users (reported_user_id).');
