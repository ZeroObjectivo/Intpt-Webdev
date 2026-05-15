-- 1. Create Colleges & Institutes Table
CREATE TABLE IF NOT EXISTS public.colleges_institutes (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    name text NOT NULL UNIQUE,
    full_name text,
    type text NOT NULL CHECK (type IN ('College', 'Institute')),
    created_at timestamp with time zone DEFAULT now()
);

-- 2. Populate Colleges
INSERT INTO public.colleges_institutes (name, full_name, type) VALUES
('CLAS', 'College of Liberal Arts and Sciences', 'College'),
('CKHK', 'College of Human Kinetics', 'College'),
('CBFS', 'College of Business and Financial Sciences', 'College'),
('CCIS', 'College of Computing and Information Sciences', 'College'),
('CITE', 'College of Innovative Teacher Education', 'College'),
('HSU', 'Higher School ng UMak', 'College'),
('CGPP', 'College of Governance and Public Policy', 'College'),
('CCSE', 'College of Construction Sciences and Engineering', 'College'),
('CET', 'College of Engineering Technology', 'College'),
('CTHM', 'College of Tourism and Hospitality Management', 'College'),
('CCAPS', 'College of Continuing, Advanced and Professional Studies', 'College')
ON CONFLICT (name) DO NOTHING;

-- 3. Populate Schools and Institutes
INSERT INTO public.colleges_institutes (name, full_name, type) VALUES
('SOL', 'School of Law', 'Institute'),
('IAD', 'Institute of Allied Health Sciences', 'Institute'),
('IOA', 'Institute of Arts and Design', 'Institute'),
('IOP', 'Institute of Pharmacy', 'Institute'),
('ION', 'Institute of Nursing', 'Institute'),
('IIHS', 'Institute of Imaging and Health Sciences', 'Institute'),
('ITEST', 'Institute of Teacher Education and Special Training', 'Institute'),
('ISDNB', 'Institute of Sustainable Development and National Building', 'Institute'),
('IOPsy', 'Institute of Psychology', 'Institute'),
('ISW', 'Institute of Social Work', 'Institute'),
('IDEM', 'Institute of Disaster and Emergency Management', 'Institute')
ON CONFLICT (name) DO NOTHING;

-- 4. Enable RLS and set policies
ALTER TABLE public.colleges_institutes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access to colleges_institutes"
    ON public.colleges_institutes FOR SELECT
    USING (true);

CREATE POLICY "Admins can manage colleges_institutes"
    ON public.colleges_institutes FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role IN ('admin', 'super_admin')
    ));
