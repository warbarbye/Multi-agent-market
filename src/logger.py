from collections.abc import Sequence
from datetime import datetime
from contextlib import ContextDecorator


EVENT_LOGGER_INITIALIZED = 'Logger initialized'
EVENT_AGENT_KILLED = 'Agent killed'
EVENT_AGENT_STARTED = 'Agent started'
EVENT_AGENT_RESTARTED = 'Agent restarted'

EVENT_AGENT_INITIAL_OFFER = 'Initial offer'
EVENT_AGENT_OFFER_CHANGED = 'Offer changed'
EVENT_AGENT_OFFER_ACCEPTED = 'Offer accepted'
EVENT_AGENT_OFFER_REJECTED = 'Offer rejected'

EVENT_AGENT_STATE_CHANGED = 'Agent state changed'
EVENT_AGENT_BANKRUPTED = 'Agent bankrupted'

EVENT_SYSTEM_INITIALIZED = 'System initialized'
EVENT_SYSTEM_CLOSE = 'System closing'
EVENT_CLI = 'CLI command received'
EVENT_EXCEPTION = 'Exception occurred'
EVENT_MESSAGE_SENT = 'Message sent'
EVENT_MESSAGE_RECEIVED = 'Message received'
EVENT_SERVER_NEGOTIATION_BREAKDOWN = 'Server negotiation breakdown'
EVENT_ALL_CLIENTS_NEGOTIATION_BREAKDOWN = 'All clients negotiation breakdown'
EVENT_CLIENT_NEGOTIATION_BREAKDOWN = 'Client negotiation breakdown'
EVENT_SERVER_FAILED_TO_RESPOND = 'Server failed to respond'


EVENTS_ALL = {
    EVENT_LOGGER_INITIALIZED: (),
    EVENT_AGENT_KILLED: ('id',),
    EVENT_AGENT_STARTED: ('id', 'name', 'connections', 'jid', 'policy'),
    EVENT_AGENT_RESTARTED: ('id',),

    EVENT_AGENT_INITIAL_OFFER: ('id', 'type', 'resource', 'money'),  # type as 'buy' or 'sell'
    EVENT_AGENT_OFFER_CHANGED: ('id', 'type', 'prev_resource', 'prev_money', 'resource', 'money'),
    EVENT_AGENT_OFFER_ACCEPTED: ('id', 'type', 'resource', 'money'),
    EVENT_AGENT_OFFER_REJECTED: ('id', 'type', 'resource', 'money'),

    EVENT_AGENT_STATE_CHANGED: ('id', 'reason', 'old_resource', 'resource', 'old_money', 'money'),
    EVENT_AGENT_BANKRUPTED: ('id',),

    EVENT_SYSTEM_INITIALIZED: (),
    EVENT_SYSTEM_CLOSE: (),
    EVENT_CLI: ('command', 'args'),
    EVENT_EXCEPTION: ('where', 'type', 'exception'),
    EVENT_MESSAGE_SENT: ('sender', 'receiver', 'content'),
    EVENT_MESSAGE_RECEIVED: ('sender', 'receiver', 'content'),
    EVENT_SERVER_NEGOTIATION_BREAKDOWN: ('id',),
    EVENT_ALL_CLIENTS_NEGOTIATION_BREAKDOWN: ('id',),
    EVENT_CLIENT_NEGOTIATION_BREAKDOWN: ('id', 'server_id'),
    EVENT_SERVER_FAILED_TO_RESPOND: ('id', 'server_id')
}


logger = None


def initialize_default_logger(log_file, stdstream=None):
    """

    :param log_file: file object to log to
    :param stdstream: additional stream to use
    """
    global logger
    streams = []
    if log_file:
        streams.append(log_file)
    if stdstream:
        streams.append(stdstream)
    logger = Logger(streams, EVENTS_ALL)


class Logger(object):
    """ Logger class, for logging (and event handling)

    logger writes to streams in csv format
    columns:
    event id    timestamp   param1  param2  ...

    number of columns is determined by event with the largest number of parameters
    """
    SEPARATOR = '\t'
    ESCAPE = '"'
    # https://stackoverflow.com/questions/4025760/python-file-write-creating-extra-carriage-return/41248005
    LINE_SEPARATOR = '\n'

    def __init__(self, to, events):
        """ Creates logger

        :param to: a stream or a list of streams that logger will write to
        :param events: a dict-like where for every event there is a sequence of parameter names
        """
        self.streams = to if isinstance(to, Sequence) else [to]
        self.events = events
        self.handlers = {}
        self.columns_n = len(max(self.events.values(), key=len)) + 2

        if EVENT_LOGGER_INITIALIZED in events:
            self.log(EVENT_LOGGER_INITIALIZED)

    def register_event_handler(self, event, handler):
        """ Registers event handler for given event

        :param event: event for which the handler is registered
        :param handler: a function that accepts event and it's params as keyword args
        """
        if event in self.handlers:
            self.handlers[event].append(handler)
        else:
            self.handlers[event] = {handler}

    def remove_event_handler(self, event, handler):
        """ Removes event handler

        :param event: event for which handler will be removed
        :param handler: handler to remove
        """
        self.handlers[event].remove(handler)

    def log(self, event, **kwargs):
        """ Logs event.
        Writes csv line to all streams
        and calls all event handler

        :param event: event to log
        :param kwargs: event params
        """
        args = [kwargs.get(param, '') for param in self.events[event]]
        timestamp = datetime.now()

        self._write_fields(event, timestamp, *args)

        if event in self.handlers:
            for handler in self.handlers[event]:
                handler(event, **kwargs)

    def _write_fields(self, *columns):
        columns = [*columns, *['' for _ in range(self.columns_n - len(columns))]]
        columns = [self._escape_csv(c) for c in columns]

        line = self.SEPARATOR.join(columns)
        self._write(line)

    def _escape_csv(self, value):
        value = str(value)
        value.replace(self.ESCAPE, f'{self.ESCAPE}{self.ESCAPE}')
        if self.SEPARATOR in value or '\n' in value:
            value = f'{self.ESCAPE}{value}{self.ESCAPE}'

        return value

    def _write(self, line):
        for stream in self.streams:
            stream.write(f'{line}{self.LINE_SEPARATOR}')
            stream.flush()


class ExceptionCatcher(ContextDecorator):
    def __init__(self, where):
        self.where = where

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logger.log(
                EVENT_EXCEPTION,
                where=self.where,
                type=exc_type,
                exception=exc_val
            )
        return True  # suppress exception
