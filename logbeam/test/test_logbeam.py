import logging
import mock
import pytest
import time

from cwlogs.push import LogEvent

from .. import (
    CloudWatchLogsHandler,
    BatchedCloudWatchSink,
    nextSequenceToken,
)

log_message_data = [
    {
        'timestamp': (time.time() * 1000) + i,
        'message': 'Message {}'.format(i),
    }
    for i in range(100)
]

first_token = 'original fake sequence token'
second_token = 'new fake sequence token'


def sink_data(sink, events):
    for event in events:
        sink.add_event(LogEvent(**event))


@pytest.fixture
def mock_cw():
    mock_cw = mock.MagicMock()
    mock_cw.describe_log_streams = mock.MagicMock(return_value={
        'logStreams': [{
            'logStreamName': 'log_stream_name',
            'uploadSequenceToken': first_token,
        }],
    })
    mock_cw.put_log_events = mock.MagicMock(return_value={
        'nextSequenceToken': second_token,
        'rejectedLogEventsInfo': {},
    })
    return mock_cw


class TestSink(object):

    @pytest.fixture
    def sink(self, mock_cw):
        sink = BatchedCloudWatchSink(
            mock_cw,
            'log_group_name',
            'log_stream_name',
            500,
            50,
            1024 * 100,
        )
        sink.start()
        return sink

    def test_get_sequence_token(self, mock_cw):
        assert (
            nextSequenceToken(mock_cw, 'log_group_name', 'log_stream_name') ==
            first_token
        )

    def test_sink_batch(self, sink):
        sink_data(sink, log_message_data[:2])
        sink.shutdown()
        sink.logs_service.put_log_events.called_once_with(
            logEvents=log_message_data[:2],
            logGroupName='log_group_name',
            logStreamName='log_stream_name',
            sequenceToken=first_token,
        )

    def test_sink_timeout(self, sink):
        sink_data(sink, log_message_data[:1])
        time.sleep(4)
        sink.logs_service.put_log_events.assert_called_with(
            logEvents=log_message_data[:1],
            logGroupName='log_group_name',
            logStreamName='log_stream_name',
            sequenceToken=first_token,
        )
        sink_data(sink, log_message_data[1:2])
        sink.shutdown()
        sink.logs_service.put_log_events.assert_called_with(
            logEvents=log_message_data[1:2],
            logGroupName='log_group_name',
            logStreamName='log_stream_name',
            sequenceToken=second_token,
        )

    def test_sink_batch_length(self, sink):
        sink_data(sink, log_message_data)
        sink.shutdown()
        sink.logs_service.put_log_events.assert_any_call(
            logEvents=log_message_data[:50],
            logGroupName='log_group_name',
            logStreamName='log_stream_name',
            sequenceToken=first_token,
        )
        sink.logs_service.put_log_events.assert_any_call(
            logEvents=log_message_data[50:],
            logGroupName='log_group_name',
            logStreamName='log_stream_name',
            sequenceToken=second_token,
        )


class TestHandler(object):

    def test_handler(self, mock_cw):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        handler = CloudWatchLogsHandler(
            logs_client=mock_cw,
            log_group_name='log_group_name',
            log_stream_name='log_stream_name',
        )
        logger.addHandler(handler)
        logger.info('Hello world')
        handler.close()
        call_args = mock_cw.put_log_events.call_args[1]
        assert call_args['sequenceToken'] == first_token
        assert len(call_args['logEvents']) == 1
        assert call_args['logEvents'][0]['message'] == 'Hello world'
