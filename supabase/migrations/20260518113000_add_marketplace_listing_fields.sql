-- Add marketplace listing fields for Herons Business posts
ALTER TABLE public.posts
    ADD COLUMN IF NOT EXISTS product_name text;

ALTER TABLE public.posts
    ADD COLUMN IF NOT EXISTS listing_availability text;

-- Backfill existing marketplace-like rows when possible
UPDATE public.posts
SET listing_availability = 'Not Available'
WHERE listing_availability IS NULL
  AND lower(coalesce(status, '')) IN ('sold', 'out', 'out of stock', 'not available', 'unavailable');

UPDATE public.posts
SET listing_availability = 'Available'
WHERE listing_availability IS NULL;

ALTER TABLE public.posts
    ALTER COLUMN listing_availability SET DEFAULT 'Available';

ALTER TABLE public.posts
    DROP CONSTRAINT IF EXISTS posts_listing_availability_check;

ALTER TABLE public.posts
    ADD CONSTRAINT posts_listing_availability_check
    CHECK (listing_availability IN ('Available', 'Not Available'));

CREATE INDEX IF NOT EXISTS idx_posts_listing_availability
    ON public.posts(listing_availability);

COMMENT ON COLUMN public.posts.product_name IS
    'Optional product title for Herons Business marketplace posts.';

COMMENT ON COLUMN public.posts.listing_availability IS
    'Seller-defined availability for marketplace posts (Available or Not Available).';
