-- supabase/migrations/20260518100001_seed_colleges_and_courses.sql
-- This script seeds the initial data for colleges and their corresponding courses.

-- Clear existing data to prevent duplicates on re-run
-- TRUNCATE TABLE public.courses RESTART IDENTITY CASCADE;
-- TRUNCATE TABLE public.colleges_institutes RESTART IDENTITY CASCADE;

-- Insert Colleges and Institutes
INSERT INTO public.colleges_institutes (name, full_name, type) VALUES
    ('CCAPS', 'College of Continuing, Advanced and Professional Studies', 'College'),
    ('IAD', 'Institute of Arts and Design', 'Institute'),
    ('CBFS', 'College of Business and Financial Science', 'College'),
    ('IOA', 'Institute of Accountancy', 'Institute'),
    ('CCIS', 'College of Computing and Information Science', 'College'),
    ('CCSE', 'College of Construction Sciences and Engineering', 'College'),
    ('CHK', 'College of Human Kinetics', 'College'),
    ('CGPP', 'College of Governance and Public Policy', 'College'),
    ('ION', 'Institute of Nursing', 'Institute'),
    ('IOP', 'Institute of Pharmacy', 'Institute'),
    ('IIHS', 'Institute of Imaging Health Sciences', 'Institute'),
    ('CITE', 'College of Innovative Teacher Education', 'College'),
    ('IOPsy', 'Institute of Psychology', 'Institute'),
    ('CTHM', 'College of Tourism and Hospitality Management', 'College'),
    ('IDEM', 'Institute for Disaster and Emergency Management', 'Institute'),
    ('ISW', 'Institute for Social Work', 'Institute'),
    ('CET', 'College of Engineering Technology', 'College'),
    ('SOL', 'School of Law', 'School'),
    ('HSU', 'Higher School ng UMak', 'School')
ON CONFLICT (name) DO NOTHING;

