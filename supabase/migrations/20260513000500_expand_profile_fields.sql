-- Migration to expand profile fields for Profile Settings
ALTER TABLE public.profiles 
ADD COLUMN IF NOT EXISTS contact_number text,
ADD COLUMN IF NOT EXISTS contact_privacy text DEFAULT 'public',
ADD COLUMN IF NOT EXISTS college text,
ADD COLUMN IF NOT EXISTS course text,
ADD COLUMN IF NOT EXISTS level text,
ADD COLUMN IF NOT EXISTS bio text;

-- Comment for clarity
COMMENT ON COLUMN public.profiles.contact_privacy IS 'Privacy setting for contact number: "public" or "only_me"';
