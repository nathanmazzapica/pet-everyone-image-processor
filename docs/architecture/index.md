# Pet Everyone Image Processor

The Pet Everyone Image Processor is a service that processes images for the Pet Everyone app.

## Requirements
Functional requirements:
- Receive images
- Scan images for viruses
- Send images to moderation
- Store temp images for processing
- Convert images to WEBP and resize
- Remove image backgrounds
- Send status updates to the Pet Everyone app
- Store final images

Non-functional requirements:
- The service must handle failures gracefully
- The service must be able to recover from failures
- The service must not store original images after preprocessing completes
- The service must support horizontal scaling for workers
- The service must not silently fail to process images
- The service must not accept arbitrary traffic
- The service must not store any non-image data

## Future Considerations
- How to handle corrupt preprocessed images?
- When to delete original/preprocessed images?
- Should original images even be stored?