"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>

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

import test, wx, os
from taskcoachlib.gui import splash


class SplashTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.splashScreen = splash.SplashScreen()
        self.splashScreen.Hide()

    def tearDown(self):
        self.splashScreen.Destroy()
        super().tearDown()

    def assertCorrectBitmap(self):
        # Load the expected bitmap from the splash.png file
        splash_path = splash.get_resource_path(os.path.join('icons', 'splash.png'))
        expectedImage = wx.Image(splash_path)
        expectedBitmap = expectedImage.ConvertToBitmap()
        actualBitmap = self.splashScreen.GetSplashWindow().GetBitmap()
        bitmapData = lambda bitmap: bitmap.ConvertToImage().GetData()
        self.assertEqual(bitmapData(expectedBitmap), bitmapData(actualBitmap))

    def testTimeout(self):
        self.assertEqual(4000, self.splashScreen.GetTimeout())

    def testBitmap(self):
        self.assertCorrectBitmap()

    def testMirrorBitmapBackWhenLanguageIsRTL(self):
        class FakeModule(object):
            def currentLanguageIsRightToLeft(self):
                return True

        splash.i18n = FakeModule()
        self.assertCorrectBitmap()
