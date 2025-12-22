#!/usr/bin/env python

'''
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
'''

# Sanity check
import sys
PYTHONEXE = sys.executable

import struct
if sys.platform == 'darwin':
    if len(struct.pack('L', 0)) == 8:
        # arch -i386 <path to python> release.py ...
        raise RuntimeError('Please use 32 bits python to run this script')


HELP_TEXT = '''
Release steps:
  - Get latest translations from Launchpad:
    * Go to https://translations.launchpad.net/taskcoach/<major.minor>/+export
    * Wait for the confirmation email from Launchpad and copy the URL
    * Run 'cd i18n.in && python make.py <url>' to update the translations
    * Run 'make languagetests' to test the translations
    * When all tests pass, run 'hg commit -m "Updated translations"' 
  - Run 'make reallyclean' to remove old packages.
  - Run 'make alltests'.
  - Run 'python release.py release' to build the distributions, upload and download them
    to/from Sourceforge, generate MD5 digests, generate the website, upload the 
    website to the Dreamhost and Hostland websites, announce the release on 
    Twitter, and PyPI (Python Package Index), mark the bug reports
    on SourceForge fixed-and-released, send the 
    announcement email, mark .dmg and .exe files as default downloads for their
    platforms, and to tag the release in Mercurial.
  - Create branch if feature release.
  - Merge recent changes to the trunk.
  - Add release to Sourceforge bug tracker and support request groups.
  - Mark feature requests on Uservoice completed.
  - If new release branch, update the buildbot masters configuration.
'''

import ftplib
import smtplib
import http.client
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import http.cookiejar
import os
import glob
import sys
import getpass
import hashlib
import base64
import configparser
import codecs
import optparse
import taskcoachlib.meta
import oauth2 as oauth
import time
import shutil
import zipfile
import subprocess

try:
    import simplejson as json
except ImportError:
    import json

# pylint: disable=W0621,W0613


def progress(func):
    ''' Decorator to print out a message when a release step starts and print
        a message when the release step is finished. '''
    def inner(*args, **kwargs):
        step = func.__name__.replace('_', ' ')
        print(step[0].upper() + step[1:] + '...')
        func(*args, **kwargs)
        print('Done %s.' % step)
    return inner


class Settings(configparser.SafeConfigParser):
    def __init__(self):
        super().__init__()
        self.set_defaults()
        self.filename = os.path.expanduser('~/.tcreleaserc')
        self.read(self.filename)

    def set_defaults(self):
        defaults = dict(webhost=['hostname', 'username', 'path'],
                        sourceforge=['username', 'password', 'consumer_key',
                                     'consumer_secret', 'oauth_token',
                                     'oauth_token_secret', 'api_key'],
                        smtp=['hostname', 'port', 'username', 'password',
                              'sender_name', 'sender_email_address'],
                        pypi=['username', 'password'],
                        twitter=['consumer_key', 'consumer_secret',
                                 'oauth_token', 'oauth_token_secret'],
                        buildbot=['username', 'password', 'host'])
        for section in defaults:
            self.add_section(section)
            for option in defaults[section]:
                self.set(section, option, 'ask')

    def get(self, section, option):  # pylint: disable=W0221
        value = super().get(section, option)
        if value == 'ask':
            get_input = getpass.getpass if option == 'password' else raw_input
            value = get_input('%s %s: ' % (section, option)).strip()
            self.set(section, option, value)
            self.write(open(self.filename, 'w'))
        return value


class HelpFormatter(optparse.IndentedHelpFormatter):
    ''' Don't mess up the help text formatting. '''
    def format_epilog(self, epilog):
        return epilog


class SFAPIError(Exception):
    pass


