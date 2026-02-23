# Pet Everyone Image Processor

The PEIP is used to prepare user uploaded content for display on Pet Everyone.

Images are processed in the following manner:

1. Incoming images are sent to OpenAI's moderation API for approval
2. Approved images are resized and converted to webp for processing
3. Images have their background removed using WithoutBG
