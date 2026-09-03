-- ============================================================
-- AI-Assisted Criminal Investigation & Intelligence Platform
-- Supabase Migration: Initial Schema
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- PROFILES TABLE (linked to auth.users)
-- ============================================================
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT UNIQUE NOT NULL,
    badge_number TEXT UNIQUE NOT NULL,
    role TEXT DEFAULT 'INVESTIGATOR' CHECK (role IN ('ADMIN', 'INVESTIGATOR')),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Index for profiles
CREATE INDEX IF NOT EXISTS idx_profiles_username ON profiles(username);
CREATE INDEX IF NOT EXISTS idx_profiles_badge_number ON profiles(badge_number);
CREATE INDEX IF NOT EXISTS idx_profiles_role ON profiles(role);

-- ============================================================
-- CASES TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS cases (
    id BIGSERIAL PRIMARY KEY,
    case_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED')),
    created_by_user_id UUID NOT NULL REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Index for cases
CREATE INDEX IF NOT EXISTS idx_cases_case_id ON cases(case_id);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_created_by ON cases(created_by_user_id);

-- ============================================================
-- CASE ACCESSES TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS case_accesses (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    case_id BIGINT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    access_status TEXT DEFAULT 'PENDING' CHECK (access_status IN ('PENDING', 'APPROVED', 'REJECTED')),
    requested_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    reviewed_at TIMESTAMPTZ,
    reviewed_by_admin_id UUID REFERENCES profiles(id),
    UNIQUE(user_id, case_id)
);

-- Index for case_accesses
CREATE INDEX IF NOT EXISTS idx_case_accesses_user_id ON case_accesses(user_id);
CREATE INDEX IF NOT EXISTS idx_case_accesses_case_id ON case_accesses(case_id);
CREATE INDEX IF NOT EXISTS idx_case_accesses_status ON case_accesses(access_status);

-- ============================================================
-- EVIDENCE DOCUMENTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS evidence_documents (
    id BIGSERIAL PRIMARY KEY,
    case_id BIGINT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    sha256_hash TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    uploaded_by_user_id UUID NOT NULL REFERENCES profiles(id),
    is_quarantined BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(case_id, sha256_hash)
);

-- Index for evidence_documents
CREATE INDEX IF NOT EXISTS idx_evidence_case_id ON evidence_documents(case_id);
CREATE INDEX IF NOT EXISTS idx_evidence_mime_type ON evidence_documents(mime_type);
CREATE INDEX IF NOT EXISTS idx_evidence_sha256 ON evidence_documents(sha256_hash);
CREATE INDEX IF NOT EXISTS idx_evidence_uploaded_by ON evidence_documents(uploaded_by_user_id);

-- ============================================================
-- PROCESSING JOBS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS processing_jobs (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES evidence_documents(id) ON DELETE CASCADE,
    schema_version TEXT NOT NULL,
    route TEXT NOT NULL,
    extraction_method TEXT NOT NULL,
    status TEXT NOT NULL,
    detection_index JSONB,
    ocr_pending_pages JSONB,
    evidence_payload JSONB,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Index for processing_jobs
CREATE INDEX IF NOT EXISTS idx_processing_jobs_document_id ON processing_jobs(document_id);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status);

-- ============================================================
-- AUDIT TRAILS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_trails (
    event_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES profiles(id),
    case_id TEXT,
    action_type TEXT NOT NULL,
    metadata_json JSONB,
    ip_address TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    tamper_hash TEXT NOT NULL DEFAULT REPEAT('0', 64)
);

-- Index for audit_trails
CREATE INDEX IF NOT EXISTS idx_audit_trails_user_id ON audit_trails(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_trails_case_id ON audit_trails(case_id);
CREATE INDEX IF NOT EXISTS idx_audit_trails_action_type ON audit_trails(action_type);
CREATE INDEX IF NOT EXISTS idx_audit_trails_timestamp ON audit_trails(timestamp);

-- ============================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================

-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_accesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_trails ENABLE ROW LEVEL SECURITY;

-- Profiles: Users can read all profiles, but only update their own
CREATE POLICY "Profiles: Users can view all profiles"
    ON profiles FOR SELECT
    USING (true);

CREATE POLICY "Profiles: Users can update own profile"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

-- Cases: Authenticated users can view cases they have access to
CREATE POLICY "Cases: Users can view cases they have access to"
    ON cases FOR SELECT
    USING (
        auth.uid() = created_by_user_id
        OR EXISTS (
            SELECT 1 FROM case_accesses
            WHERE case_accesses.case_id = cases.id
            AND case_accesses.user_id = auth.uid()
            AND case_accesses.access_status = 'APPROVED'
        )
        OR EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'ADMIN'
        )
    );

-- Cases: Authenticated users can create cases
CREATE POLICY "Cases: Users can create cases"
    ON cases FOR INSERT
    WITH CHECK (auth.uid() = created_by_user_id);

-- Case Accesses: Users can view their own access requests
CREATE POLICY "Case Accesses: Users can view own access requests"
    ON case_accesses FOR SELECT
    USING (
        user_id = auth.uid()
        OR EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'ADMIN'
        )
    );

