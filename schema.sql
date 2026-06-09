-- maps errors to human readable descriptions, used for observability
CREATE TABLE IF NOT EXISTS FailureCodes (
    err_no INTEGER PRIMARY KEY,
    err_desc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Job (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type TEXT NOT NULL CHECK (job_type IN (
            'PREPROCESS',
            'BACKGROUND_REMOVAL'
        )),
    job_status TEXT NOT NULL DEFAULT 'QUEUED' CHECK (job_status IN (
            'QUEUED',
            'PROCESSING',
            'DONE',
            'FAILED',
            'REJECTED'
        )),
    input_key TEXT NOT NULL,
    output_key TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_locked INTEGER NOT NULL DEFAULT 0, -- 0 means never locked
    pet_id TEXT NOT NULL,   -- populated with pet_id from the request
    image_id TEXT NOT NULL, -- unique identifier for the uploaded image
    ready_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_job_worker_poll
    ON Job (job_status, ready_at)
    WHERE job_status = 'QUEUED';

CREATE INDEX IF NOT EXISTS idx_job_stale_lock
    ON Job (job_status, last_locked)
    WHERE job_status = 'PROCESSING';

CREATE TRIGGER IF NOT EXISTS trg_job_updated_at
    AFTER UPDATE ON Job
    FOR EACH ROW
    BEGIN
        UPDATE Job
        SET updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        WHERE job_id = OLD.job_id;
    end;

CREATE TABLE IF NOT EXISTS FailedJobs (
    job_id INTEGER NOT NULL REFERENCES Job(job_id),
    timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    err_no INTEGER NOT NULL REFERENCES FailureCodes(err_no),
    PRIMARY KEY (job_id, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_failedjobs_jobid
    ON FailedJobs (job_id);

CREATE TABLE IF NOT EXISTS JobOutbox (
    job_id INTEGER NOT NULL REFERENCES Job(job_id),
    timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (job_id)
);

CREATE INDEX IF NOT EXISTS idx_outbox_timestamp
    ON JobOutbox (timestamp);