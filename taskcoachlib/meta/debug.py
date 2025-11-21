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

import sys


def log_call(traceback_depth):
    """Decorator for function calls that prints the function name,
    arguments and result to stdout. Usage:

    @log_call(traceback_depth)
    def function(arg):
        ...
    """
    # Import here instead of at the module level to prevent unnecessary
    # inclusion of the inspect module when packaging the application:
    import inspect

    def outer(func):
        def inner(*args, **kwargs):
            result = func(*args, **kwargs)
            write = sys.stdout.write
            for frame in inspect.stack(context=2)[traceback_depth:0:-1]:
                write(format_traceback(frame))
            write("%s\n" % signature(func, args, kwargs, result))
            write("===\n")
            return result

        return inner

    return outer


def time_call(func):
    """Decorator for function calls that times the call."""

    import time

    def inner(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        stop = time.time()
        sys.stdout.write(
            "%s took %f seconds\n"
            % (signature(func, args, kwargs, result), stop - start)
        )
        return result

    return inner


def profile_call(func):
    """Docorator for profiling a specific function. I'm not sure what
    happens if you decorate a recursive function..."""

    import hotshot

    def inner(*args, **kwargs):
        profiler = hotshot.Profile(".profile")
        return profiler.runcall(func, *args, **kwargs)

    return inner


def signature(func, args, kwargs, result):
    func = func.__name__
    result = str(result)
    try:
        return "%s(%s, %s) -> %s" % (func, str(args), str(kwargs), result)
    except Exception:
        return "%s(...) -> %s" % (func, result)  # Args couldn't be stringified


def format_traceback(frame):
    result = []
    filename, lineno, caller, context = frame[1:5]
    result.append('  File "%s", line %s, in %s' % (filename, lineno, caller))
    for line in context:
        result.append(line[:-1])
    return "\n".join(result) + "\n"