-- Case Accesses: Users can create access requests
CREATE POLICY "Case Accesses: Users can create access requests"
    ON case_accesses FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- Case Accesses: Admins can update access requests
CREATE POLICY "Case Accesses: Admins can update access requests"
    ON case_accesses FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'ADMIN'
        )
    );

-- Evidence Documents: Users can view evidence for cases they have access to
CREATE POLICY "Evidence: Users can view evidence for accessible cases"
    ON evidence_documents FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM cases
            WHERE cases.id = evidence_documents.case_id
            AND (
                cases.created_by_user_id = auth.uid()
                OR EXISTS (
                    SELECT 1 FROM case_accesses
                    WHERE case_accesses.case_id = cases.id
                    AND case_accesses.user_id = auth.uid()
                    AND case_accesses.access_status = 'APPROVED'
                )
                OR EXISTS (
                    SELECT 1 FROM profiles
                    WHERE profiles.id = auth.uid()
                    AND profiles.role = 'ADMIN'
                )
            )
        )
    );

-- Evidence Documents: Users can upload evidence for cases they have access to
CREATE POLICY "Evidence: Users can upload evidence for accessible cases"
    ON evidence_documents FOR INSERT
    WITH CHECK (
        uploaded_by_user_id = auth.uid()
        AND EXISTS (
            SELECT 1 FROM cases
            WHERE cases.id = evidence_documents.case_id
            AND (
                cases.created_by_user_id = auth.uid()
                OR EXISTS (
                    SELECT 1 FROM case_accesses
                    WHERE case_accesses.case_id = cases.id
                    AND case_accesses.user_id = auth.uid()
                    AND case_accesses.access_status = 'APPROVED'
                )
                OR EXISTS (
                    SELECT 1 FROM profiles
                    WHERE profiles.id = auth.uid()
                    AND profiles.role = 'ADMIN'
                )
            )
        )
    );

-- Processing Jobs: Users can view processing jobs for evidence they can access
CREATE POLICY "Processing: Users can view processing jobs for accessible evidence"
    ON processing_jobs FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM evidence_documents
            WHERE evidence_documents.id = processing_jobs.document_id
            AND EXISTS (
                SELECT 1 FROM cases
                WHERE cases.id = evidence_documents.case_id
                AND (
                    cases.created_by_user_id = auth.uid()
                    OR EXISTS (
                        SELECT 1 FROM case_accesses
                        WHERE case_accesses.case_id = cases.id
                        AND case_accesses.user_id = auth.uid()
                        AND case_accesses.access_status = 'APPROVED'
                    )
                    OR EXISTS (
                        SELECT 1 FROM profiles
                        WHERE profiles.id = auth.uid()
                        AND profiles.role = 'ADMIN'
                    )
                )
            )
        )
    );

-- Processing Jobs: Users can create processing jobs
CREATE POLICY "Processing: Users can create processing jobs"
    ON processing_jobs FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM evidence_documents
            WHERE evidence_documents.id = processing_jobs.document_id
            AND EXISTS (
                SELECT 1 FROM cases
                WHERE cases.id = evidence_documents.case_id
                AND (
                    cases.created_by_user_id = auth.uid()
                    OR EXISTS (
                        SELECT 1 FROM case_accesses
                        WHERE case_accesses.case_id = cases.id
                        AND case_accesses.user_id = auth.uid()
                        AND case_accesses.access_status = 'APPROVED'
                    )
                    OR EXISTS (
                        SELECT 1 FROM profiles
                        WHERE profiles.id = auth.uid()
                        AND profiles.role = 'ADMIN'
                    )
                )
            )
        )
    );

-- Audit Trails: Only admins can view audit trails
CREATE POLICY "Audit: Only admins can view audit trails"
    ON audit_trails FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'ADMIN'
        )
    );

-- Audit Trails: System can insert audit trails (using service role)
CREATE POLICY "Audit: System can insert audit trails"
    ON audit_trails FOR INSERT
    WITH CHECK (true);

-- ============================================================
-- FUNCTION: Auto-create profile on user signup
-- ============================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, username, badge_number, role)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'username', NEW.email),
        COALESCE(NEW.raw_user_meta_data->>'badge_number', ''),
        COALESCE(NEW.raw_user_meta_data->>'role', 'INVESTIGATOR')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to auto-create profile on signup
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- STORAGE BUCKET: evidence-vault
-- ============================================================
-- Note: Create this bucket via Supabase Dashboard or API
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('evidence-vault', 'evidence-vault', false);
