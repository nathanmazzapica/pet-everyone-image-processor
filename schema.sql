CREATE TABLE job (
  job_id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_status TEXT NOT NULL DEFAULT 'PENDING' CHECK (
    job_status IN (
      'PENDING',
      'QUEUED',
      'PROCESSING',
      'DONE',
      'FAILED',
      'RETRY',
      'REJECTED'
    )
  ),
  input_url TEXT NOT NULL,
  proc_url TEXT,
  output_url TEXT,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  last_locked REAL,
  created_at REAL NOT NULL DEFAULT (strftime('%s','now')),
  updated_at REAL NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE INDEX idx_job_status ON job(job_status);
CREATE INDEX idx_job_last_locked ON job(last_locked);

CREATE TRIGGER job_set_updated_at
AFTER UPDATE ON job
FOR EACH ROW
BEGIN
  UPDATE job
  SET updated_at = strftime('%s','now')
  WHERE job_id = NEW.job_id;
END;
