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

    # If you use the root logger instead of __name__ you will need to turn off
    # propagation for loggers 'cwlogs' and 'botocore' or a cycle of logs about
    # log message delivery will be created, causing the log handler never to
    # exit and your program to hang.
    logger = logging.getLogger(__name__)

    logger.setLevel(logging.INFO)
    logger.addHandler(cw_handler)

    logger.info("Hello world!")

Warning: As mentioned in the snippet above, if you attach the handler to the root
logger (``logging.getLogger()``) you need to disable propagation for the
``cwlogs`` and ``botocore`` loggers to prevent an infinite loop of logs. The
following example sends logs from these loggers to stderr instead:

::
    local_handler = logging.StreamHandler()

    for logger_name in ('cwlogs', 'botocore'):
        lg = logging.getLogger(logger_name)

        # Don't propagate to the root handler if it has a CloudWatchLogsHandler
        lg.propagate = False

        # Write logs to stderr instead
        lg.addHandler(local_handler)


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
