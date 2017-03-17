from locale import getpreferredencoding
from threading import Thread


class NonBlockingStreamReader(Thread):

    def __init__(self, name, stream, buffer, hide, file, encoding=None):
        name = '{name}-reader'.format(name=name)
        super().__init__(name=name, daemon=True)
        self.stream = stream
        self.buffer = buffer
        self.hide = hide
        self.file = file
        self.encoding = encoding or getpreferredencoding(do_setlocale=False)
        self.finished = False
        self.start()

    def run(self):
        # Read stream until told to stop; stream may or may not be
        # closed at this point.
        while not self.finished:
            if self.read() is None:
                # Stream is closed; no need to continue.
                return
        # Read until stream is closed or EOF is reached.
        while self.read():
            pass

    def finish(self):
        self.finished = True
        self.join()

    def read(self):
        if self.stream.closed:
            return None
        try:
            data = self.stream.readline()
        except ValueError:
            return None
        if data:
            if isinstance(data, bytes):
                text = data.decode(self.encoding)
            else:
                text = data
            self.buffer.append(text)
            if not self.hide:
                self.file.write(text)
                self.file.flush()
        return data

    def get_string(self):
        return ''.join(self.buffer)
