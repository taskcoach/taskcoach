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

from taskcoachlib import patterns
from . import dateandtime, timedelta
import logging
import weakref
import bisect


class ScheduledMethod(object):
    def __init__(self, method):
        self.__func = method.__func__
        self.__self = weakref.ref(method.__self__)
        self.__id = None

    def setId(self, id_):
        self.__id = id_

    def __eq__(self, other):
        return (
            self.__func is other.__func
            and self.__self() is other.__self()
            and self.__id == other.__id
        )

    def __lt__(self, other):
        lvalue = 0 if self.__id is None else self.__id
        rvalue = 0 if other.__id is None else other.__id
        return lvalue < rvalue

    def __hash__(self):
        return hash((self.__dict__["_ScheduledMethod__func"], self.__id))

    def __call__(self, *args, **kwargs):
        obj = self.__self()
        if obj is None:
            Scheduler().unschedule(self)
        else:
            self.__func(obj, *args, **kwargs)


class TwistedScheduler(object):
    """
    A class to schedule jobs at specified date/time. Unlike apscheduler, this
    uses Twisted instead of threading, in order to avoid busy waits.
    """

    def __init__(self):
        super().__init__()
        self.__jobs = []
        self.__nextCall = None
        self.__firing = False

    def __schedule(self, job, dateTime, interval):
        if self.__nextCall is not None:
            self.__nextCall.cancel()
            self.__nextCall = None
        bisect.insort_right(self.__jobs, (dateTime, job, interval))
        if not self.__firing:
            self.__fire()

    def scheduleDate(self, job, dateTime):
        """
        Schedules 'job' to be called at 'dateTime'. This assumes the caller is the
        main loop thread.
        """
        self.__schedule(job, dateTime, None)

    def scheduleInterval(self, job, interval, startDateTime=None):
        self.__schedule(
            job, startDateTime or dateandtime.Now() + interval, interval
        )

    def unschedule(self, theJob):
        for idx, (ts, job, interval) in enumerate(self.__jobs):
            if job == theJob:
                del self.__jobs[idx]
                break

    def isScheduled(self, theJob):
        for ts, job, interval in self.__jobs:
            if job == theJob:
                return True
        return False

    def shutdown(self):
        if self.__nextCall is not None:
            self.__nextCall.cancel()
            self.__nextCall = None
        self.__jobs = []

    def jobs(self):
        return [job for ts, job, interval in self.__jobs]

    def __fire(self):
        self.__firing = True
        try:
            while self.__jobs and self.__jobs[0][0] <= dateandtime.Now():
                ts, job, interval = self.__jobs.pop(0)
                try:
                    job()
                except Exception:
                    # Log exceptions from scheduled jobs but continue
                    import traceback

                    traceback.print_exc()
                if interval is not None:
                    self.__schedule(job, ts + interval, interval)
        finally:
            self.__firing = False

        if self.__jobs and self.__nextCall is None:
            dt = self.__jobs[0][0] - dateandtime.Now()
            nextDuration = int(
                (dt.microseconds + (dt.seconds + dt.days * 24 * 3600) * 10**6)
                / 10**3
            )
            nextDuration = max(nextDuration, 1)
            nextDuration = min(nextDuration, 2**31 - 1)
            from twisted.internet import reactor

            self.__nextCall = reactor.callLater(
                nextDuration / 1000, self.__callback
            )

    def __callback(self):
        self.__nextCall = None
        self.__fire()


class Scheduler(object, metaclass=patterns.Singleton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__scheduler = TwistedScheduler()

    def shutdown(self):
        self.__scheduler.shutdown()

    def schedule(self, function, dateTime):
        job = ScheduledMethod(function)
        self.__scheduler.scheduleDate(job, dateTime)
        return job

    def schedule_interval(self, function, days=0, minutes=0, seconds=0):
        job = ScheduledMethod(function)
        if not self.__scheduler.isScheduled(job):
            startDate = dateandtime.Now().endOfDay() if days > 0 else None
            self.__scheduler.scheduleInterval(
                job,
                timedelta.TimeDelta(
                    days=days, minutes=minutes, seconds=seconds
                ),
                startDateTime=startDate,
            )
            return job

    def unschedule(self, function):
        job = (
            function
            if isinstance(function, ScheduledMethod)
            else ScheduledMethod(function)
        )
        self.__scheduler.unschedule(job)

    def is_scheduled(self, function):
        return self.__scheduler.isScheduled(ScheduledMethod(function))

    def get_jobs(self):
        return self.__scheduler.jobs()
