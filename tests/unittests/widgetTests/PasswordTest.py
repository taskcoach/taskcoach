"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2026 Task Coach developers <developers@taskcoach.org>

Task Coach is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Task Coach is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import copy
import sys
from unittest import mock

import keyring
import keyring.errors
import test
import wx
from taskcoachlib.widgets import password

NO_SERVICE = keyring.errors.NoKeyringError("No recommended backend")


class PasswordTestCase(test.wxTestCase):
    def setUp(self):
        super().setUp()
        # Never the user's keychain
        self.get = self.patch(keyring, "get_password", return_value=None)
        self.set = self.patch(keyring, "set_password")
        self.ask = self.patch(wx, "GetPasswordFromUser", return_value="secret")
        self.message = self.patch(wx, "MessageBox")
        cache = copy.copy(password._PASSWORDCACHE)
        self.patch(password, "_PASSWORDCACHE", new=cache)

    def patch(self, target, name, **kwargs):
        patcher = mock.patch.object(target, name, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()


class GetPasswordTest(PasswordTestCase):
    """The mail password where the keychain cannot be used (P177):
    asked once until Task Coach quits, without an error message."""

    def test_no_keychain_service(self):
        self.get.side_effect = NO_SERVICE
        for _ in range(2):
            self.assertEqual(
                "secret", password.GetPassword("imap.example.org", "me")
            )
        self.assertEqual(1, self.ask.call_count)
        self.message.assert_not_called()

    def test_wrong_password_asks_again(self):
        self.get.side_effect = self.set.side_effect = NO_SERVICE
        password.GetPassword("imap.example.org", "me")
        password.GetPassword("imap.example.org", "me", reset=True)
        self.assertEqual(2, self.ask.call_count)

    def test_no_keyring_package(self):
        with mock.patch.dict(sys.modules, keyring=None):
            self.assertEqual(
                "secret", password.GetPassword("imap.example.org", "me")
            )
        self.message.assert_not_called()


class KeychainPasswordWidgetTest(PasswordTestCase):
    def test_a_keychain_that_cannot_store_it(self):
        dialog = password.KeychainPasswordWidget(
            "imap.example.org", "me", self.frame, wx.ID_ANY, "Password"
        )
        # Unless destroyed with the test's frame
        self.addCleanup(lambda: dialog and dialog.Destroy())
        dialog.passwordField.SetValue("secret")
        self.set.side_effect = keyring.errors.PasswordSetError("Locked")
        with mock.patch.object(dialog, "EndModal") as end:
            dialog.OnOK(None)
        end.assert_called_once_with(wx.ID_OK)
        self.assertEqual("secret", dialog.password)
