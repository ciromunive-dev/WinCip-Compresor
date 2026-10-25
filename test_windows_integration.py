"""Exercise install/uninstall registry changes inside an isolated user subtree."""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid
import winreg

import windows_integration as integration


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.exe = Path(self.temp.name) / 'WinCip.exe'
        self.exe.write_bytes(b'fixture')
        self.exe.with_name('WinCipShell-3.2.dll').write_bytes(b'fixture')
        self.hive = 'Software\\WinCipInstallerTests\\' + uuid.uuid4().hex
        self.original_hkcu = winreg.HKEY_CURRENT_USER
        self.sandbox = winreg.CreateKey(self.original_hkcu, self.hive)
        self.override = patch.object(winreg, 'HKEY_CURRENT_USER', self.sandbox.handle)
        self.override.start()
        self.addCleanup(self.dispose)
        self.runner = patch('windows_integration.subprocess.run')
        self.run = self.runner.start()
        self.run.return_value.returncode = 0
        self.addCleanup(self.runner.stop)

    def dispose(self):
        integration.delete_owned_key(r'Software')
        self.override.stop()
        self.sandbox.Close()
        winreg.DeleteKey(self.original_hkcu, self.hive)

    def read(self, path, name=''):
        with winreg.OpenKey(self.sandbox.handle, path) as key:
            return winreg.QueryValueEx(key, name)[0]

    def test_register_then_unregister_removes_owned_records_only(self):
        defaults = r'Software\Classes\.zip'
        integration.set_value(defaults, '', 'Other.Archive')
        integration.set_value(defaults + r'\OpenWithProgids', 'Other.Archive', '')
        integration.register(self.exe)
        self.assertEqual(self.read(defaults), 'Other.Archive')
        self.assertEqual(self.read(r'Software\WinCip\Capabilities', 'ApplicationName'), 'WinCip Compresor')
        integration.unregister(self.exe)
        self.assertEqual(self.read(defaults), 'Other.Archive')
        self.assertEqual(self.read(defaults + r'\OpenWithProgids', 'Other.Archive'), '')
        for key in (r'Software\Classes\WinCip.Archive', r'Software\WinCip\Capabilities',
                    r'Software\Classes\*\shell\WinCip'):
            with self.assertRaises(FileNotFoundError):
                self.read(key)

    def test_uninstall_does_not_remove_a_different_installation(self):
        integration.register(self.exe)
        other = self.exe.parent / 'other' / 'WinCip.exe'
        integration.unregister(other)
        self.assertEqual(self.read(r'Software\Classes\WinCip.Archive\shell\open\command'),
                         f'"{self.exe}" "%1"')
        self.assertEqual(self.read(r'Software\Classes\*\shell\WinCip', 'Icon'), f'"{self.exe}",0')

    def test_windows_10_uses_classic_menu_without_registering_modern_package(self):
        with patch.object(integration.sys, 'getwindowsversion', return_value=SimpleNamespace(build=19045)), \
             patch.object(integration, 'register') as register, \
             patch.object(integration, 'install_modern_menu') as modern, \
             patch.object(integration.os, 'startfile') as defaults:
            integration.open_defaults()
            register.assert_called_once()
            modern.assert_not_called()
            defaults.assert_called_once_with('ms-settings:defaultapps')

        with patch.object(integration.sys, 'getwindowsversion', return_value=SimpleNamespace(build=19045)):
            with self.assertRaisesRegex(RuntimeError, 'Windows 11'):
                integration.install_modern_menu(self.exe)
        self.run.assert_not_called()

    def test_windows_11_keeps_modern_menu_and_direct_default_apps_link(self):
        with patch.object(integration.sys, 'getwindowsversion', return_value=SimpleNamespace(build=22631)), \
             patch.object(integration.sys, 'frozen', True, create=True), \
             patch.object(integration.sys, 'executable', str(self.exe)), \
             patch.object(integration, 'register'), \
             patch.object(integration, 'install_modern_menu') as modern, \
             patch.object(integration.os, 'startfile') as defaults:
            integration.open_defaults()
            modern.assert_called_once_with(self.exe)
            defaults.assert_called_once_with('ms-settings:defaultapps?registeredAppUser=WinCip')


if __name__ == '__main__':
    unittest.main()
