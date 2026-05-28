# Architecture Layers

Each component of the pipeline follows the following pattern:

Actor → Orchestrator → Processor/Storage

Where the actor is the 'client' of the pipeline (Workers), the orchestrator is the 'middleman' between the actor and the processor/storage.
Workers additionally get access to a repository for database operations.


## Actors
Workers are responsible for:
- Processing jobs
- Marking job status

## Orchestrators
Orchestrators are responsible for:
- Receiving jobs
- Bubbling up processor errors
- Bubbling up storage errors
- Data validation
- Passing image data from storage to processor
- Passing transformed image data to storage

## Processors
Processors are responsible for:
- Transforming images

## Storage
Storage is responsible for:
- Storing images
- Retrieving images
- 
## API Layer
The API layer is responsible for:
- Receiving requests from the client
- Passing incoming bytes to the upload service
- Sending responses to the client

TODO: 
- [ ] Determine how API will communicate job status back to Pet Everyone's server/the client
