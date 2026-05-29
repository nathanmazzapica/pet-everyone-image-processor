## Job Stories

### Background Removal
Users will upload image of their pets to Pet Everyone, and Pet Everyone will forward the image to the image processor.
Their pet will then be visible to all users with the background removed and they can share with friends. Users will want to view the status
of their image. They will want to know if it failed and what stage of processing it is at. 

## Endpoints

- POST `/upload` (requires auth)
    - body
        - pet_id
        - user_id
        - secret
    - response
        - 201 success
        - 401
        - 500
- GET `/status/{image_id}`
- GET `/subscribe/{image_id}` (requires auth)
    - opens SSE stream for events
- GET `/ping` health checkpoint
    - 200 OK

## Considerations

Should `/upload` require user's auth? Could we just whitelist the P.E instance's IP and forward the image instead of direct user upload?
This would make db management feel easier, and prevent unintended usage.

Should the image processor be responsible for a `DELETE /{image_id}` endpoint? Or should that responsibility stay in the main app?
Again, this decision would impact where the database lives. I don't know if I could keep it on the same server as the main Pet Everyone app
if I want the image processor to handle image deletions. I suppose the image processor shouldn't though. If an image is deleted, the pet would be deleted too.

This does have me wondering if I should move the database to its own thing now though. I would have to anyway *if* I needed to scale to multiple instance of
pet everyone. This need is unlikely, but maybe it is worth doing just for the learning experience?
