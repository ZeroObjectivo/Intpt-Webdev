-- Add category column to umak_coop_items table
ALTER TABLE public.umak_coop_items ADD COLUMN IF NOT EXISTS category text DEFAULT 'Other';

-- Update existing items to 'Other' if they don't have a category
UPDATE public.umak_coop_items SET category = 'Other' WHERE category IS NULL;
