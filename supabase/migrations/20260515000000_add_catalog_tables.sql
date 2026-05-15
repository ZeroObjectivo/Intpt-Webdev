-- Scholarship and UMak Coop catalog tables
-- Readable by authenticated users; writable only by admin/super_admin.

CREATE TABLE IF NOT EXISTS public.scholarship_catalog (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scholarship_type text NOT NULL,
    name text NOT NULL,
    details text NOT NULL,
    qualifications text,
    requirements text,
    created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT timezone('utc', now()),
    updated_at timestamptz NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS idx_scholarship_catalog_created_at ON public.scholarship_catalog(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scholarship_catalog_type ON public.scholarship_catalog(scholarship_type);

CREATE TABLE IF NOT EXISTS public.umak_coop_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    details text NOT NULL,
    price numeric(12, 2) NOT NULL CHECK (price >= 0),
    availability text NOT NULL DEFAULT 'Available',
    image_url text,
    created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT timezone('utc', now()),
    updated_at timestamptz NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS idx_umak_coop_items_created_at ON public.umak_coop_items(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_umak_coop_items_availability ON public.umak_coop_items(availability);

ALTER TABLE public.scholarship_catalog ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.umak_coop_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can read scholarship catalog" ON public.scholarship_catalog;
CREATE POLICY "Authenticated users can read scholarship catalog" ON public.scholarship_catalog
    FOR SELECT
    USING (auth.role() = 'authenticated');

DROP POLICY IF EXISTS "Authenticated users can read UMak Coop items" ON public.umak_coop_items;
CREATE POLICY "Authenticated users can read UMak Coop items" ON public.umak_coop_items
    FOR SELECT
    USING (auth.role() = 'authenticated');

DROP POLICY IF EXISTS "Admins can insert scholarship catalog" ON public.scholarship_catalog;
CREATE POLICY "Admins can insert scholarship catalog" ON public.scholarship_catalog
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND role IN ('admin', 'super_admin', 'superadmin')
        )
    );

DROP POLICY IF EXISTS "Admins can update scholarship catalog" ON public.scholarship_catalog;
CREATE POLICY "Admins can update scholarship catalog" ON public.scholarship_catalog
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND role IN ('admin', 'super_admin', 'superadmin')
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND role IN ('admin', 'super_admin', 'superadmin')
        )
    );

DROP POLICY IF EXISTS "Admins can delete scholarship catalog" ON public.scholarship_catalog;
CREATE POLICY "Admins can delete scholarship catalog" ON public.scholarship_catalog
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND role IN ('admin', 'super_admin', 'superadmin')
        )
    );

DROP POLICY IF EXISTS "Admins can insert UMak Coop items" ON public.umak_coop_items;
CREATE POLICY "Admins can insert UMak Coop items" ON public.umak_coop_items
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND role IN ('admin', 'super_admin', 'superadmin')
        )
    );

DROP POLICY IF EXISTS "Admins can update UMak Coop items" ON public.umak_coop_items;
CREATE POLICY "Admins can update UMak Coop items" ON public.umak_coop_items
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND role IN ('admin', 'super_admin', 'superadmin')
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND role IN ('admin', 'super_admin', 'superadmin')
        )
    );

DROP POLICY IF EXISTS "Admins can delete UMak Coop items" ON public.umak_coop_items;
CREATE POLICY "Admins can delete UMak Coop items" ON public.umak_coop_items
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND role IN ('admin', 'super_admin', 'superadmin')
        )
    );

DROP TRIGGER IF EXISTS set_scholarship_catalog_updated_at ON public.scholarship_catalog;
CREATE TRIGGER set_scholarship_catalog_updated_at
    BEFORE UPDATE ON public.scholarship_catalog
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS set_umak_coop_items_updated_at ON public.umak_coop_items;
CREATE TRIGGER set_umak_coop_items_updated_at
    BEFORE UPDATE ON public.umak_coop_items
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();
