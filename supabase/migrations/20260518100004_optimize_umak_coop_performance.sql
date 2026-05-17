-- Optimize UMak Coop table for performance
CREATE INDEX IF NOT EXISTS idx_umak_coop_items_name_trgm ON public.umak_coop_items USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_umak_coop_items_category ON public.umak_coop_items (category);
CREATE INDEX IF NOT EXISTS idx_umak_coop_items_availability ON public.umak_coop_items (availability);
CREATE INDEX IF NOT EXISTS idx_umak_coop_items_price ON public.umak_coop_items (price);
CREATE INDEX IF NOT EXISTS idx_umak_coop_items_created_at ON public.umak_coop_items (created_at DESC);