class SourceforgeAPI(object):
    def __init__(self, settings, options):
        consumer_key = settings.get('sourceforge', 'consumer_key')
        consumer_secret = settings.get('sourceforge', 'consumer_secret')
        consumer = oauth.Consumer(key=consumer_key, secret=consumer_secret)
        oauth_token = settings.get('sourceforge', 'oauth_token')
        oauth_token_secret = settings.get('sourceforge', 'oauth_token_secret')
        token = oauth.Token(key=oauth_token, secret=oauth_token_secret)
        self.client = oauth.Client(consumer, token)
        self.verbose = options.verbose
        self.dry_run = options.dry_run

    def __apply(self, func, data=None):
        url = 'https://sourceforge.net/rest/p/taskcoach/' + func
        if data is None:
            response, content = self.client.request(url)
            ok = 200
        else:
            response, content = self.client.request(url, method='POST', body=urllib.parse.urlencode(data))
            ok = 302
        if response.status != ok:
            raise SFAPIError(response.status)
        if data is None:
            return json.loads(content)

    def fix(self, id_):
        if self.dry_run:
            print('Skipping marking #%s fixed' % id_)
        else:
            ticketData = self.__apply('bugs/%s' % id_)['ticket']
            # Status: fixed; priority: 1
            data = [('ticket_form.status', 'fixed')]
            for name, value in list(ticketData.get('custom_fields', dict()).items()):
                if name == '_priority':
                    value = '1'
		if name == '_milestone': # WTF?
		    data.append(('ticket_form._milestone', value))
		else:
		    data.append(('ticket_form.custom_fields.%s' % name, value))
            self.__apply('bugs/%s/save' % id_, data=data)

            # Canned response
            self.__apply('bugs/_discuss/thread/%s/new' % ticketData['discussion_thread']['_id'],
                         data=[('text', '''A fix was made and checked into the source code repository of Task Coach. The fix will be part of the next release. You will get another notification when that release is available with the request to install the new release and confirm that your issue has indeed been fixed.

If you like, you can download a recent build from http://www.fraca7.net/TaskCoach-packages/latest_bugfixes.py to test the fix.

Because a fix has been made for this bug report, the priority of this report has been lowered to 1 and its resolution has been set to 'Fixed'.
Thanks, Task Coach development team''')])

            if self.verbose:
                print('Bug #%s fixed.' % id_)

    def release(self, id_):
        if self.dry_run:
            print('Skipping marking #%s released.' % id_)
        else:
            try:
                ticketData = self.__apply('bugs/%s' % id_)['ticket']
                self.__apply('bugs/%s/save' % id_, data=[('ticket_form.status', 'fixed-and-released')])
                self.__apply('bugs/_discuss/thread/%s/new' % ticketData['discussion_thread']['_id'],
                             data=[('text', '''This bug should be fixed in the latest release of Task Coach. Can you please install the latest release of Task Coach and confirm that this bug has indeed been fixed?

Thanks, Task Coach development team''')])
            except SFAPIError:
                print('Warning: could not marking fix #%s released.' % id_)


class FOSSHubAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.baseuri = 'https://api.fosshub.com/rest/'
        self.connection = http.client.HTTPSConnection('api.fosshub.com')

    def get(self, endpoint, **headers):
        headers['X-Auth-Key'] = self.api_key
        self.connection.request('GET', '%s%s' % (self.baseuri, endpoint), headers=headers)
        response = self.connection.getresponse()
        if response.status != 200:
            raise RuntimeError('Request failed: %d %s' % (response.status, response.reason))
        data = json.load(response)
        if data['error'] is not None:
            raise RuntimeError('Request failed: %s %s' % (data['code'], data['text']))
        return data['data']

    def post(self, endpoint, data, **headers):
        headers['X-Auth-Key'] = self.api_key
        headers['Content-Type'] = 'application/json'
        self.connection.request('POST', '%s%s' % (self.baseuri, endpoint), json.dumps(data), headers)
        response = self.connection.getresponse()
        if response.status != 200:
            raise RuntimeError('Request failed: %d %s' % (response.status, response.reason))
        data = json.load(response)
        if data['error'] is not None:
            raise RuntimeError('Request failed: %s %s' % (data['code'], data['text']))
        return data['status']


def sourceforge_location(settings):
    metadata = taskcoachlib.meta.data.metaDict
    project = metadata['filename_lower']
    project_first_two_letters = project[:2]
    project_first_letter = project[0]
    username = '%s,%s' % (settings.get('sourceforge', 'username'), project)
    folder = '/home/frs/project/%(p)s/%(pr)s/%(project)s/%(project)s/' \
             'Release-%(version)s/' % dict(project=project, 
                                           pr=project_first_two_letters, 
                                           p=project_first_letter, 
                                           version=metadata['version'])
    return '%s@frs.sourceforge.net:%s' % (username, folder)


def rsync(settings, options, rsync_command):
    location = sourceforge_location(settings)
    rsync_command = rsync_command % location
    if options.dry_run:
        print('Skipping %s.' % rsync_command)
    else:
        os.system(rsync_command)