-- Insert Courses
-- Note: This uses a CTE (Common Table Expression) to look up college IDs by name.
WITH college_ids AS (
    SELECT id, name FROM public.colleges_institutes
)
INSERT INTO public.courses (college_id, name, program_type, major) VALUES
-- CCAPS
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Bachelor of Arts in Political Science', 'Undergraduate Programs', 'Local Government Administration'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Bachelor in Automotive Technology', 'Undergraduate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Bachelor in Industrial Facilities Technology Management', 'Undergraduate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Bachelor of Science in Business Administration', 'Undergraduate Programs', 'Human Resource Development Management'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Bachelor of Science in Entrepreneurship', 'Undergraduate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Certificate in Barangay Governance', 'Certificate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Certificate in Katarungang Pambarangay and Alternative Dispute Resolution', 'Certificate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Diploma in Development Management and Governance', 'Diploma Program', NULL),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master of Arts in Education', 'Masters Programs', 'Administration and Supervision'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master of Arts in Education', 'Masters Programs', 'Guidance and Counselling'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master of Arts in Innovative Education', 'Masters Programs', 'Biology'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master of Arts in Innovative Education', 'Masters Programs', 'Business Education'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master of Arts in Innovative Education', 'Masters Programs', 'Chemistry'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master of Arts in Innovative Education', 'Masters Programs', 'Computer'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master of Arts in Innovative Education', 'Masters Programs', 'Filipino'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master of Arts in Innovative Education', 'Masters Programs', 'General Science'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master of Arts in Innovative Education', 'Masters Programs', 'Physics'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master of Arts in Innovative Education', 'Masters Programs', 'Social Science'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master of Arts in Innovative Education', 'Masters Programs', 'Special Education'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master of Arts in Special Education', 'Masters Programs', 'Autism and Mental Retardism'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master of Arts in Special Education', 'Masters Programs', 'Early Childhood Education'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master of Arts in Nursing', 'Masters Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master in Business Administration', 'Masters Programs', 'Building Property Management'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master in Business Administration', 'Masters Programs', 'Entrepreneurship'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master in Business Administration', 'Masters Programs', 'Healthcare Management'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master in Development Management and Governance', 'Masters Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master in Public Administration', 'Masters Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master in Public Administration', 'Masters Programs', 'Local Governance'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Master of Science in Radiologic Technology', 'Masters Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Doctor of Education', 'Doctorate Programs', 'Educational Management'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Doctor of Philosophy in Special Education', 'Doctorate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Doctor of Philosophy in Leadership', 'Doctorate Programs', 'Business Track'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Doctor of Philosophy in Leadership', 'Doctorate Programs', 'Education Track'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Doctor of Philosophy in Leadership', 'Doctorate Programs', 'Public Management Track'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Doctor of Public Administration', 'Doctorate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Executive Doctorate in Leadership', 'Doctorate Programs', 'Business Track'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Executive Doctorate in Leadership', 'Doctorate Programs', 'Education Track'),
((SELECT id FROM college_ids WHERE name = 'CCAPS'), 'Executive Doctorate in Leadership', 'Doctorate Programs', 'Public Management Track'),
-- IAD
((SELECT id FROM college_ids WHERE name = 'IAD'), 'Bachelor in Multimedia Arts', 'Undergraduate Programs', 'Animation'),
((SELECT id FROM college_ids WHERE name = 'IAD'), 'Bachelor in Multimedia Arts', 'Undergraduate Programs', 'Film Production'),
((SELECT id FROM college_ids WHERE name = 'IAD'), 'Associate in Customer Service Communication', 'Undergraduate Programs', NULL),
-- CBFS
((SELECT id FROM college_ids WHERE name = 'CBFS'), 'Bachelor of Science in Business Administration', 'Undergraduate Programs', 'Building and Property Management'),
((SELECT id FROM college_ids WHERE name = 'CBFS'), 'Bachelor of Science in Business Administration', 'Undergraduate Programs', 'Supply Management'),
((SELECT id FROM college_ids WHERE name = 'CBFS'), 'Bachelor of Science in Entrepreneurial Management', 'Undergraduate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CBFS'), 'Bachelor of Science in Business Administration', 'Undergraduate Programs', 'Marketing Management'),
((SELECT id FROM college_ids WHERE name = 'CBFS'), 'Bachelor of Science in Office Administration', 'Undergraduate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CBFS'), 'Bachelor of Science in Business Administration', 'Undergraduate Programs', 'Human Resource Management'),
((SELECT id FROM college_ids WHERE name = 'CBFS'), 'Bachelor of Science in Financial Management', 'Undergraduate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CBFS'), 'Associate in Building and Property Management', 'Associate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CBFS'), 'Associate in Supply Management', 'Associate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CBFS'), 'Associate in Entrepreneurship', 'Associate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CBFS'), 'Associate in Sales Management', 'Associate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CBFS'), 'Associate in Office Management Technology', 'Associate Programs', NULL),
-- IOA
((SELECT id FROM college_ids WHERE name = 'IOA'), 'Bachelor of Science in Accountancy (BSA)', 'Undergraduate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'IOA'), 'Bachelor of Science in Management Accounting (BSMA)', 'Undergraduate Programs', NULL),
-- CCIS
((SELECT id FROM college_ids WHERE name = 'CCIS'), 'Bachelor of Science in Computer Science', 'Undergraduate Programs', 'Application Development Elective Track'),
((SELECT id FROM college_ids WHERE name = 'CCIS'), 'Bachelor of Science in Information Technology', 'Undergraduate Programs', 'Information and Network Security Elective Track'),
((SELECT id FROM college_ids WHERE name = 'CCIS'), 'Diploma in Application Development', 'Diploma Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CCIS'), 'Diploma in Computer Network Administration', 'Diploma Programs', NULL),
-- CCSE
((SELECT id FROM college_ids WHERE name = 'CCSE'), 'Bachelor of Science in Civil Engineering', 'Undergraduate Programs', 'Construction Engineering and Management'),
-- CHK
((SELECT id FROM college_ids WHERE name = 'CHK'), 'Bachelor of Science in Exercise and Sports Science', 'Undergraduate Programs', 'Fitness and Sports Management'),
-- CGPP
((SELECT id FROM college_ids WHERE name = 'CGPP'), 'Bachelor of Arts in Political Science', 'Undergraduate Programs', 'Paralegal Studies'),
((SELECT id FROM college_ids WHERE name = 'CGPP'), 'Bachelor of Arts in Political Science', 'Undergraduate Programs', 'Policy Management'),
-- ION
((SELECT id FROM college_ids WHERE name = 'ION'), 'Master of Arts in Nursing', 'Masters Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'ION'), 'Bachelor of Science in Nursing', 'Undergraduate Programs', NULL),
-- IOP
((SELECT id FROM college_ids WHERE name = 'IOP'), 'Bachelor of Science in Pharmacy', 'Undergraduate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'IOP'), 'Associate in Applied Science in Pharmacy Technology', 'Associate Programs', NULL),
-- IIHS
((SELECT id FROM college_ids WHERE name = 'IIHS'), 'Master of Science in Radiologic Technology', 'Masters Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'IIHS'), 'Bachelor of Science in Radiologic Technology', 'Undergraduate Programs', NULL),
-- CITE
((SELECT id FROM college_ids WHERE name = 'CITE'), 'Bachelor of Elementary Education', 'Undergraduate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CITE'), 'Bachelor of Secondary Education', 'Undergraduate Programs', 'English'),
((SELECT id FROM college_ids WHERE name = 'CITE'), 'Bachelor of Secondary Education', 'Undergraduate Programs', 'Mathematics'),
((SELECT id FROM college_ids WHERE name = 'CITE'), 'Bachelor of Secondary Education', 'Undergraduate Programs', 'Social Studies'),
-- IOPsy
((SELECT id FROM college_ids WHERE name = 'IOPsy'), 'Bachelor of Science in Psychology', 'Undergraduate Programs', NULL),
-- CTHM
((SELECT id FROM college_ids WHERE name = 'CTHM'), 'Bachelor of Science in Hospitality Management', 'Undergraduate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CTHM'), 'Bachelor of Science in Tourism Management', 'Undergraduate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CTHM'), 'Associate in Hospitality Management', 'Associate Programs', NULL),
-- IDEM
((SELECT id FROM college_ids WHERE name = 'IDEM'), 'Bachelor of Science in Disaster Risk Management (BSDRM)', 'Undergraduate Programs', NULL),
-- ISW
((SELECT id FROM college_ids WHERE name = 'ISW'), 'Bachelor of Science in Social Work (BSSW)', 'Undergraduate Programs', NULL),
-- CET
((SELECT id FROM college_ids WHERE name = 'CET'), 'Bachelor of Engineering Technology', 'Undergraduate Programs', 'Electrical Technology'),
((SELECT id FROM college_ids WHERE name = 'CET'), 'Bachelor of Engineering Technology', 'Undergraduate Programs', 'Electronics Technology'),
((SELECT id FROM college_ids WHERE name = 'CET'), 'Bachelor in Automotive Technology', 'Undergraduate Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CET'), 'Diploma in Electrical Technology', 'Diploma Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CET'), 'Diploma in Industrial Facilities Technology', 'Diploma Programs', NULL),
((SELECT id FROM college_ids WHERE name = 'CET'), 'Diploma in Industrial Facilities Technology', 'Diploma Programs', 'Service Mechanics'),
((SELECT id FROM college_ids WHERE name = 'CET'), 'Associate in Electronics Technology', 'Associate Programs', NULL),
-- SOL
((SELECT id FROM college_ids WHERE name = 'SOL'), 'Juris Doctor with Thesis', 'Doctorate Programs', NULL),
-- HSU
((SELECT id FROM college_ids WHERE name = 'HSU'), 'Automotive Servicing', 'TVL Track', NULL),
((SELECT id FROM college_ids WHERE name = 'HSU'), 'Drafting Technology', 'TVL Track', NULL),
((SELECT id FROM college_ids WHERE name = 'HSU'), 'Computer Programming', 'TVL Track', NULL),
((SELECT id FROM college_ids WHERE name = 'HSU'), 'Computer Systems Servicing', 'TVL Track', NULL),
((SELECT id FROM college_ids WHERE name = 'HSU'), 'Hotel and Restaurant Servicing', 'TVL Track', NULL),
((SELECT id FROM college_ids WHERE name = 'HSU'), 'Music', 'Arts and Design Track', NULL),
((SELECT id FROM college_ids WHERE name = 'HSU'), 'Film Production', 'Arts and Design Track', NULL),
((SELECT id FROM college_ids WHERE name = 'HSU'), 'Theater Arts Production', 'Arts and Design Track', NULL),
((SELECT id FROM college_ids WHERE name = 'HSU'), 'Visual Arts and Multimedia Arts', 'Arts and Design Track', NULL),
((SELECT id FROM college_ids WHERE name = 'HSU'), 'Sports Coaching', 'Sports Track', NULL),
((SELECT id FROM college_ids WHERE name = 'HSU'), 'Sports Officiating', 'Sports Track', NULL)
ON CONFLICT (college_id, name, major) DO NOTHING;
