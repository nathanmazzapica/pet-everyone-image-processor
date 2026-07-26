# Pet Everyone Image Processor (PEIP)

Python image-processing microservice for Pet Everyone. Prepares user-uploaded
content for display: moderation, resize/webp conversion, background removal.
Built as a hands-on distributed-systems learning project.

## AI usage policy

This is a learning project — manually converting theory to code is the point.
Assist, review, and explain; do **not** write whole subsystems unprompted.
All AI involvement is noted in commit messages. Prefer surfacing options and
tradeoffs over producing finished implementations.

## Commands

```bash
pytest                              # run tests
python3 -m src.repository.init_db   # initialize the SQLite DB (run once, on fresh checkout)
python3 -m src.main                 # run the supervisor (workers)
python3 -m src.service.api.run_api  # run the API
```

Setup (see README for detail): `pip3 install -r requirements.txt`, install &
configure the ClamAV daemon, copy `.env.example` to `.env`.

**Startup order on a fresh checkout:** init the DB before starting the
supervisor or API. Redis is **not** required at startup — if it's down,
workers keep processing and `JobOutbox` simply accumulates until Redis is
reachable and the outbox drains. A Redis outage is the scenario the outbox
absorbs, not a `FatalServiceError`.

## Architecture

Two transports, doing two different jobs — do not conflate them:

- **SQLite queue** = the job system and source of truth. Workers find work by
  querying the DB. Job hand-offs are DB writes.
- **Redis pub/sub** = *outbound status only*, back to the Pet Everyone web app.
  It is NOT the inter-worker mechanism. Workers never coordinate via Redis.

### Job lifecycle

1. Image bytes hit the API → ClamAV scans.
2. On pass, a job is created with `job_type = PREPROCESS` (job_type is an enum).
3. A preprocess worker pulls it from the queue, does the resize/webp work, then
   in a **single SQLite transaction**: marks the job complete, enqueues the next
   job (`job_type = BACKGROUND_REMOVAL`), and stages a status event in
   `JobOutbox`.
4. A separate step drains `JobOutbox` and publishes to Redis (fire-and-forget)
   for the web app to consume.

### The invariant that matters most

The status update + next-job enqueue + outbox write happen in **one
transaction**. The Redis publish is fire-and-forget and happens *after* commit,
by draining `JobOutbox` — never inside the worker's transaction, and never as a
direct publish that bypasses the outbox.

This is the transactional outbox pattern. It exists to prevent the dual-write
bug: if a worker did the DB write and the Redis publish as two separate steps,
a crash between them loses the status update or double-publishes. Do not
"simplify" by publishing directly from the worker.

## Conventions

- **Timestamps:** UTC, ISO 8601.
- **Error taxonomy:**
  - `JobFailedError` — *this job* is bad (e.g. ClamAV flags it, image won't
    decode). Mark the job failed and move on; the worker keeps running.
  - `FatalServiceError` — *the service* is broken (e.g. a dependency is
    unreachable). Stop the worker.

<!-- Schema lives in schema.sql — composite PK, JobOutbox table, partial
     indexes. Read the file rather than duplicating it here. -->