@progress
def building_packages(settings, options):
    host = settings.get('buildbot', 'host')
    metadata = taskcoachlib.meta.data.metaDict
    branch = 'Release%s_Branch' % '_'.join(metadata['version'].split('.')[:2])
    if options.dry_run:
        print('Skipping force build on branch "%s"' % branch)
    else:
        status = json.load(urllib.request.urlopen('http://%s:8010/json/builders/Release' % host))
        if status['state'] != 'idle':
            raise RuntimeError('Builder Release is not idle.')

        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        for i in range(3): # Retry in case of 500
            try:
                opener.open('http://%s:8010/login' % host,
                            urllib.parse.urlencode([('username', settings.get('buildbot', 'username')),
                                              ('passwd', settings.get('buildbot', 'password'))]))
                opener.open('http://%s:8010/builders/Release/force' % host,
                            urllib.parse.urlencode([('forcescheduler', 'Force'),
                                              ('branch', branch),
                                              ('username', 'release'),
                                              ('reason', 'release')]))
            except urllib.error.HTTPError as e:
                print('Failed to force (%s), retrying' % e)
                time.sleep(5)
            else:
                break
        else:
            raise RuntimeError('Could not force build')

        if options.verbose:
            print('Build forced.')

    if options.verbose:
        print('Waiting for completion.')

    while True:
        time.sleep(60)
        status = json.load(urllib.request.urlopen('http://%s:8010/json/builders/Release' % host))
        if status['state'] == 'idle':
            break

    if options.verbose:
        print('Build finished.')
        print('Downloading release.zip')

    buildno = status['cachedBuilds'][-1]
    status = json.load(urllib.request.urlopen('http://%s:8010/json/builders/Release/builds/%d' % (host, buildno)))
    try:
        zipurl = status['steps'][-1]['urls']['Download release']
    except (KeyError, IndexError):
        raise RuntimeError('release.zip URL not found. Build failed.')

    if os.path.exists('dist'):
        shutil.rmtree('dist')
    os.mkdir('dist')

    shutil.copyfileobj(urllib.request.urlopen(zipurl), open(os.path.join('dist', 'release.zip'), 'wb'))

    try:
        zipFile = zipfile.ZipFile(os.path.join('dist', 'release.zip'), 'r')
        try:
            for info in zipFile.infolist():
                if options.verbose:
                    print('Extracting "%s"' % info.filename)
                shutil.copyfileobj(zipFile.open(info, 'r'),
                                   open(os.path.join('dist', info.filename), 'wb'))
        finally:
            zipFile.close()
    finally:
        os.remove(os.path.join('dist', 'release.zip'))


@progress
def uploading_distributions_to_host(settings, options):
    host = settings.get('webhost', 'hostname')
    user = settings.get('webhost', 'username')
    path = settings.get('webhost', 'distpath')
    os.system('rsync dist/ -avP %s@%s:%s' % (user, host, path))


@progress
def uploading_distributions_to_SourceForge(settings, options):
    rsync(settings, options, 'rsync -avP -e ssh dist/* %s')


def uploading_distributions_to_fosshub(settings, options):
    api = FOSSHubAPI(settings.get('fosshub', 'api_key'))
    # Play it safe.
    for project in api.get('projects'):
        if project['name'] == 'Task Coach':
            project_id = project['id']
            break
    else:
        raise RuntimeError('Cannot find Task Coach project on FOSSHub')

    for release in api.get('projects/%s/releases' % project_id):
        if release['version'] == taskcoachlib.meta.data.version:
            print('Version %s already published' % release['version'])
            import pprint
            pprint.pprint(release)
            return

    metadata = taskcoachlib.meta.data.metaDict
    changelog = latest_release(metadata)

    data = {'version': taskcoachlib.meta.data.version, 'changeLog': changelog, 'publish': True, 'files': []}
    for filetmpl, type_ in [
        ('TaskCoach-%s-win32.exe', '32-bit Windows Installer'),
        ('TaskCoach-%s.dmg', 'OS X'),
        ('X-TaskCoach_%s_rev1.zip', 'Portable (WinPenPack Format)'),
        ('TaskCoachPortable_%s.paf.exe', 'Portable (PortableApps Format)'),
        ]:
        filedata = {'fileUrl': '%s%s' % (settings.get('webhost', 'disturl'), filetmpl % taskcoachlib.meta.data.version), 'type': type_, 'version': taskcoachlib.meta.data.version}
        data['files'].append(filedata)
    api.post('projects/%s/releases' % project_id, data)


def uploading_distributions(settings, options):
    uploading_distributions_to_host(settings, options)
    uploading_distributions_to_SourceForge(settings, options)
    uploading_distributions_to_fosshub(settings, options)


