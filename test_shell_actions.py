"""Explorer command queue integration, including password retries."""
import queue
from pathlib import Path
import tempfile
import threading
import unittest
from archive_core import create_archive, Cancelled, PasswordRequired
from features import Features
from workflows import BatchFailure

class ShellQueue(Features):
    def __init__(self):
        self.busy = False
        self.cancel = threading.Event()
        self.events = queue.Queue()
        self.report = lambda *args: None
        self.completed = lambda result: None
    def run_job(self, label, operation, callback):
        self.operation = operation

class ShellActionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.first = self.root / 'primero con espacios.txt'
        self.first.write_bytes(b'first')
        self.second = self.root / 'segundo.txt'
        self.second.write_bytes(b'second')
        self.app = ShellQueue()

    def test_multiple_archives_each_get_a_folder(self):
        paths = [create_archive([self.first], self.root / 'one.zip'), create_archive([self.second], self.root / 'two.zip')]
        self.app.extract_paths(paths)
        self.app.operation()
        self.assertEqual((self.root / 'one' / self.first.name).read_bytes(), b'first')
        self.assertEqual((self.root / 'two' / self.second.name).read_bytes(), b'second')

    def test_password_retry_keeps_finished_archives(self):
        paths = [create_archive([self.first], self.root / 'one.zip'), create_archive([self.second], self.root / 'two.zip', password='secret')]
        destination = self.root / 'out'
        destination.mkdir()
        self.app.extract_paths(paths, destination=destination)
        with self.assertRaises(PasswordRequired):
            self.app.operation()
        self.assertEqual(self.app.batch_password_path, paths[1])
        self.app.batch_secrets[paths[1]] = 'secret'
        self.app.operation()
        self.assertEqual(len(list(destination.iterdir())), 2)
        self.assertEqual((destination / 'two' / self.second.name).read_bytes(), b'second')

    def test_extract_here_renames_existing_files(self):
        archive = create_archive([self.first], self.root / 'one.zip')
        self.app.extract_paths([archive], here=True)
        self.app.operation()
        self.assertEqual(self.first.read_bytes(), b'first')
        self.assertEqual((self.root / 'primero con espacios (2).txt').read_bytes(), b'first')

    def test_cancelled_queue_writes_nothing(self):
        archive = create_archive([self.first], self.root / 'one.zip')
        self.app.extract_paths([archive])
        self.app.cancel.set()
        with self.assertRaises(Cancelled):
            self.app.operation()
        self.assertFalse((self.root / 'one').exists())

    def test_skipping_broken_archive_continues_batch(self):
        first = create_archive([self.first], self.root / 'one.zip')
        broken = self.root / 'broken.zip'
        broken.write_bytes(b'not an archive')
        last = create_archive([self.second], self.root / 'three.zip')
        self.app.extract_paths([first, broken, last])
        with self.assertRaises(BatchFailure) as failure:
            self.app.operation()
        self.assertEqual(failure.exception.path, broken)
        self.assertEqual((self.root / 'one' / self.first.name).read_bytes(), b'first')
        self.app.batch_skip()
        self.app.operation()
        self.assertEqual((self.root / 'three' / self.second.name).read_bytes(), b'second')
        completed, omitted, pending = self.app.batch_report
        self.assertEqual((len(completed), len(omitted), len(pending)), (2, 1, 0))

if __name__ == '__main__':
    unittest.main()
