CREATE TABLE IF NOT EXISTS models (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    version VARCHAR NOT NULL,
    model_type VARCHAR NOT NULL,
    dataset VARCHAR NOT NULL,
    params JSONB,
    feature_names JSONB,
    s3_path VARCHAR NOT NULL,
    git_path VARCHAR,
    stage VARCHAR NOT NULL DEFAULT 'experimental',
    owner VARCHAR NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_name_version UNIQUE (name, version)
);

CREATE INDEX IF NOT EXISTS idx_models_name ON models(name);
CREATE INDEX IF NOT EXISTS idx_models_stage ON models(stage);
CREATE INDEX IF NOT EXISTS idx_models_model_type ON models(model_type);
CREATE INDEX IF NOT EXISTS idx_models_owner ON models(owner);