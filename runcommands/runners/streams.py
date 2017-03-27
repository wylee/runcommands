import io
import os
import time

from locale import getpreferredencoding
from threading import Thread


class NonBlockingStreamReader(Thread):

    def __init__(self, name, stream, hide, file, chunk_size=io.DEFAULT_BUFFER_SIZE, encoding=None):
        name = '{name}-reader'.format(name=name)
        super().__init__(name=name, daemon=True)

        self.stream = stream
        self.hide = hide
        self.file = file
        self.chunk_size = chunk_size
        self.encoding = encoding or getpreferredencoding(do_setlocale=False)

        self.lines = []
        self.last_segment = None

        self.finished = False
        self.start()

    def run(self):
        # Read stream until told to stop; stream may or may not be
        # closed at this point.
        while not self.finished:
            if self.read() is None:
                # Stream is closed; no need to continue.
                return
            time.sleep(0.1)
        # Read until stream is closed or EOF is reached.
        while self.read():
            time.sleep(0.1)

    def finish(self):
        self.finished = True
        self.join()

    def read(self):
        if self.stream.closed:
            return None

        # Before doing the next read, flush last segment.
        if self.last_segment:
            self.lines.append(self.last_segment)
            if not self.hide:
                self.file.write(self.last_segment)
                self.file.flush()
            self.last_segment = None

        try:
            data = self.stream.read(self.chunk_size)
        except ValueError:
            # Stream was closed in the meantime
            return None

        if data:
            text = data.decode(self.encoding) if isinstance(data, bytes) else data

            # XXX: Currently, this will never happen
            if self.last_segment:
                text = ''.join((self.last_segment, text))
                self.last_segment = None

            *lines, segment = text.splitlines(keepends=True)

            if segment.endswith(os.linesep):
                lines.append(segment)
            else:
                self.last_segment = segment

            if lines:
                self.lines.extend(lines)
                if not self.hide:
                    self.file.writelines(lines)
                    self.file.flush()

        # XXX: Currently, this will never happen
        elif self.last_segment:
            self.lines.append(self.last_segment)
            if not self.hide:
                self.file.write(self.last_segment)
                self.file.flush()
            self.last_segment = None

        return data

    def get_string(self):
        return ''.join(self.lines)
