import errno
import os
from select import select


def mirror_and_capture(in_, out, err, chunk_size, finish=False, poll_timeout=0.05):
    """Read streams; mirror and capture output.

    Read from a subprocess's stdout and mirror it to the console's
    stdout (typically sys.stdout) and also capture it into a buffer.
    Ditto for stderr.

    On the input side, read the console's stdin (typicall sys.stdin) and
    mirror it to the subprocess's stdin. Input can be captured too, but
    it typically isn't.

    Args:
        in_ (int, int, bool, list): Read fd, write fd, mirror?, buffer
        out (int, int, bool, list): Read fd, write fd, mirror?, buffer
        err (int, int, bool, list): Read fd, write fd, mirror?, buffer
        chunk_size (int): Number of bytes to read
        finish (bool): Passed by the caller to indicate it's finished
        poll_timeout (float): How long to wait when `select`ing

    File descriptors must be integers. Buffers can be ``None`` to
    disable capture.

    """
    def _read(read_from, write_to, mirror, buffer, num_bytes, remove=True):
        try:
            data = os.read(read_from, num_bytes)
        except OSError as exc:
            if exc.errno != errno.EIO:
                raise
            data = None
        except ValueError:
            data = None
        if data:
            if mirror:
                try:
                    os.write(write_to, data)
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
                    if remove:
                        rlist.remove(read_from)
            if buffer is not None:
                buffer.append(data)
        elif finish and remove:
            rlist.remove(read_from)

    in_read, in_write, mirror_in, in_buffer = in_
    out_read, out_write, mirror_out, out_buffer = out
    err_read, err_write, mirror_err, err_buffer = err

    rlist, _, __ = select([in_read, out_read, err_read], [], [], poll_timeout)

    # XXX: I'm not entirely sure why we have to first read 0 bytes and
    #      then do a second read. Without the first read of 0 bytes,
    #      programs that accept single characters without requiring a
    #      newline behave strangely (e.g., less).
    if in_read in rlist:
        _read(in_read, in_write, mirror_in, in_buffer, 0)
        in_rlist, _, __ = select([in_read], [], [], poll_timeout)
        if in_read in in_rlist:
            _read(in_read, in_write, mirror_in, in_buffer, chunk_size, remove=False)

    if out_read in rlist:
        _read(out_read, out_write, mirror_out, out_buffer, chunk_size)

    if err_read in rlist:
        _read(err_read, err_write, mirror_err, err_buffer, chunk_size)

    return rlist
