#!/usr/bin/env python

import time
import gevent
import datetime
from gevent import monkey
monkey.patch_all()  # Patch everything


class Hub(object):
    """A simple reactor hub... In async!"""

    def __init__(self, name=None):
        self.name = name
        self.handlers = {}

    def on(self, event_name, handler):
        """Binds an event to a function."""
        handlers = self.handlers.get(event_name, [])
        if not handler in handlers:
            handlers.append(handler)
            self.handlers[event_name] = handlers

    def off(self, event_name, handler):
        """Unbinds an event to a function."""
        handlers = self.handlers.get(event_name, [])
        handlers.remove(handler)

    def emit(self, event_name, *args, **kwargs):
        """Calls an event. You can also pass arguments."""
        handlers = self.handlers.get(event_name, [])
        for handler in handlers:
            # XXX: If spawned within a greenlet, there's no need to join
            # the greenlet. It is automatically executed.
            gevent.spawn(handler, *args, **kwargs)

    def start(self, *entry_points):
        """Run entry point."""
        gevent.joinall([gevent.spawn(ep) for ep in entry_points])


##
#
# Usage...
#
# Here's an example that uses redis' pub/sub feature.
##


# Create an instance of the hub.
hub = Hub(name='myhub')


def append(line):
    if int(line.split(" ")[1]) == 10:
        time.sleep(10)
    with open("sample.txt", "a") as file_object:
        # Append 'hello' at the end of file
        file_object.write(f"{line}\n")


hub.on('data.write', append)


def entry_point():
    for data in [f'{i}' for i in range(10000)]:
        hub.emit('data.write',
                 f"{datetime.datetime.now().timestamp()*1000} {data}")


if __name__ == '__main__':
    hub.start(entry_point)