@progress
def marking_default_downloads(settings, options):
    defaults = list()
    for name in os.listdir('dist'):
        if name.endswith('.dmg'):
            defaults.append(('mac', name))
        elif name.endswith('-win32.exe'):
            defaults.append(('windows', name))

    for platform, name in defaults:
        if options.dry_run:
            print('Skipping marking "%s" as default for %s' % (name, platform))
        else:
            # httplib does not seem to handle PUT very well
            # See http://stackoverflow.com/questions/111945/is-there-any-way-to-do-http-put-in-python
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler)
            url = 'https://sourceforge.net/projects/taskcoach/files/taskcoach/Release-%s/%s' % (taskcoachlib.meta.version, name)
            req = urllib.request.Request(url,
                                  data=urllib.parse.urlencode(dict(default=platform, api_key=settings.get('sourceforge', 'api_key'))))
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            req.get_method = lambda: 'PUT'
            try:
                opener.open(req)
            except urllib.error.HTTPError as e:
                print('Warning: could not mark "%s" as default download for %s (%s)' % (name, platform, e))
            else:
                if options.verbose:
                    print('Marked "%s" as default download for %s' % (name, platform))


@progress
def marking_bug_fixed(settings, options, *bugIds):
    api = SourceforgeAPI(settings, options)
    for bugId in bugIds:
        api.fix(bugId)


@progress
def marking_bug_released(settings, options, *bugIds):
    api = SourceforgeAPI(settings, options)
    for bugId in bugIds:
        api.release(bugId)


@progress
def downloading_distributions_from_SourceForge(settings, options):
    rsync(settings, options, 'rsync -avP -e ssh %s dist/')


@progress
def generating_MD5_digests(settings, options):
    contents = '''md5digests = {\n'''
    for filename in glob.glob(os.path.join('dist', '*')):
        
        md5digest = hashlib.md5(open(filename, 'rb').read())  # pylint: disable=E1101
        filename = os.path.basename(filename)
        hexdigest = md5digest.hexdigest()
        contents += '''    "%s": "%s",\n''' % (filename, hexdigest)
        if options.verbose:
            print('%40s -> %s' % (filename, hexdigest))
    contents += '}\n'
    
    md5digests_file = open(os.path.join('website.in', 'md5digests.py'), 'w')
    md5digests_file.write(contents)
    md5digests_file.close()


@progress
def generating_website(settings, options):
    os.system('make changes')
    os.chdir('website.in')
    os.system('"%s" make.py' % PYTHONEXE)
    os.chdir('..')


class SimpleFTP(ftplib.FTP):
    def __init__(self, hostname, username, password, folder='.'):
        super().__init__(hostname, username, password)
        self.ensure_folder(folder)
        self.remote_root = folder
            
    def ensure_folder(self, folder):
        try:
            self.cwd(folder)
        except ftplib.error_perm:
            self.mkd(folder)
            self.cwd(folder)    
            
    def put(self, folder, *filename_whitelist):
        for root, subfolders, filenames in os.walk(folder):
            if root != folder:
                print('Change into %s' % root)
                for part in root.split(os.sep):
                    self.cwd(part)
            for subfolder in subfolders:
                print('Create %s' % os.path.join(root, subfolder))
                try:
                    self.mkd(subfolder)
                except ftplib.error_perm as info:
                    print(info)
            for filename in filenames:
                if filename_whitelist and filename not in filename_whitelist:
                    print('Skipping %s' % os.path.join(root, filename))
                    continue
                print('Store %s' % os.path.join(root, filename))
                try:
                    self.storbinary('STOR %s' % filename, 
                                    open(os.path.join(root, filename), 'rb'))
                except ftplib.error_perm as info:
                    if str(info).endswith('Overwrite permission denied'):
                        self.delete(filename)
                        self.storbinary('STOR %s' % filename, 
                                        open(os.path.join(root, filename), 
                                             'rb'))
                    else:
                        raise
            self.cwd(self.remote_root)

    def get(self, filename):
        print('Retrieve %s' % filename)
        self.retrbinary('RETR %s' % filename, open(filename, 'wb').write)


