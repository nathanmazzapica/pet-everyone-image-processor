# Pet Everyone Background Removal / Image Processing Microservice

## Problem

Loading up the WithoutBG ML model for each removal process is expensive in time and memory.

## Constraints

- 2GB VPS
- 1 Worker
- ~6-10s per job
- 1080p max input (Derived from VPS memory constraint: WithoutBG memory usage scales in linear time O(p) where p = pixels in an image

## Architecture

This service will handle background removal for user uploaded images:

convert from HEIC (if needed) -> resize -> removeBG -> convert to WebP

Endpoints:
- POST api/enqueue           enqueues a job (creates database entry)
- GET  api/status/{job_id}   returns the status of a job
- GET  api/ping              returns health status (is online, jobs in queue)

Jobs will be stored in a SQLite DB for now. I am choosing a persistent DB over an in-memory queue to prevent total queue loss if the process crashes.

The service will be split into layers:

1. API inbound adapter
2. Service
3. Repository
4. Models
5. Storage

Once an image is processed it is stored in S3, will need to get this URL back to the main server binary

A TTL manager will occasionally poll the database for in-process jobs to check if their time since locked exceeds a threshold. If it does there are two scenarios.

Scenario A: an output file exists and is valid for the job
job.state -> DONE

Scenario B: No output file exists / output is corrupted
job.state -> QUEUED

## Job States

A job can have the following states:

0. PENDING                  A job in the 'PENDING' state is awaiting moderation approval. Valid transitions: ->Queued, ->REJECTED
1. QUEUED (idle)            A job in the queued state is ready to be picked up by a worker. ->PROCESSING
2. PROCESSING (Locked)      A job in the PROCESSING state is locked. No other worker can touch it. When entering this state, the time will be logged. If time > TTL; Requeue (or retry?) ->RETRY, ->DONE, ->FAILED
3. DONE                     
4. FAILED (?)               A job in the FAILED state has failed more than the max retries or failed in a way where retrying has no chance of fixing it (e.g S3 URL points to nothing)
5. RETRY                    A job in the RETRY state has failed but can still be retried a few more times. ->PROCESSING
6. REJECTED                 A job in the REJECTED state was flagged by moderation.

Jobs will track when they were locked. If it has been locked for too long it will be sent back to the queue

## Job Dataclass

The following fields will be required for the service to work:

job_id
job_status
job_src_url
job_proc_url *(local filepath for any temporary files generated in processing)*
job_output_url
job_attempt_count
job_last_locked

The following fields will be good for observability, but might not be required

job_error *(I'm not sure if this should be required for service to work, or if a flag to retry would be better?)*
job_duration


## Failure Recovery

The following scenarios can cause a job to fail:

1. Process crashing
2. VPS crashing
3. Storage full
4. OOM (out of memory)
5. S3 URL wrong (don't retry)

## Failure Recovery Walkthroughs

**Scenario A: Worker crashes after saving the processed image, but before updating the job status**

**State:**

Database row: [ id = 5 ] [ status = PROCESSING ] [ last_locked = xx:xx:xx ] [ filepath = ugc/images/image-e928.heic ] [ output_filepath = ugc/images/processed/image-e928.webp ]
S3 bucket contains: ugc/images/processed/image-e928-withoutbg.webp

On service restart, the database will be checked and in-progress jobs will be put in a verification queue. Their status will be verified by checking if the output image exists. If the file exists and the image is not corrupted, the job will be marked DONE. 

**Scenario B: A worker crashes before finishing a job**

Database row: [ id = 5 ] [ status = PROCESSING ] [ last_locked = xx:xx:xx ] [ filepath = ugc/images/image-e928.heic ]
S3 bucket contains: *no output*

This case will also be captured on service restart. If an in-process job has no output, then the job will be set back to the QUEUED state.

**Scenario C: OOM mid processing**

Python exposes a `MemoryError` exception. This provides opportunity to gracefully recover from OOM.

The likely cause of this in the BG remover would be the ML model. A secondary cause could be a queue growing too large unbounded.

If the second were the case, the in-memory queue could have its tail cut off or simply be completely deleted.

If the ML model is the problem, a graceful restart might be viable.

Including a secondary process that watches the bg-remover process and restarts it if it crashes would also help here.

If OS level OOM killer nukes our process, the state check on restart will update job statuses appropriately:

```
for job in db.query(where status == PROCESSING)
    if output_file does not exist:
        job.state = queued
    else:
        job.state = done
```

**Scenario D**: Storage Failure

> What do we do if there is no more space on disk prior to S3 migration? OR if S3 is down?


## Other Considerations

I want to include image moderation. My current (very underthought) plan is to just use OpenAI's moderation API (free!)

This opens the question:

> Who is responsible for making the call to OpenAI's API, and who is responsible for the response?

Right now I am leaning toward making this part of the background removal job cycle. (This service). Perhaps an additional state "PENDING".

Another (much smaller) worker coroutine could poll the DB for 'PENDING' jobs and send them upstream. Then it would check the response and either queue the job 
or mark it rejected. Likely sending a notification back to the main server process too to inform the user.

> How do we send notifications back to the user?

## Security Considerations

Should only accept API requests from the main server process. I think this can be achieved by setting up UFW
to only allow incoming HTTP from a specified IP but need to research further
