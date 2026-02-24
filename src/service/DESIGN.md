## Job Handling

As of right now jobs are mutable in memory, this seems like the right call given the memory constraints.

## Thread Safety

To start there will only be one worker process, but I'm going to design for multiple so that I can learn.

I'm not sure if this should/needs to be enforced at the service level or is
a worker concern. If thread safety is guarunteed at the worker level, my hypothesis
is that nothing will need to structurally change about the service layer.
