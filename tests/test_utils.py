import unittest
import unittest.mock as mock

import os
from sm.core import util
import errno


class fake_proc:

    def __init__(self):
        self.returncode = 0

    def communicate(self, inputtext):
        return b"hello", b"hello"


@mock.patch('sm.core.xs_errors.XML_DEFS', 'libs/sm/core/XE_SR_ERRORCODES.xml')
class TestCreate(unittest.TestCase):

    @mock.patch('subprocess.Popen', autospec=True)
    def test_env_concatenated(self, popen):
        new_env = {"NewVar1": "yadayada", "NewVar2": "blah"}
        popen.return_value = fake_proc()
        with mock.patch.dict('os.environ', {'hello': 'world'}, clear=True):
            self.assertEqual(os.environ.get('hello'), 'world')
            util.pread(['mount.cifs', '\\aServer',
                        '/run/sr-mount/asr_uuid',
                        '-o', 'cache=loose,vers=3.0,actimeo=0,domain=citrix'],
                       new_env=new_env)
            expected_cmd = ['mount.cifs', '\\aServer',
                            '/run/sr-mount/asr_uuid', '-o',
                            'cache=loose,vers=3.0,actimeo=0,domain=citrix']
            popen.assert_called_with(expected_cmd,
                                     close_fds=True, stdin=-1, stderr=-1,
                                     env={'hello': 'world', 'NewVar2': 'blah',
                                          'NewVar1': 'yadayada'}, stdout=-1,
                                     universal_newlines=True)

    @mock.patch("sm.core.util.os.fsync", autospec=True)
    @mock.patch("sm.core.util.os.rename", autospec=True)
    @mock.patch("sm.core.util.os.path.isfile", autospec=True)
    @mock.patch("sm.core.util.os.remove", autospec=True)
    @mock.patch("sm.core.util.tempfile.mkstemp", autospec=True)
    @mock.patch("sm.core.util.SMlog", autospec=True)
    def test_atomicFileWrite_normal(self, mock_log, mock_mtemp, mock_remove,
                                    mock_isfile, mock_rename, mock_fsync):
        opener_mock = mock.mock_open()

        mock_isfile.return_value = False
        mock_mtemp.return_value = ("im_ignored",
                                   "/run/random_temp.txt")
        with mock.patch('builtins.open', opener_mock, create=True) as m:

            m.return_value.fileno.return_value = 123
            util.atomicFileWrite("/run/test.txt", "var/run", "blah blah")

            self.assertEqual(mock_mtemp.call_count, 1)
            m.assert_called_with("/run/random_temp.txt", 'w')
            m.return_value.write.assert_called_with("blah blah")
            self.assertEqual(m.return_value.flush.call_count, 1)
            mock_fsync.assert_called_with(123)
            self.assertEqual(m.return_value.close.call_count, 1)
            mock_rename.assert_called_with("/run/random_temp.txt",
                                           "/run/test.txt")
            mock_isfile.assert_called_with("/run/random_temp.txt")
            self.assertEqual(mock_remove.call_count, 0)

    @mock.patch("sm.core.util.os.fsync", autospec=True)
    @mock.patch("sm.core.util.os.rename", autospec=True)
    @mock.patch("sm.core.util.os.path.isfile", autospec=True)
    @mock.patch("sm.core.util.os.remove", autospec=True)
    @mock.patch("sm.core.util.tempfile.mkstemp", autospec=True)
    @mock.patch("sm.core.util.SMlog", autospec=True)
    def test_atomicFileWrite_exception(self, mock_log, mock_mtemp, mock_remove,
                                       mock_isfile, mock_rename, mock_fsync):

        opener_mock = mock.mock_open()

        mock_isfile.return_value = True
        mock_mtemp.return_value = ("im_ignored",
                                   "/run/random_temp.txt")
        with mock.patch('builtins.open', opener_mock, create=True) as m:
            m.return_value.write.side_effect = OSError((errno.EPERM),
                                                       'Not Allowed')
            m.return_value.closed = False
            # Assert is swallowed
            util.atomicFileWrite("/run/test.txt", "var/run",
                                 "blah blah")
            expectedMsg = "FAILED to atomic write to /run/test.txt"
            mock_log.assert_called_with(expectedMsg)
            mock_remove.assert_called_with("/run/random_temp.txt")
            self.assertEqual(opener_mock.return_value.close.call_count, 1)
