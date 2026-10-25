import gzip
import io
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from archive_core import Cancelled, extract_archive, list_archive, stream_entry, CancellableReader


class CancellationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_cancelled_extraction_does_not_read_or_decompress(self):
        source = self.root / 'data.txt.gz'
        source.write_bytes(gzip.compress(b'x' * (5 * 1024 * 1024)))
        cancel = threading.Event()
        cancel.set()
        with patch('archive_core.list_archive') as listing:
            with self.assertRaises(Cancelled):
                extract_archive(source, self.root / 'out', cancel)
            listing.assert_not_called()

    def test_cancel_during_stream_listing_stops_before_second_read(self):
        cancel = threading.Event()
        reads = []
        class Reader(io.BytesIO):
            def read(self, size=-1):
                reads.append(size)
                cancel.set()
                return super().read(size)
        with patch.dict('archive_core.STREAM_OPENERS', {'gz': lambda *args: Reader(b'x' * (2 * 1024 * 1024))}):
            with self.assertRaises(Cancelled):
                stream_entry('unused.gz', 'gz', cancel)
        self.assertEqual(len(reads), 1)

    def test_cancelled_listing_does_not_start_format_detection(self):
        cancel = threading.Event()
        cancel.set()
        with patch('archive_core.archive_kind') as detect:
            with self.assertRaises(Cancelled):
                list_archive('unused.rar', cancel)
            detect.assert_not_called()

    def test_tar_reader_observes_cancellation_before_read_and_seek(self):
        cancel = threading.Event()
        raw = io.BytesIO(b'1234')
        reader = CancellableReader(raw, cancel)
        self.assertEqual(reader.read(1), b'1')
        cancel.set()
        for operation in (lambda: reader.read(1), lambda: reader.readinto(bytearray(1)), lambda: reader.seek(0)):
            with self.assertRaises(Cancelled):
                operation()
        self.assertEqual(raw.tell(), 1)