@progress
def registering_with_PyPI(settings, options):
    import setuptools
    if tuple(map(int, setuptools.__version__.split('.'))) < (27, 0):
        raise RuntimeError('Need at least setuptools 27 to upload on PyPi')

    username = settings.get('pypi', 'username')
    password = settings.get('pypi', 'password')
    with open('.pypirc', 'w') as pypirc:
        pypirc.write('[distutils]\n')
        pypirc.write('index-servers =\n')
        pypirc.write('  pypi\n')
        pypirc.write('[pypi]\n')
        pypirc.write('repository=https://upload.pypi.org/legacy/\n')
        pypirc.write('username=%s\n' % username)
        pypirc.write('password=%s\n' % password)
    # pylint: disable=W0404
    from setup import setupOptions
    languages_pypi_does_not_know = ['Basque', 'Belarusian', 'Breton', 
        'Estonian', 'Galician', 'Lithuanian', 'Norwegian (Bokmal)', 
        'Norwegian (Nynorsk)', 'Occitan', 'Papiamento', 'Slovene', 
        'German (Low)', 'Mongolian', 'English (AU)', 'English (CA)',
        'English (GB)', 'English (US)']
    for language in languages_pypi_does_not_know:
        try:
            setupOptions['classifiers'].remove('Natural Language :: %s' % language)
        except ValueError:
            pass
    from distutils.core import setup
    del sys.argv[1:]
    os.environ['HOME'] = '.'
    sys.argv.append('sdist')
    sys.argv.append('upload')
    if options.dry_run:
        print('Skipping PyPI registration.')
    else:
        setup(**setupOptions)  # pylint: disable=W0142
    os.remove('.pypirc')


def status_message():
    ''' Return a brief status message for e.g. Twitter. '''
    metadata = taskcoachlib.meta.data.metaDict
    return "Release %(version)s of %(name)s is available from %(url)s. " \
           "See what's new at %(url)schanges.html." % metadata


def announcing_via_OAuth_Api(settings, options, section, host):
    consumer_key = settings.get(section, 'consumer_key')
    consumer_secret = settings.get(section, 'consumer_secret')
    consumer = oauth.Consumer(key=consumer_key, secret=consumer_secret)
    oauth_token = settings.get(section, 'oauth_token')
    oauth_token_secret = settings.get(section, 'oauth_token_secret')
    token = oauth.Token(key=oauth_token, secret=oauth_token_secret)
    client = oauth.Client(consumer, token)
    status = status_message()
    if options.dry_run:
        print('Skipping announcing "%s" on %s.' % (status, host))
    else:
        response, content = client.request( \
            'https://api.%s/1.1/statuses/update.json' % host, method='POST', 
            body='status=%s' % status, headers=None)
        if response.status != 200:
            print('Request failed: %d %s' % (response.status, response.reason))
            print(content)


@progress
def announcing_on_Twitter(settings, options):
    announcing_via_OAuth_Api(settings, options, 'twitter', 'twitter.com')


def uploading_website(settings, options):
    ''' Upload the website contents to the website(s). '''
    host = settings.get('webhost', 'hostname')
    user = settings.get('webhost', 'username')
    path = settings.get('webhost', 'path')
    os.system('rsync website.out/ -avP %s@%s:%s' % (user, host, path))


def announcing(settings, options):
    #registering_with_PyPI(settings, options)
    announcing_on_Twitter(settings, options)
    mailing_announcement(settings, options)


def updating_Sourceforge_trackers(settings, options):
    sys.path.insert(0, 'changes.in')
    import changes, changetypes

    for release in changes.releases:
        if release.number == taskcoachlib.meta.version:
            break
    else:
        raise RuntimeError('Could not find version "%s" in changelog' % taskcoachlib.meta.version)

    alreadyDone = set()
    for bugFixed in release.bugsFixed:
        if isinstance(bugFixed, changetypes.Bugv2):
            for id_ in bugFixed.changeIds:
                if id_ not in alreadyDone:
                    alreadyDone.add(id_)
                    if options.dry_run:
                        print('Skipping mark bug #%s released' % id_)
                    else:
                        api = SourceforgeAPI(settings, options)
                        api.release(id_)


def releasing(settings, options):
    building_packages(settings, options)
    uploading_distributions(settings, options)
    downloading_distributions_from_SourceForge(settings, options)
    generating_MD5_digests(settings, options)
    generating_website(settings, options)
    uploading_website(settings, options)
    announcing(settings, options)
    updating_Sourceforge_trackers(settings, options)
    tagging_release_in_mercurial(settings, options)
    marking_default_downloads(settings, options)


