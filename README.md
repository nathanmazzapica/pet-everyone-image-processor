# Pet Everyone Image Processor

The PEIP is used to prepare user uploaded content for display on Pet Everyone.

Images are processed in the following manner:

1. Incoming images are sent to OpenAI's moderation API for approval
2. Approved images are resized and converted to webp for processing
3. Images have their background removed using WithoutBG

## Purpose

This project is being built as a service for Pet Everyone to use for UGC image upload and processing.

It allows for expensive image manipulation operations to be offloaded from the main application server
and provides a foundation for horizontally scalable processing workers

## Development Setup
1. Install the requirements
```bash
pip3 install -r requirements.txt
```
2. Install and configure the [ClamAV](https://docs.clamav.net/manual/Installing.html) Dameon
3. Setup environment variables, an example is provided in `.env.example`
4. Run the api with `python3 -m src.service.api.run_api`
## AI Usage

Since this project is meant for learning (and fun) AI use will be limited and made explicit in commit messages.
The purpose of this project is to give me a hands-on learning experience with a distributed system. I believe the friction of
manually converting theory to code is an essential part of that process.
