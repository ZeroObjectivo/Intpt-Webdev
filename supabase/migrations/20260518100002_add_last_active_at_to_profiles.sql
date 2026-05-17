-- Add last_active_at to profiles table
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS last_active_at timestamp with time zone DEFAULT now();

-- Update existing profiles to have a last_active_at value
UPDATE public.profiles SET last_active_at = updated_at WHERE last_active_at IS NULL;
