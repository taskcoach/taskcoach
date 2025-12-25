
from twisted.application import service
from buildslave.bot import BuildSlave

basedir = r'c:\dev\buildslave'
buildmaster_host = 'jeromelaheurte.net'
port = 9989
slavename = 'WinXPSP3'
passwd = open('.passwd', 'rb').readlines()[0].strip()
keepalive = 600
usepty = 1
umask = None

application = service.Application('buildslave')
s = BuildSlave(buildmaster_host, port, slavename, passwd, basedir,
               keepalive, usepty, umask=umask)
s.setServiceParent(application)

