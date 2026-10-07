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


class Singleton(type):
    """Singleton metaclass. Use by defining the metaclass of a class Singleton,
    e.g.: class ThereCanBeOnlyOne:
              __metaclass__ = Singleton
    """

    def __call__(cls, *args, **kwargs):
        if not cls.hasInstance():
            # pylint: disable=W0201
            cls.instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.instance

    def deleteInstance(cls):
        """Delete the (only) instance. This method is mainly for unittests so
        they can start with a clean slate."""
        if cls.hasInstance():
            del cls.instance

    def hasInstance(cls):
        """Has the (only) instance been created already?"""
        return "instance" in cls.__dict__
