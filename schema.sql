-- Relational schema for the Loblaw Bio immune cell trial.
-- Normalised so that subject-level facts (treatment, response, sex, age,
-- condition) are stored once per subject, sample-level facts once per sample,
-- and cell counts in long format (one row per sample x population).
-- Adding a new population or project needs no schema change.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS subjects (
    subject_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id),
    condition  TEXT NOT NULL,                      -- melanoma / carcinoma / healthy
    age        INTEGER,
    sex        TEXT CHECK (sex IN ('M', 'F')),
    treatment  TEXT NOT NULL,                      -- miraclib / phauximab / none
    response   TEXT CHECK (response IN ('yes', 'no'))  -- NULL for untreated healthy
);

CREATE TABLE IF NOT EXISTS samples (
    sample_id                 TEXT PRIMARY KEY,
    subject_id                TEXT NOT NULL REFERENCES subjects(subject_id),
    sample_type               TEXT NOT NULL,       -- PBMC / WB ...
    time_from_treatment_start INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS cell_counts (
    sample_id  TEXT NOT NULL REFERENCES samples(sample_id),
    population TEXT NOT NULL,                      -- b_cell, cd8_t_cell, ...
    count      INTEGER NOT NULL CHECK (count >= 0),
    PRIMARY KEY (sample_id, population)
);

CREATE INDEX IF NOT EXISTS idx_subjects_filter ON subjects(condition, treatment, response);
CREATE INDEX IF NOT EXISTS idx_samples_subject ON samples(subject_id);
CREATE INDEX IF NOT EXISTS idx_samples_filter  ON samples(sample_type, time_from_treatment_start);
CREATE INDEX IF NOT EXISTS idx_counts_pop      ON cell_counts(population);
