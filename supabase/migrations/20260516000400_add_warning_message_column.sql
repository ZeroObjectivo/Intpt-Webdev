-- Add message column to warnings table to store the specific text sent to the user
ALTER TABLE public.warnings 
    ADD COLUMN IF NOT EXISTS message text;

-- Log schema update
INSERT INTO public.admin_logs (action_type, details) 
VALUES ('schema_update', 'Added message column to warnings table to store detailed administrative feedback.');
