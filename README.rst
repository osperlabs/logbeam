logbeam - A python logging handler for CloudWatch Logs
======================================================

A standard Python logging handler using the event batching framework
supplied by the ``awscli-cwlogs`` package.

Logs are submitted in batches to the CloudWatch API, with configurable
limits on the maximum age of messages before a partial batch is transmitted,
and maximum batch sizes. These all match the same configuration options you'll
find for `configuring the cwlogs agent`__

.. __: http://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AgentReference.html


Installation
------------

::

    pip install logbeam


Usage
-----

Here's an example for setting up your root logging handler for use with
logbeam's ``CloudWatchLogsHandler``

::

    import logging
    from logbeam import CloudWatchLogsHandler

    cw_handler = CloudWatchLogsHandler(
        log_group_name='my_log_group',
        log_stream_name='my_log_stream',
        buffer_duration=10000,
        batch_count=10,
        batch_size=1048576
    )

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(cw_handler)

    logger.info("Hello world!")

Warning: If you attach the logger to the root logger like the example above, you
should turn off propagation for the ``cwlogs`` logger to prevent a log-loop-storm,
where logs about the CloudWatch process cause additional logs to be sent to
CloudWatch.

You can turn propagation off by calling ``logging.getLogger('cwlogs').propagate = False``.
You may also want to attach a file log handler here so you can see any errors
or warnings from it.


Handler arguments
-----------------

The ``CloudWatchLogsHandler`` can be initialised with the following args

- ``log_group_name`` - the destination CloudWatch log group name
- ``log_stream_name`` - the destination CloudWatch log stream name
- ``buffer_duration`` - (default 10000) maximum age in ms of the oldest log item in a batch before the batch must be transmitted to CloudWatch.
- ``batch_count``- (default 10000) maximum number of log items in a batch before the batch must be transmitted to CloudWatch.
- ``batch_size`` - (default 1024*1024) maximum size in bytes a batch of logs can reach before being transmitted to CloudWatch.
- ``logs_client`` - (optional) an initialised boto3 ``CloudWatchLogs.Client``. if this isn't supplied the handler will initialise its own.


A word on batch settings
------------------------

Log records are buffered in memory for a short while before being sent to
CloudWatch, meaning there is a small chance of losing log records in the event
of some kind of apocalypse (e.g. unexpected process termination).

Under normal conditions the shutdown of the Python logging system when the
process exits will instruct the CloudWatch threads created by the handler to
flush their buffers and wait for them to exit.

If the process is forcefully terminated (e.g. SIGKILL) any logs that are in the
buffer and haven't been transmitted to CloudWatch yet will be lost. For this
reason it is sensible to configure the ``buffer_duration`` to be relatively
short.

The buffer size (in bytes) and length (number of items) should not be set too
low, because of the CloudWatch Logs API limit of a maximum 5 PutLogEvents calls
per second for a log stream. If these values are too low and you are emitting
lots of log items each batch will queue up behind the last one for 0.2 seconds.
