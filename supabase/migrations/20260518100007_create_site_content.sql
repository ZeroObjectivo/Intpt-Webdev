-- Key-value store for editable landing page content
CREATE TABLE IF NOT EXISTS public.site_content (
    key text PRIMARY KEY,
    value text NOT NULL DEFAULT ''
);

ALTER TABLE public.site_content ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role can manage site content"
    ON public.site_content FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Anyone can view site content"
    ON public.site_content FOR SELECT
    USING (true);

-- Seed defaults
INSERT INTO public.site_content (key, value) VALUES
    ('hero_title', 'Herons'' Hub'),
    ('hero_subtitle', 'Community for everyone'),
    ('about_kicker', 'About Us'),
    ('about_description', 'Herons'' Hub is a University of Makati digital community where students can share campus updates, discover opportunities, join events, and connect through verified school identities. Built for collaboration, it keeps discussions relevant, student-focused, and easy to navigate.'),
    ('features_kicker', 'Features'),
    ('feature_1_label', 'Only UMak Students allowed'),
    ('feature_1_desc', 'Access is limited to verified @umak.edu.ph accounts to keep the community safe and school-focused.'),
    ('feature_1_icon', 'user'),
    ('feature_2_label', 'Community Posts'),
    ('feature_2_desc', 'Share updates, marketplace offers, and questions in one moderated student feed.'),
    ('feature_2_icon', 'document'),
    ('feature_3_label', 'Unified Platform'),
    ('feature_3_desc', 'Events, scholarship listings, and UMak Coop catalogs are accessible in one place.'),
    ('feature_3_icon', 'calendar'),
    ('feature_4_label', 'Student-Based Application'),
    ('feature_4_desc', 'Built around student needs with campus-first features, reporting, and real-time interactions.'),
    ('feature_4_icon', 'list'),
    ('team_kicker', 'The Team'),
    ('team_title', 'Meet the Team'),
    ('team_desc', 'The people behind Herons'' Hub — building a better campus experience for every UMak student.'),
    ('footer_contact_title', 'Developers / Contact'),
    ('footer_contact_email', 'sample@heronshub.social')
ON CONFLICT (key) DO NOTHING;
