-- Add moderation enforcement fields for profanity tracking and timed suspension
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS profanity_count integer NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS profanity_counter_started_at timestamptz,
ADD COLUMN IF NOT EXISTS profanity_warning_sent boolean NOT NULL DEFAULT false,
ADD COLUMN IF NOT EXISTS suspended_until timestamptz;

-- Helpful index for admin filtering and automated checks
CREATE INDEX IF NOT EXISTS idx_profiles_suspended_until ON public.profiles (suspended_until);

-- Seed approved blocked terms (idempotent)
INSERT INTO public.forbidden_words (word)
VALUES
    ('putang ina'),
    ('putangina'),
    ('tang ina'),
    ('tangina'),
    ('puta ka'),
    ('anak ka ng puta'),
    ('gago'),
    ('gaga'),
    ('ulol'),
    ('tanga'),
    ('bobo'),
    ('pakshet'),
    ('punyeta'),
    ('kantot'),
    ('burat'),
    ('bayag'),
    ('jakol'),
    ('fuck'),
    ('fucking'),
    ('shit'),
    ('bitch'),
    ('asshole'),
    ('motherfucker'),
    ('bastard'),
    ('dick'),
    ('pussy'),
    ('cunt'),
    ('slut'),
    ('whore'),
    ('bullshit'),
    ('puta'),
    ('hijo de puta'),
    ('coño'),
    ('mierda'),
    ('cabron'),
    ('madarchod'),
    ('behenchod'),
    ('chutiya'),
    ('randi'),
    ('gandu'),
    ('شرموطة'),
    ('قحبة'),
    ('كس'),
    ('طيز'),
    ('زب')
ON CONFLICT (word) DO NOTHING;
