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

DESIGN NOTE (Twisted Removal - 2024):
Previously used Twisted's Deferred and reactor.callLater for async service
registration. Now uses a simple callback-based pattern with wx.CallAfter
for thread-safe GUI interaction.

The key changes:
- Twisted Deferred → AsyncResult class with callback/errback pattern
- reactor.callLater(0, fn) → wx.CallAfter(fn)
- Failure → standard Exception handling

This maintains the async pattern for callers while eliminating Twisted dependency.
"""

import socket
import wx
from zeroconf import Zeroconf, ServiceInfo


class AsyncResult:
    """
    Simple async result handler replacing Twisted's Deferred.

    Provides callback/errback pattern for async operations.
    This is a minimal replacement for Twisted Deferred that
    maintains API compatibility with existing callers.
    """

    def __init__(self):
        self._callbacks = []
        self._errbacks = []
        self._result = None
        self._error = None
        self._called = False

    def addCallback(self, callback):
        """Add a callback for successful completion."""
        if self._called:
            if self._error is None:
                callback(self._result)
        else:
            self._callbacks.append(callback)
        return self

    def addErrback(self, errback):
        """Add an error handler for failure."""
        if self._called:
            if self._error is not None:
                errback(self._error)
        else:
            self._errbacks.append(errback)
        return self

    def callback(self, result):
        """Fire the deferred with a successful result."""
        if self._called:
            return
        self._called = True
        self._result = result
        for cb in self._callbacks:
            try:
                cb(result)
            except Exception:
                pass

    def errback(self, error):
        """Fire the deferred with an error."""
        if self._called:
            return
        self._called = True
        self._error = error
        for eb in self._errbacks:
            try:
                eb(error)
            except Exception:
                pass


class BonjourServiceDescriptor(object):
    """
    Wrapper for Zeroconf service registration.

    This class manages the lifecycle of a registered Bonjour/Zeroconf service,
    providing start/stop methods for integration with the application lifecycle.

    Previously used pybonjour with Twisted reactor integration. Now uses
    python-zeroconf which is pure Python and doesn't require system Bonjour
    libraries or reactor file descriptor polling.
    """

    def __init__(self):
        self._zeroconf = None
        self._service_info = None

    def start(self, service_info):
        """
        Start the Zeroconf service registration.

        Args:
            service_info: A ServiceInfo object describing the service to register
        """
        self._zeroconf = Zeroconf()
        self._service_info = service_info
        self._zeroconf.register_service(service_info)

    def stop(self):
        """
        Stop and unregister the Zeroconf service.

        This should be called during application shutdown to properly
        clean up the service registration.
        """
        if self._zeroconf is not None:
            if self._service_info is not None:
                self._zeroconf.unregister_service(self._service_info)
                self._service_info = None
            self._zeroconf.close()
            self._zeroconf = None

    def logPrefix(self):
        """Return log prefix for this service."""
        return "bonjour"


def BonjourServiceRegister(settings, port):
    """
    Register a Bonjour/Zeroconf service for iPhone sync discovery.

    This function registers a '_taskcoachsync._tcp' service on the local
    network, allowing iPhone/iPad devices to automatically discover the
    Task Coach sync service without manual configuration.

    The service type is registered at http://www.dns-sd.org/ServiceTypes.html

    Args:
        settings: Application settings object with iPhone configuration
        port: The port number the sync service is listening on

    Returns:
        An AsyncResult that fires with the BonjourServiceDescriptor
        on success, or errbacks with a RuntimeError on failure.

    DESIGN NOTE (Twisted Removal - 2024):
    Previously returned a Twisted Deferred. Now returns an AsyncResult
    which provides the same callback/errback interface but without
    Twisted dependency.
    """
    d = AsyncResult()
    reader = BonjourServiceDescriptor()

    def do_register():
        try:
            # Get service name from settings, or use default
            service_name = settings.get("iphone", "service") or "Task Coach"

            # Create ServiceInfo for the sync service
            # Service type format: "_service._protocol.local."
            service_type = "_taskcoachsync._tcp.local."
            service_full_name = f"{service_name}.{service_type}"

            # Get local IP addresses for service registration
            # Using empty list lets zeroconf use all available interfaces
            addresses = []
            try:
                # Try to get the primary local IP
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                if local_ip and local_ip != "127.0.0.1":
                    addresses = [socket.inet_aton(local_ip)]
            except socket.error:
                pass  # Will use all interfaces if we can't get specific IP

            service_info = ServiceInfo(
                service_type,
                service_full_name,
                port=port,
                addresses=addresses if addresses else None,
                properties={},
            )

            reader.start(service_info)
            d.callback(reader)

        except Exception as e:
            reader.stop()
            d.errback(
                RuntimeError(f"Could not register with Bonjour/Zeroconf: {e}")
            )

    # Schedule registration on main thread using wx.CallAfter
    # NOTE: Previously used reactor.callLater(0, do_register)
    wx.CallAfter(do_register)
    return d
