i wont have much time to work on this for a bit so i will dump brain


- need to consider job mutability. Good for saving on memory but could lead to annoying and hard to track corrupt state
    - immutable jobs might be better ; memory impact might not be too bad
    - could introduce multiple job models
        - some fields not needed for processing
        - main memory drivers will be `TEXT` fields
            - I think i can control this though, just make shorter path names lol
            - each job (with empty str fields) is 354 bytes
            - How many jobs will be processed at a time?
                - Good question, we can remove 1 background at a time given our hardware constraints, however
                we could reasonably process multiple conversions in parallel though.
- need to figure out how to verify images aren't malware
- need to design the api
- need to figure out how S3 storage will work
    - private download method unique to S3 storage implementation probably
- i'm not too sure how workers work. I think i'll need two types of workers for this
    - one for bg removal
    - one for pre-processing cleanup
- need to remember to remove metadata
    - seriously don't forget this
- can we detect if images already have transparent backgrounds and avoid unnecessary WithoutBG processing?
    - i reckon yes! png, webp use channels, meaning that there is an Alpha channel we can inspect.
    - could be a cool ml project lol, but can probably infer well enough with simple inspection


## concurrency deep dive

Given the 2gb memory constraint of the VPS I'll be hosting on, I can only realistically remove one background
at a time. **(todo: benchmark this)**. However, I don't see a reason the service could not process
multiple conversions and resizes concurrently. I would have to benchmark the memory usage here, but it seems
inexpensive enough. 

It might not require a job relation at all. I *could* instead receive bytes at the API and use
`vips.new_from_bytes` or whatever to immediately thumbnail and webp-ify the image. That would save a lot of disc
space, and make the job state machine much simpler. Although, moderation must also be considered.

I suppose still, the libvips process is lightweight enough *(verify)* that we could just moderate the
smaller image.

I think the API should not directly call any service-related methods, because that could allow the number of
concurrent processes to grow without bound. I need to verify how HTTP serving works in python. In Go, each
HTTP handler starts a new goroutine for each request. My instincts tell me Python does not do this, since the

concurrency models are so different, but I will need to research.

Regardless, it's probably good practice to go API -> Queue -> Service.

If we are to forego saving the job to the database at the thumbnailing stage, we must also accept that
images currently being thumbnailed will be completely lost when the service crashes. We also need to consider how
we will propogate a retry signal back to the client asynchronously. One strategy for this would be
benchmarking the thumbnailing process and timing out after `n + someBuffer` seconds. 

This makes sense to me right now, it removes the need to store the full sized image on disc until job completion.
Job state machine's journey would begin at the moderation stage instead of the thumbnailing stage. This might have
surfaced as a requirement anyway, due to how unsupported HEIC still appears to be 9 years later... It may also
offer performance benefits, I don't know how computer vision works (yet), but I can guess that a smaller image
can be moderated quicker than a larger image. 

## notes to self

this little project has a lot of ins and outs, and small bumps to be considered. I should really be proud
of it. good job nathan
