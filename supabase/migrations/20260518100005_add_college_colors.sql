-- Add color column to colleges_institutes table
ALTER TABLE public.colleges_institutes ADD COLUMN IF NOT EXISTS color text DEFAULT '#64748B';

-- Seed initial colors based on existing design system
UPDATE public.colleges_institutes SET color = '#0891B2' WHERE name = 'CCIS';
UPDATE public.colleges_institutes SET color = '#166534' WHERE name = 'CBFS';
UPDATE public.colleges_institutes SET color = '#9A3412' WHERE name = 'CTHM';
UPDATE public.colleges_institutes SET color = '#1E40AF' WHERE name IN ('CLAS', 'CAS');
UPDATE public.colleges_institutes SET color = '#9F1239' WHERE name IN ('CON', 'ION');
UPDATE public.colleges_institutes SET color = '#5B21B6' WHERE name IN ('COE', 'CET');
UPDATE public.colleges_institutes SET color = '#334155' WHERE name = 'HSU';
UPDATE public.colleges_institutes SET color = '#854D0E' WHERE name = 'CHK';
UPDATE public.colleges_institutes SET color = '#3730A3' WHERE name = 'CGPP';
UPDATE public.colleges_institutes SET color = '#0F766E' WHERE name = 'CCSE';
UPDATE public.colleges_institutes SET color = '#BE123C' WHERE name = 'CITE';
UPDATE public.colleges_institutes SET color = '#4F46E5' WHERE name = 'CCAPS';
UPDATE public.colleges_institutes SET color = '#001035' WHERE name = 'SOL';
UPDATE public.colleges_institutes SET color = '#EC4899' WHERE name = 'IAD';
UPDATE public.colleges_institutes SET color = '#06B6D4' WHERE name = 'IOA';
UPDATE public.colleges_institutes SET color = '#F59E0B' WHERE name = 'IOP';
UPDATE public.colleges_institutes SET color = '#10B981' WHERE name = 'IIHS';
UPDATE public.colleges_institutes SET color = '#8B5CF6' WHERE name = 'IOPsy';
UPDATE public.colleges_institutes SET color = '#7C3AED' WHERE name = 'IDEM';
UPDATE public.colleges_institutes SET color = '#DB2777' WHERE name = 'ISW';
