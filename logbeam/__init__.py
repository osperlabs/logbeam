import logging
from threading import Event

import boto3
from botocore.exceptions import ClientError

from cwlogs.push import EventBatchPublisher, EventBatch, LogEvent
from cwlogs.threads import BaseThread
from six.moves import queue as Queue


logger = logging.getLogger(__name__)


class BatchedCloudWatchSink(BaseThread):

    """A sink for LogEvent objects which batches and uploads to CloudWatch logs

    It relies on the LogEvent, EventBatch and EventBatchPublisher from the
    awscli-cwlogs plugin (cwlogs package). The latter of the two do the heavy
    lifting - all this class does is add items to batches and submit batches
    to the EventBatchPublisher queue for publishing when they are full.
    """
    def __init__(
            self,
            logs_service,
            log_group_name,
            log_stream_name,
            buffer_duration,
            batch_count,
            batch_size):
        super(BatchedCloudWatchSink, self).__init__(Event())
        self.logs_service = logs_service
        self.publisher_stop_flag = Event()
        self.group_stop_flag = Event()

        # Incoming LogEvents enter this queue via self.add_event()
        self.event_queue = Queue.Queue()
        # Completed EventBatches get put onto this queue, for the
        # EventBatchPublisher to upload
        self.publisher_queue = Queue.Queue()

        # The publisher thread, will be started and stopped with this thread
        self.publisher = EventBatchPublisher(
            self.publisher_stop_flag,
            self.publisher_queue,
            logs_service,
            log_group_name,
            log_stream_name
        )
        self.publisher.group_stop_flag = self.group_stop_flag
        # Get the nextSequenceToken for this log stream from AWS
        # otherwise the first batch upload will fail (though it would succeed
        # when it automatically retries)
        self.publisher.sequence_token = nextSequenceToken(
            logs_service,
            log_group_name,
            log_stream_name
        )

        self.buffer_duration = buffer_duration
        self.batch_count = batch_count
        self.batch_size = batch_size
        self.event_batch = None

    def shutdown(self):
        logger.info('CloudWatch sink shutting down gracefully')
        # Only shutdown ourselves here. The publisher thread should be shut
        # down by the end of the _run(), that this flag breaks the loop of
        self.stop_flag.set()
        self.join()
        self.publisher.join()
        logger.info('CloudWatch sink shutdown complete')

    def _add_event_to_batch(self, event):
        if self.event_batch is None:
            self.event_batch = EventBatch(
                self.buffer_duration,
                self.batch_count,
                self.batch_size
            )
        return self.event_batch.add_event(event)

    def _send_batch_to_publisher(self, force=False):
        if self.event_batch is None:
            return
        if force or self.event_batch.should_batch_be_published():
            self.event_batch.force_publish = (
                force or self.event_batch.force_publish
            )
            self.publisher_queue.put(self.event_batch)
            self.event_batch = None

    def _run(self):
        self.publisher.start()
        logger.info('CloudWatch Sink thread starting')
        while True:
            try:
                event = self.event_queue.get(False)
                add_status = self._add_event_to_batch(event)
                if add_status == 0:
                    self._send_batch_to_publisher(force=True)
                    self._add_event_to_batch(event)
            except Queue.Empty:
                if self._exit_needed():
                    self._send_batch_to_publisher(force=True)
                    break
                else:
                    self.stop_flag.wait(2)
            self._send_batch_to_publisher()
        logger.info('Asking publisher thread to shut down...')
        self.publisher_stop_flag.set()

    def on_run_failed(self, e):
        self.group_stop_flag.set()
        self.publisher_stop_flag.set()

    def add_event(self, event):
        self.event_queue.put(event)


class CloudWatchLogsHandler(logging.Handler):
    def __init__(
            self,
            log_group_name,
            log_stream_name,
            buffer_duration=10000,
            batch_count=10,
            batch_size=1024 * 1024,
            logs_client=None,
            *args, **kwargs):
        super(CloudWatchLogsHandler, self).__init__(*args, **kwargs)
        self.prev_event = None
        if logs_client is None:
            logs_client = boto3.client('logs')
        self.sink = BatchedCloudWatchSink(
            logs_client,
            log_group_name,
            log_stream_name,
            buffer_duration,
            batch_count,
            batch_size
        )
        self.sink.start()
        logger.info('CloudWatch Sink started...')

    def logrecord_to_logevent(self, record):
        return LogEvent(
            timestamp=int(record.created * 1000),
            message=self.format(record),
            prev_event=self.prev_event,
        )

    def emit(self, record):
        event = self.logrecord_to_logevent(record)
        self.prev_event = event
        self.sink.add_event(event)

    def close(self):
        self.sink.shutdown()


def nextSequenceToken(cwl, log_group_name, log_stream_name):
    try:
        res = cwl.describe_log_streams(
            logGroupName=log_group_name,
            logStreamNamePrefix=log_stream_name,
        )
    except ClientError:
        return None
    try:
        matching_streams = res['logStreams']
        # As the search is prefixed-based, we need to make sure we're looking
        # at a log stream with exactly the correct name
        stream, = (
            x for x in matching_streams
            if x['logStreamName'] == log_stream_name
        )
        return stream['uploadSequenceToken']
    except (KeyError, IndexError, ValueError):
        return None