def latest_release(metadata, summary_only=False):
    sys.path.insert(0, 'changes.in')
    # pylint: disable=F0401
    import changes 
    import converter  
    del sys.path[0]
    greeting = 'release %(version)s of %(name)s.' % metadata
    if summary_only:
        greeting = greeting[0].upper() + greeting[1:] 
    else:
        greeting = "We're happy to announce " + greeting
    text_converter = converter.ReleaseToTextConverter()
    convert = text_converter.summary if summary_only else text_converter.convert
    return convert(changes.releases[0], greeting)


@progress
def mailing_announcement(settings, options):
    metadata = taskcoachlib.meta.data.metaDict
    for sender_info in 'sender_name', 'sender_email_address':
        metadata[sender_info] = settings.get('smtp', sender_info)
    metadata['release'] = latest_release(metadata)
    msg = '''To: %(announcement_addresses)s
BCC: %(bcc_announcement_addresses)s
From: %(sender_name)s <%(sender_email_address)s>
Reply-To: %(author_email)s
Subject: [ANN] Release %(version)s of %(name)s

Hi,

%(release)s

What is %(name)s?

%(name)s is a simple task manager that allows for hierarchical tasks, 
i.e. tasks in tasks. %(name)s is open source (%(license_abbrev)s) and is developed 
using Python and wxPython. You can download %(name)s from:

%(url)s

In addition to the source distribution, packaged distributions are available 
for Windows, Mac OS X, Linux, and BSD.

Note that although we consider %(name)s to be %(release_status)s software,
and we do our best to prevent bugs, it is always wise to back up your task 
file regularly, and especially when upgrading to a new release.

Regards, 

%(author)s
Task Coach development team

''' % metadata

    recipients = metadata['announcement_addresses']
    server = settings.get('smtp', 'hostname')
    port = settings.get('smtp', 'port')
    username = settings.get('smtp', 'username')
    password = settings.get('smtp', 'password')

    session = smtplib.SMTP(server, port)
    if options.verbose:
        session.set_debuglevel(1)
    session.helo()
    session.ehlo()
    if password:
        session.starttls()
        session.esmtp_features["auth"] = "LOGIN"  # Needed for Gmail SMTP.
        session.login(username, password)
    if options.dry_run:
        print('Skipping sending mail.')
        smtpresult = None
    else:
        smtpresult = session.sendmail(username, recipients, msg)

    if smtpresult:
        errstr = ""
        for recip in list(smtpresult.keys()):
            errstr = """Could not deliver mail to: %s 
Server said: %s
%s
%s""" % (recip, smtpresult[recip][0], smtpresult[recip][1], errstr)
        raise smtplib.SMTPException(errstr)


@progress
def tagging_release_in_mercurial(settings, options):
    metadata = taskcoachlib.meta.data.metaDict
    version = metadata['version']
    release_tag = 'Release' + version.replace('.', '_')
    hg_tag = 'hg tag %s' % release_tag
    commit_message = 'Tag for release %s.' % version
    if options.dry_run:
        print('Skipping %s.' % hg_tag)
    else:
        os.system(hg_tag)
        os.system('hg commit -m "%s"' % commit_message)


COMMANDS = dict(release=releasing,
                build=building_packages,
                uploaddist=uploading_distributions_to_host,
                uploadsf=uploading_distributions_to_SourceForge,
                uploadfoss=uploading_distributions_to_fosshub,
                upload=uploading_distributions,
                download=downloading_distributions_from_SourceForge, 
                md5=generating_MD5_digests,
                websitegen=generating_website,
                website=uploading_website,
                twitter=announcing_on_Twitter,
                pypi=registering_with_PyPI, 
                mail=mailing_announcement,
                announce=announcing,
                update=updating_Sourceforge_trackers,
                tag=tagging_release_in_mercurial,
                markdefault=marking_default_downloads,
                markfixed=marking_bug_fixed,
                markreleased=marking_bug_released)

USAGE = 'Usage: %%prog [options] [%s]' % '|'.join(sorted(COMMANDS.keys()))

SETTINGS = Settings()

parser = optparse.OptionParser(usage=USAGE, epilog=HELP_TEXT, 
                               formatter=HelpFormatter())
parser.add_option('-n', '--dry-run', action='store_true', dest='dry_run', 
                  help="don't make permanent changes")
parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
                  help='provide more detailed progress information')
options, args = parser.parse_args()

try:
    if len(args) > 1:
        COMMANDS[args[0]](SETTINGS, options, *args[1:])  # pylint: disable=W0142
    else:
        COMMANDS[args[0]](SETTINGS, options)
except (KeyError, IndexError):
    parser.print_help()
