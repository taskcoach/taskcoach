#!/usr/bin/env python
# -*- encoding: UTF-8 -*-

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

import os, sys, glob, shutil, wx

sys.path.insert(0, "..")
from taskcoachlib import meta
import style

try:
    import md5digests

    md5digests = md5digests.md5digests
except ImportError:
    md5digests = dict()


one_ad = """
                    <div class="well">
                        <p>
                            <script type="text/javascript"><!--
google_ad_client = "ca-pub-2371570118755412";
/* 120x240, gemaakt 10-5-09 */
google_ad_slot = "6528039249";
google_ad_width = 120;
google_ad_height = 240;
//-->
</script>
<script type="text/javascript"
src="https://pagead2.googlesyndication.com/pagead/show_ads.js">
</script>
                        </p>   
                    </div>"""

ads = """
                    <div class="well">
                        <p>
                            <script type="text/javascript"><!--
google_ad_client = "ca-pub-2371570118755412";
/* 120x600 tekstads */
google_ad_slot = "6546906699";
google_ad_width = 120;
google_ad_height = 600;
//-->
</script>
<script type="text/javascript"
src="https://pagead2.googlesyndication.com/pagead/show_ads.js">
</script>
                        </p>   
                    </div>"""

pages = {}
pages["index"] = (
    """          
            <div class="row">
                <div class="span10">
                    <p><img src="images/banner.png" alt="Banner image"></p>
                    <div class="row">
                        <p align=center><a class="btn btn-primary btn-large" href="download.html">Download Task Coach, it's open source!</a></p>
                    </div>
                    <div class="row">
                        <div class="span5">
                            <h3>What is %(name)s?</h3>  
                            <p>%(name)s is a simple open source todo manager to keep track of
                            personal tasks and todo lists. It is designed for composite tasks,
                            and also offers effort tracking, categories, notes and more.</p>
                            <p><a class="btn" href="features.html">Read more &raquo;</a></p>
                            <h3>What platforms are supported?</h3>
                            <p>%(name)s is available for 
                            <a href="download_for_windows.html">Windows</a>,
                            <a href="download_for_mac.html">Mac OS X</a>, <a href="download_for_linux.html">Linux</a>, 
                            <a href="download_for_bsd.html">BSD</a>.</p>
                            <h3>What does it cost?</h3>
                            %(name)s is completely free.
                            <p><a class="btn" href="license.html">Read license &raquo;</a></p>
                        </div>
                        <div class="span5">  
                            <h3>What support is available?</h3>
                            <p>We offer support for free. You can contact us by e-mail, 
                            via our support request tracker, and via our bug tracker.</p>
                            <p><a class="btn" href="getsupport.html">Get support &raquo;</a></p>
                            <h3>How can I help?</h3>
                            <p>Glad you asked! The easiest way is to help spread the word. Improving 
                            a translation is also an easy way to help. Patches are very welcome. 
                            And we'll gladly accept donations.</p>
                            <p><a class="btn" href="givesupport.html">Give support &raquo;</a></p>
                            <h3>Who is behind this?</h3>
                            <p>%(name)s is developed by <a href="mailto:%(author_email)s">%(author_unicode)s</a>, 
                            with help of different people providing <a href="i18n.html">translations</a>. 
                            <p><a href="https://twitter.com/taskcoach" class="twitter-follow-button">Follow Task Coach on Twitter</a>
                            <script src="https://platform.twitter.com/widgets.js" type="text/javascript"></script></p> 
                            <!-- AppStoreHQ:claim_code:258f8973d401112a215d79afdb82fef934ee56c9 -->
                            <!-- AppStoreHQ:developer_claim_code:d28c5a79965194fd06870ec80ab83114356b664d -->
                        </div>
                    </div>
                </div>
                <div class="span2">"""
    + ads
    + """
                </div>
            </div>
        """
)

pages[
    "getsupport"
] = """
            <div class="page-header">
                <h1>Get support</h1>
            </div>
            <div class="row">
             <div class="span4">
                    <h2>Browse FAQ</h2>
                    <p>Browse the frequently asked questions to see whether your 
                    question has been answered before.</p>
                    <p>Please do not ask questions on the mailinglist or submit
                    support requests before you have browsed the FAQ. Thanks!</p>
                    <div class="btn-group">
                        <a class="btn btn-primary" href="%(faq_url)s">Browse FAQ</a>
                        <a class="btn btn-primary dropdown-toggle" data-toggle="dropdown">
                            <span class="caret"></span>
                        </a>
                        <ul class="dropdown-menu">
                            <li><a href="https://answers.launchpad.net/taskcoach/+faq/1724">Why can I not mark this task completed?</a></li>
                            <li><a href="https://answers.launchpad.net/taskcoach/+faq/1448">Can a task file be edited by multiple users?</a></li>
                            <li class="divider"></li>
                            <li><a href="%(faq_url)s">Browse all frequently asked questions</a></li>
                        </ul>
                    </div>
                </div>
                <div class="span4">
                    <h2>Join the mailinglist</h2>
                    <p>A Yahoo!Groups mailing list is available for discussing
                    %(name)s.</p>
                    <p>You can browse the <a
                    href="https://groups.yahoo.com/group/taskcoach/messages">archive
                    of messages</a> without subscribing to the mailing list.</p>
                    <p>The mailing list is also available as  
                    <a href="https://dir.gmane.org/gmane.comp.sysutils.pim.taskcoach">newsgroup</a>
                    on <a href="https://gmane.org">Gmane</a>.</p>
                    <p><a class="btn"
                    href="https://groups.yahoo.com/group/taskcoach/join">Join mailinglist</a></p>
                </div>
                <div class="span4">
                    <h2>User manual</h2>
                    <p>A user manual is under development in a Wiki. Unfortunately,
                    the manual is far from being completed. However, since this is a 
                    community effort, you can help too.</p>
                    <p><a class="btn" 
                          href="https://sourceforge.net/p/taskcoach/wiki/manual/">Browse manual</a></p>
                </div>
            </div>
            <hr>
            <div class="row">
                <div class="span4">
                    <h2>Request support</h2>
                    <p>Submit a support request on Sourceforge. Be sure to 
                    explain your issue with as much detail as you can. Mention 
                    the version of %(name)s you are using, the operating system 
                    you are using and what exactly your issue is.</p>
                    <p><a class="btn" href="%(support_request_url)s" 
                          title="Request support from the developers">Request support</a></p>
                </div>
                <div class="span4">
                    <h2>Report a bug</h2>
                    <p>Submit a bug report on Sourceforge. Be sure to explain 
                    the bug with as much detail as you can. Mention the 
                    version of %(name)s you are using, the operating system 
                    you are using and how to trigger the bug.
                    <p><a class="btn" href="%(known_bugs_url)s" 
                          title="Browse known bugs and report new bugs">Report a bug</a></p>
                </div>
                <div class="span4">
                    <h2>Request a feature</h2>
                    <p>Submit a request for a new feature on UserVoice or vote on
                    existing feature requests. Please note that we have many open
                    feature requests and we can't make any promises on when new 
                    features are delivered.</p>
                    <p><a class="btn" href="%(feature_request_url)s" 
                          title="Browse requested features, vote for your favorite features and request new features">Request a feature</a></p>
                </div>
            </div>"""

pages[
    "givesupport"
] = """
            <div class="page-header">
                <h1>Give support</h1>
            </div>
           <div class="row">
                <div class="span4">
                    <h2>Help translate</h2>
                    <p>If you speak a language different than English, you can help 
                    translate the user interface of %(name)s in your language. 
                    Even if you have limited time available you can help by
                    translating a few strings.</p>
                    <p><a class="btn" href="i18n.html">Help translate</a></p>
                </div>
                <div class="span4">
                    <h2>Help write the manual</h2>
                    <p>A user manual is under development in a Wiki. Unfortunately,
                    the manual is far from being completed. However, since this is a 
                    community effort, you can help too.</p>
                    <p><a class="btn" 
                          href="https://snowdrift.coop/p/taskcoach/w/en/main">Browse manual</a></p>
                </div>
                <div class="span4">
                    <h2>Help develop</h2>
                    <p>If you know how to program, you can learn 
                    <a href="https://www.python.org">Python</a>. If you know Python,
                    you can help develop! And we are looking for developers, so
                    don't hesitate to jump in.</p>  
                    <p><a class="btn" href="devinfo.html">Developer info</a></p>
                </div>
            </div>
            <hr>
            <div class="row">
                <div class="span4">
                    <h2>Donate</h2>
                    <p>Donations for the development of %(name)s are very much 
                    appreciated. Please donate what you feel %(name)s is worth 
                    to you, but any amount is fine.</p>
                    <p>
                        <form action="https://www.paypal.com/cgi-bin/webscr" method="post">
                            <input type="hidden" name="cmd" value="_s-xclick">
                            <input type="hidden" name="hosted_button_id" value="FA3B7MEK8MXZG">
                            <input type="image" src="https://www.paypalobjects.com/en_US/NL/i/btn/btn_donateCC_LG.gif" border="0" name="submit" alt="PayPal - The safer, easier way to pay online!">
                            <img alt="" border="0" src="https://www.paypalobjects.com/en_US/i/scr/pixel.gif" width="1" height="1">
                        </form>
                    </p>
                </div>
                <div class="span4">
                    <h2>Flattr us</h2>
                    <p><a href="https://flattr.com">Flattr</a> is a mechanism for
                    making social micropayments. In plain English, you can donate
                    us (and other people that create stuff you like for free) 
                    a small amount of money really easy.</p>
                    <p>
                        <a class="FlattrButton" style="display:none;" href="https://taskcoach.org"></a>
                        <noscript>
                            <a href="https://flattr.com/thing/181658/Task-Coach-Your-friendly-task-manager" target="_blank">
                                <img src="https://api.flattr.com/button/flattr-badge-large.png" alt="Flattr this" title="Flattr this" border="0" />
                            </a>
                        </noscript>
                    </p>
                </div>
                <div class="span4">
                    <h2>Spread the word</h2>
                    <p>Help us spread the word. Talk about %(name)s with your
                    family, friends and colleagues. Tweet about %(name)s, +1 us,
                    you know the drill.</p>
                    <p><a href="https://twitter.com/share" class="twitter-share-button" data-url="https://taskcoach.org" data-text="Check out Task Coach: a free and open source todo app for Windows, Mac, and Linux." data-count="horizontal" data-via="taskcoach">Tweet</a><script type="text/javascript" src="https://platform.twitter.com/widgets.js"></script></p>
                    <p><iframe src="https://www.facebook.com/plugins/like.php?href=http%%3A%%2F%%2Ftaskcoach.org&amp;layout=button_count&amp;show_faces=true&amp;width=190&amp;action=like&amp;colorscheme=light&amp;height=21" 
                            scrolling="no" frameborder="0" 
                            style="border:none; overflow:hidden; width:190px; height:21px;" 
                            allowTransparency="true">
                    </iframe></p>
                    <p><g:plusone size="medium"></g:plusone></p>
                </div>
            </div>"""


pages["changes"] = (
    """
            <div class="page-header">
                <h1>Change history <small>Recent releases</small></h1>
            </div>
            <div class="row">
                <div class="span10">"""
    + open("changes.html").read().decode("UTF-8")
    + """
                    <p><a class="btn" href="all_changes.html">View complete change history &raquo;</a></p>
                </div>
                <div class="span2">"""
    + ads
    + """
                </div>
            </div>"""
)

pages["all_changes"] = (
    """
            <div class="page-header">
                <h1>Change history <small>All releases</small></h1>
            </div>
            <div class="row">
                <div class="span10">"""
    + open("all_changes.html").read().decode("UTF-8")
    + """
                </div>
                <div class="span2">"""
    + ads
    + """
                </div>
            </div>"""
)

prerequisites = """
              <a href="https://www.python.org/download/">Python</a> 
              <strong>%(pythonversion)s</strong> and 
              <a href="https://www.wxpython.org/download.php">wxPython</a>
              <strong>%(wxpythonversion)s</strong> (or newer)"""

prerequisites26 = prerequisites % dict(
    pythonversion="2.6", wxpythonversion="%(wxpythonversion)s"
)

prerequisites27 = prerequisites % dict(
    pythonversion="2.7", wxpythonversion="%(wxpythonversion)s"
)


def download_header(platform=None, release=None, warning=None):
    title = "Download %(name)s"
    if release:
        title += " release %s" % release
    if platform:
        title += " for %s" % platform
    if not warning:
        warning = """%(name)s is actively developed. New features are added
          on a regular basis. This means that %(name)s contains bugs. We do 
          our best to prevent bugs and fix them as soon as possible. Still, 
          we <strong>strongly</strong> advise you to make backups of your 
          work on a regular basis, and especially before upgrading."""
    return """        
            <div class="page-header">
                <h1>%s</h1>
            </div>
            <div class="row">
                <div class="span10">
                    <p>
                        <span class="label label-warning">Warning</span> %s
                    </p>""" % (
        title,
        warning,
    )


def download_footer(ads=ads):
    return (
        """
                </div>
                <div class="span2">"""
        + ads
        + """
                </div>
            </div>"""
    )


def download_table(**kwargs):
    filename = (
        list(kwargs["download_urls"].values())[0].split("/")[-1]
        % meta.metaDict
    )
    md5 = md5digests.get(filename, "")
    kwargs["rows"] = 5 if md5 else 4
    kwargs["md5"] = (
        "\n            <dt>MD5 digest</dt><dd>%s.</dd>" % md5 if md5 else ""
    )
    # Deal with platforms that are not a name but 'all platforms':
    if "prerequisites" not in kwargs:
        kwargs["prerequisites"] = "None"
    if "action" not in kwargs:
        kwargs["action"] = "Download"
    if "platform" in kwargs:
        download_url_template = '%(action)s <a href="%(url)s">%(package_type)s</a> for %(platform)s from %(source)s'
        platform = kwargs["platform"]
        kwargs["platform_versions"] = (
            "Platforms"
            if platform == "all platforms"
            else platform + " versions"
        )
    else:
        download_url_template = (
            '%(action)s <a href="%(url)s">%(package_type)s</a> from %(source)s'
        )
        kwargs["platform_versions"] = "Platforms"
    urls = []
    for source, url in list(kwargs["download_urls"].items()):
        parameters = kwargs.copy()
        parameters["url"] = url
        parameters["source"] = source
        urls.append((source, download_url_template % parameters))
    urls.sort()
    urls = [url[1] for url in urls]
    kwargs["download_urls"] = "<br>\n".join(urls)
    return (
        """        <p>
          <table width="100%%%%" class="table table-striped">
            <tbody>
            <tr>
              <td rowspan=%(rows)s valign=top width=130>
                <img src="images/%(image)s.png" alt="%(image)s">
              </td>
              <td>
                <h3>
                  %(download_urls)s
                </h3>
              </td>
            </tr>
            <tr><td><dl>
            <dt>%(platform_versions)s supported</dt><dd>%(platform_versions_supported)s.</dd>
            <dt>Prerequisites</dt><dd>%(prerequisites)s.</dd>
            <dt>Installation</dt><dd>%(installation)s.</dd>%(md5)s</dl></td></tr>
            </tbody>
          </table>
        </p>"""
        % kwargs
    )


windowsOptions = dict(
    platform_lower="windows",
    platform_versions_supported="Windows 2000, XP, Vista, Windows 7, Windows 8",
)

bestsoft_url = "https://www.fosshub.com/Task-Coach.html"

windowsInstaller = download_table(
    image="windows",
    download_urls=dict(
        Sourceforge="%(dist_download_prefix)s/%(filename)s-%(version)s-win32.exe",
        FossHub=bestsoft_url,
    ),
    package_type="%(name)s Installer",
    installation="Run the installer; it will guide you through the installation process",
    **windowsOptions
)

windowsPortableApp = download_table(
    image="portableApps",
    download_urls=dict(
        Sourceforge="%(dist_download_prefix)s/%(filename)sPortable_%(version)s.paf.exe",
        FossHub=bestsoft_url,
    ),
    package_type="%(name)s in PortableApps Format",
    installation="Run the installer; it will guide you through the installation process",
    **windowsOptions
)

windowsPenPack = download_table(
    image="winPenPack",
    download_urls=dict(
        Sourceforge="%(dist_download_prefix)s/X-%(filename)s_%(version)s_rev1.zip",
        FossHub=bestsoft_url,
    ),
    package_type="%(name)s in winPenPack Format",
    installation="Unzip the archive contents in the location where you want %(name)s to be installed",
    **windowsOptions
)

sep = "\n"

pages["download_for_windows"] = sep.join(
    [
        download_header(platform="Microsoft Windows", release="%(version)s"),
        windowsInstaller,
        windowsPortableApp,
        windowsPenPack,
        download_footer(),
    ]
)


macDMG = download_table(
    image="mac",
    download_urls=dict(
        Sourceforge="%(dist_download_prefix)s/%(filename)s-%(version)s.dmg"
    ),
    package_type="Disk image (dmg)",
    platform_lower="macosx",
    platform_versions_supported="Mac OS X Leopard/10.5 (Universal) and newer",
    installation="Double click the package and drop the %(name)s application in your Applications folder",
)

pages["download_for_mac"] = sep.join(
    [
        download_header(platform="Mac OS X", release="%(version)s"),
        macDMG,
        download_footer(one_ad),
    ]
)


debian = download_table(
    image="debian",
    download_urls=dict(
        Sourceforge="%(dist_download_prefix)s/%(filename_lower)s_%(version)s-1.deb"
    ),
    package_type="Debian package (deb)",
    platform="Debian",
    platform_lower="debian",
    platform_versions_supported='Debian GNU/Linux 6.0 ("squeeze") and newer',
    prerequisites=prerequisites26
    + """. If your Debian 
              installation does not have the minimally required wxPython version 
              you will need to install it yourself following 
              <a href="https://wiki.wxpython.org/InstallingOnUbuntuOrDebian">these 
              instructions</a>""",
    installation="Double click the package to start the installer",
)


ubuntu_ppa = download_table(
    image="ubuntu",
    download_urls=dict(
        Launchpad="https://launchpad.net/~taskcoach-developers/+archive/ppa"
    ),
    package_type="PPA",
    platform="Ubuntu",
    platform_lower="ubuntu",
    platform_versions_supported='Ubuntu 10.04 LTS ("Lucid Lynx") and newer',
    prerequisites=prerequisites27,
    installation="""Add ppa:taskcoach-developers/ppa to your Software Sources.""",
)


ubuntu = download_table(
    image="ubuntu",
    download_urls=dict(
        Sourceforge="%(dist_download_prefix)s/%(filename_lower)s_%(version)s-1.deb"
    ),
    package_type="Debian package (deb)",
    platform="Ubuntu",
    platform_lower="ubuntu",
    platform_versions_supported='Ubuntu 10.04 LTS ("Lucid Lynx") and newer',
    prerequisites=prerequisites26,
    installation="""Double click the package to start the 
installer. You can also use the PPA (<a href="https://answers.launchpad.net/taskcoach/+faq/1615">see the FAQ</a>)""",
)

gentoo = download_table(
    image="gentoo",
    action="Install",
    download_urls={
        "Gentoo.org": "https://packages.gentoo.org/package/app-office/taskcoach"
    },
    package_type="Ebuild",
    platform="Gentoo",
    platform_lower="gentoo",
    platform_versions_supported="Gentoo 2008.0 and newer",
    prerequisites=prerequisites,
    installation="%(name)s is included in Gentoo Portage. Install with emerge: <tt>$ emerge taskcoach</tt>",
)

opensuse = download_table(
    image="opensuse",
    download_urls=dict(
        Sourceforge="%(dist_download_prefix)s/%(filename_lower)s-%(version)s-1.opensuse.i386.rpm"
    ),
    package_type="RPM package",
    platform="OpenSuse",
    platform_lower="opensuse",
    platform_versions_supported="OpenSuse 11.4 and newer",
    prerequisites=prerequisites,
    installation='Double click the package to start the installer. Alternatively, you can find RPMs for various Suse versions on <a href="https://software.opensuse.org/package/TaskCoach">software.opensuse.org</a>.',
)

fedora14 = download_table(
    image="fedora",
    download_urls=dict(
        Sourceforge="%(dist_download_prefix)s/%(filename_lower)s-%(version)s-1.fc14.noarch.rpm"
    ),
    package_type="RPM package",
    platform="Fedora",
    platform_lower="fedora",
    platform_versions_supported="Fedora 14 and newer",
    prerequisites=prerequisites27,
    installation="<code>sudo yum install --nogpgcheck %(filename_lower)s-%(version)s-1.fc*.noarch.rpm</code>",
)

archlinux = download_table(
    image="archlinux",
    action="Install",
    download_urls={
        "ArchLinux.org": "https://aur.archlinux.org/packages/taskcoach"
    },
    package_type="ArchLinux package",
    platform="Arch",
    platform_lower="arch",
    platform_versions_supported="Not applicable (Arch uses a rolling release)",
    prerequisites=prerequisites26,
    installation="""%(name)s is included in the Arch 
User Repository. See the 
<a href="https://wiki.archlinux.org/index.php/AUR_User_Guidelines">AUR user 
guidelines</a>""",
)

redhat_el4and5 = download_table(
    image="redhat",
    download_urls=dict(
        Sourceforge="%(dist_download_prefix)s/%(filename)s-%(version)s.tar.gz"
    ),
    package_type="Source tar archive",
    platform="Red Hat Enterprise Linux",
    platform_lower="redhat",
    platform_versions_supported="Red Hat Enterprise Linux 4 and 5",
    prerequisites=prerequisites,
    installation="""Follow the instructions on
<a href='https://warped.org/blog/2010/04/02/ch0wned-installing-taskcoach-and-all-its-depenencies-in-home-for-el4/'>
Max Baker's blog</a>""",
)

linux = download_table(
    image="linux",
    download_urls=dict(
        Sourceforge="%(dist_download_prefix)s/%(filename)s-%(version)s-1.noarch.rpm"
    ),
    package_type="RPM package",
    platform="Linux",
    platform_lower="rpm",
    platform_versions_supported="All Linux versions that support RPM and the prerequisites",
    prerequisites=prerequisites,
    installation="Use your package manager to install the package",
)

pages["download_for_linux"] = sep.join(
    [
        download_header(platform="Linux", release="%(version)s"),
        ubuntu_ppa,
        ubuntu,
        debian,
        fedora14,
        gentoo,
        opensuse,
        redhat_el4and5,
        archlinux,
        linux,
        download_footer(),
    ]
)


freeBSD = download_table(
    image="freebsd",
    action="Install",
    download_urls={
        "FreeBSD.org": "https://www.freebsd.org/cgi/cvsweb.cgi/ports/deskutils/taskcoach/"
    },
    package_type="%(name)s Port",
    platform="FreeBSD",
    platform_lower="freebsd",
    platform_versions_supported="FreeBSD 8.2 and newer",
    installation="Update your ports collection and then run: <code>cd /usr/ports/deskutils/taskcoach &amp;&amp; make install clean</code>",
)

pages["download_for_bsd"] = sep.join(
    [
        download_header(platform="FreeBSD", release="%(version)s"),
        freeBSD,
        download_footer(one_ad),
    ]
)


sourceOptions = dict(
    image="source",
    prerequisites=prerequisites,
    installation="""Decompress the archive and run <code>python 
              setup.py install</code>. If you have a previous version of %(name)s 
              installed, you may need to force old files to be overwritten: 
              <code>python setup.py install --force</code>""",
)

source_rpm = download_table(
    download_urls=dict(
        Sourceforge="%(dist_download_prefix)s/%(filename)s-%(version)s-1.src.rpm"
    ),
    package_type="Source RPM package",
    platform="Linux",
    platform_lower="source_rpm",
    platform_versions_supported="All Linux platforms that support RPM and the prerequisites",
    **sourceOptions
)

source_tgz = download_table(
    download_urls=dict(
        Sourceforge="%(dist_download_prefix)s/%(filename)s-%(version)s.tar.gz"
    ),
    package_type="Source tar archive",
    platform="Linux",
    platform_lower="source_gz",
    platform_versions_supported="All Linux platforms that support the prerequisites",
    **sourceOptions
)

source_raw = download_table(
    download_urls=dict(
        Sourceforge="%(dist_download_prefix)s/%(filename)s-%(version)s-raw.tar.gz"
    ),
    package_type="Raw source tar archive",
    platform="Linux",
    platform_lower="source_raw",
    platform_versions_supported="All Linux platforms that support the prerequisites",
    image="source",
    prerequisites=prerequisites + ", GNU make and patch",
    installation="""Decompress the archive, run <code>make prepare</code> and then
               <code>python setup.py install</code>. If you have a previous version of %(name)s 
               installed, you may need to force old files to be overwritten: 
               <code>python setup.py install --force</code>""",
)

source_zip = download_table(
    download_urls=dict(
        Sourceforge="%(dist_download_prefix)s/%(filename)s-%(version)s.zip"
    ),
    package_type="Source zip archive",
    platform="Windows",
    platform_lower="source_zip",
    platform_versions_supported="All Windows platforms that support the prerequisites",
    **sourceOptions
)

mercurial = download_table(
    image="sources",
    download_urls=dict(
        Sourceforge="https://sourceforge.net/projects/taskcoach/develop"
    ),
    package_type="Sources from Mercurial",
    platform="all platforms",
    platform_lower="mercurial",
    platform_versions_supported="All platforms that support the prerequisites",
    prerequisites=prerequisites,
    installation="""Run <code>make prepare</code> to generate 
              the icons and language files and then <code>python taskcoach.py</code> 
              to start the application""",
)


pages["download_sources"] = sep.join(
    [
        download_header(release="%(version)s"),
        source_rpm,
        source_zip,
        source_tgz,
        source_raw,
        mercurial,
        download_footer(),
    ]
)


buildbotOptions = dict(
    platform="all platforms",
    platform_versions_supported="See the different download sections",
    prerequisites="See the different download sections",
    installation="See the different download sections",
)

latest_bugfixes = download_table(
    image="bug",
    download_urls=dict(
        Buildbot="http://jeromelaheurte.net/TaskCoach-packages/latest_bugfixes.py"
    ),
    package_type="Latest bugfixes",
    platform_lower="latest_bugfixes",
    **buildbotOptions
)

latest_features = download_table(
    image="latest_features",
    download_urls=dict(
        Buildbot="http://jeromelaheurte.net/TaskCoach-packages/latest_features.py"
    ),
    package_type="Latest features",
    platform_lower="latest_features",
    **buildbotOptions
)

warning = """          These packages are automatically generated by our <a
        href="http://jeromelaheurte.net:8010/waterfall">buildbot</a> each
        time a change is checked in the source tree. This is bleeding
        edge, use at your own risk."""

pages["download_daily_build"] = sep.join(
    [
        download_header(warning=warning),
        latest_bugfixes,
        latest_features,
        download_footer(one_ad),
    ]
)

old_releases = download_table(
    image="archive",
    download_urls=dict(
        Sourceforge="https://sourceforge.net/projects/taskcoach/files/taskcoach/"
    ),
    package_type="Old releases",
    platform="all platforms",
    platform_lower="old_releases",
    platform_versions_supported="See the different download sections",
    prerequisites="See the different download sections",
    installation="See the different download sections",
)

pages["download_old_releases"] = sep.join(
    [download_header(), old_releases, download_footer(one_ad)]
)


pages["download"] = (
    """ 
            <div class="page-header">
                <h1>Download %(name)s</h1>
            </div>
            <div class="row">
                <div class="span10">
                    <table width="100%%">
                        <tbody>
                            <tr>
                                <td style="border-top: 0px;">
                                    <h3>Windows</h3>
                                    <a href="download_for_windows.html"><img alt="Windows" src="images/windows.png"></a>
                                </td>
                                <td style="border-top: 0px;">
                                    <h3>Mac OS X</h3>
                                    <a href="download_for_mac.html"><img alt="Mac OS X" src="images/mac.png"></a>
                                </td>
                                <td style="border-top: 0px;">
                                    <h3>Linux</h3>
                                    <a href="download_for_linux.html"><img alt="Linux" src="images/linux.png"></a>
                                </td>
                                <td style="border-top: 0px;">
                                    <h3>BSD</h3>
                                    <a href="download_for_bsd.html"><img alt="BSD" src="images/freebsd.png"></a>
                                </td>
                            </tr>
                            <tr>
                                <td>
                                    <h3>Sources</h3>
                                    <a href="download_sources.html"><img alt="Sources" src="images/sources.png"></a>
                                </td>
                                <td>
                                    <h3>Daily builds</h3>
                                    <a href="download_daily_build.html"><img alt="Daily build" src="images/latest_features.png"></a>
                                </td>
                                <td>
                                    <h3>Old releases</h3>
                                    <a href="download_old_releases.html"><img alt="Old releases" src="images/archive.png"></a>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="span2">"""
    + one_ad
    + """
                </div>
            </div>"""
)


pages["features"] = (
    """        
            <div class="page-header">
                <h1>Features</h1>
            </div>
            <div class="row">
                <div class="span10">
                    <h2>%(name)s for the desktop</h2>
                    <p>The desktop version of %(name)s (Windows, Mac, Linux, BSD)
                    has the following features:</p>
                    <ul>
                        <li>Creating, editing, and deleting tasks and subtasks.</li>
                        <li>Tasks have a subject, description, priority, start date, 
                        due date, a completion date and an optional reminder. Tasks can
                        recur on a daily, weekly or monthly basis.</li>
                        <li>Tasks can be viewed as a list or as a tree.</li>
                        <li>Tasks can be sorted by all task attributes, e.g. subject,
                        budget, budget left, due date, etc.</li>
                        <li>Several filters to e.g. hide completed tasks or view
                        only tasks that are due today.</li>
                        <li>Tasks can be created by dragging an e-mail message from 
                        a mail user agent (Outlook, Thunderbird, Claws Mail, Apple Mail)
                        onto a task viewer.</li>
                        <li>Attachments can be added to tasks, notes, and categories by 
                        dragging and dropping files, e-mail messages, or URL's onto a 
                        task, note or category.</li>
                        <li>Task status depends on its subtask and vice versa. E.g. if 
                        you mark the last uncompleted subtask as completed, the parent 
                        task is automatically marked as completed too.</li>
                        <li>Tasks and notes can be assigned to user-defined categories.</li>
                        <li>Settings are persistent and saved automatically. The
                        last opened file is loaded automatically when starting
                        %(name)s.</li>
                        <li>Tracking time spent on tasks. Tasks can have a budget. 
                        Time spent can be viewed by individual effort period, by day, 
                        by week, and by month.</li>
                        <li>The %(name)s file format (.tsk) is XML.</li>
                        <li>Tasks, notes, effort, and categories can be exported to HTML
                        and CSV (comma separated format). Effort can be exported to 
                        iCalendar/ICS format as well.</li>
                        <li>Tasks, effort, notes, and categories can be printed. When printing, 
                        %(name)s prints the information that is visible in the current
                        view, including any filters and sort order.</li>
                        <li>%(name)s can be run from a removable medium.</li>
                    </ul>
                </div>
                <div class="span2">"""
    + ads
    + """
                </div>
            </div>"""
)


def thumbnails(indent):
    systems = reversed(
        [
            path
            for path in os.listdir("screenshots")
            if os.path.isdir(os.path.join("screenshots", path))
            and not path.startswith(".")
        ]
    )
    thumbnails = ""
    for system in systems:
        images = []

        for filename in list(
            reversed(glob.glob(os.path.join("screenshots", system, "*.png")))
        ):
            basename = os.path.basename(filename)
            thumbnailFilename = os.path.join(
                "screenshots", system, "Thumb-%s" % basename
            )
            release, platform, description = basename.split("-")
            platform = platform.replace("_", " ")
            description = description[: -len(".png")].replace("_", " ")
            caption = "%s (release %s on %s)" % (
                description,
                release,
                platform,
            )
            images.append(
                (caption, thumbnailFilename, filename.replace("\\", "/"))
            )

        if not images:
            continue

        thumbnails += " " * indent + "<h2>%s</h2>\n" % system
        thumbnails += " " * indent + '<ul class="thumbnails">\n'
        for caption, thumbnailFilename, filename in images:
            thumbnails += " " * (
                indent + 4
            ) + '<li><a class="lightbox" title="%s" href="%s"><img src="%s" alt="%s"/></a></li>\n' % (
                caption,
                filename.replace("\\", "/"),
                thumbnailFilename.replace("\\", "/"),
                caption,
            )
        thumbnails += " " * indent + "</ul>"
    return thumbnails


pages["screenshots"] = (
    """
            <div class="page-header">
                <h1>Screenshots <small>Click thumbnails to see full size screenshots</small></h1>
            </div>
            <div class="row">
                <div class="span10">
"""
    + thumbnails(indent=20)
    + """
                </div>
                <div class="span2">"""
    + ads
    + """
                </div>
            </div>"""
)

pages["license"] = (
    """
            <div class="page-header">
                <h1>License</h1>
            </div>
            <div class="row">
                <div class="span10">"""
    + meta.licenseHTML
    + """
                </div>
                <div class="span2">"""
    + ads
    + """
                </div>
            </div>"""
)


def languages(nr_columns=9):
    link = '<a href="https://translations.launchpad.net/taskcoach/1.4/+pots/i18n.in/%s/+details">%s</a>'
    languages = sorted(meta.languages.keys())
    languages = [
        link % (meta.languages[language][0], language)
        for language in languages
        if meta.languages[language][0] is not None
    ]
    while len(languages) % nr_columns:
        languages.append("")
    nr_of_rows = len(languages) / nr_columns
    rows = []
    for row_index in range(nr_of_rows):
        rows.append(
            languages[row_index * nr_columns : (row_index + 1) * nr_columns]
        )
    return "</tr><tr>".join(
        [("<td>%s</td>" * nr_columns) % tuple(row) for row in rows]
    )


pages["i18n"] = (
    """
            <div class="page-header">
                <h1>Internationalization</h1>
            </div>
            <div class="row">
                <div class="span10">
                    <h2>Information for users</h2>
                    <p>You can select languages via 'Edit' -> 'Preferences'. 
                    Click the 'Language' icon, select the language of your 
                    choice and restart %(name)s.</p>
                    <p>Currently, %(name)s is available in these languages 
                    (though some translations are incomplete):</p>
                    <table class="table table-bordered">
                        <tbody>
                            <tr>
"""
    + languages()
    + """
                            </tr>
                        </tbody>
                    </table>
                    <h2>Instructions for translators</h2>
                    <p>We would welcome translations in additional languages.
                    Please be aware that, next to providing the initial translation,
                    you will be expected to keep your translation up to date as new
                    versions of %(name)s are released.</p>
                    <p>A Yahoo!Groups mailing list is available for discussing the 
                    development and translation of %(name)s. You can join by 
                    sending mail to <tt><a href="mailto:taskcoach-dev-subscribe@yahoogroups.com">taskcoach-dev-subscribe@yahoogroups.com</a></tt>
                    or alternatively, if you have a Yahoo id (or don't mind creating one), 
                    join via the <a href="https://groups.yahoo.com/group/taskcoach-dev/join">webinterface</a>.</p>

                    <p>To create a new translation or update an existing translation, 
                    please follow these steps and guidelines:
                    <ol>
                        <li>Register at <a href="https://launchpad.net">Launchpad</a> and
                        don't forget to set your preferred languages, i.e. the language(s)
                        you want to translate to.</li>
                        <li>Learn more about <a href="https://translations.launchpad.net/+about">translation 
                        support by Launchpad</a>.</li>
                        <li>Go to <a href="https://launchpad.net/taskcoach">%(name)s at 
                        Launchpad</a> and click "Help translate".</li>
                        <li>Start contributing to an existing translation or create a new
                        one.</li>
                        <li><span class="label label-info">Note</span> Please make sure you 
                        understand how <a href="https://docs.python.org/lib/typesseq-strings.html">Python
                        string formatting</a> works since %(name)s uses both the regular
                        <code>%%s</code> type of string formatting as well as the 
                        mapping key form <code>%%(mapping_key)s</code> (note the trailing <code>s</code>; 
                        it shouldn't be removed). If string formatting is used in the English
                        version of a string, the same formatting should occur in the 
                        translated string. In addition, formatting of the form <code>%%s</code> 
                        needs to be in the same order in the translated string as it is 
                        in the English version. Formatting in the form <code>%%(mapping_key)s</code>
                        can be ordered differently in the translated string than in the 
                        English version.</li>
                        <li><span class="label label-warning">Warning</span> Don't translate 
                        the string formatting keys: e.g. when you see
                        <code>%%(name)s</code>, don't translate the word <code>name</code>.</li>
                        <li>Don't translate keyboard shortcuts: e.g. when you see 
                        <code>Shift+Ctrl+V</code>, don't translate the words <code>Shift</code>
                        and <code>Ctrl</code>, even if your keyboard uses 
                        different labels for those keys. Picking a different letter is 
                        possible, but please make sure each letter is used only once.</li>
                        <li>To test your translation, download it as .po file from 
                        Launchpad and start %(name)s with the <code>--po &lt;po file&gt;</code> 
                        command line option.</li> 
                    </ol>
                </div>
                <div class="span2">"""
    + ads
    + """
                </div>
            </div>"""
)


pages["devinfo"] = (
    """
            <div class="page-header">
                <h1>Information for developers</h1>
            </div>
            <div class="row">
                <div class="span10">
                    <p>Here's some information for developers that either want to hack
                    on %(name)s or reuse code.</p>
            
                    <h2>Project hosting</h2>
                    <p>%(name)s source code, file downloads and bug/patch/support trackers are hosted at 
                    <a href="https://sourceforge.net/projects/taskcoach/" 
                    title="%(name)s @ Sourceforge">Sourceforge</a>. Translations are hosted
                    at <a href="https://launchpad.net/taskcoach/"
                    title="%(name)s @Launchpad">Launchpad</a>. Feature requests are hosted at
                    <a href="https://taskcoach.uservoice.com/">Uservoice</a>.
                    </p>
            
                    <h2>Mailing list</h2>
                    <p>A Yahoo!Groups mailing list is available for discussing the development
                    of %(name)s. You can join by sending mail to <tt><a 
                    href="mailto:taskcoach-dev-subscribe@yahoogroups.com">taskcoach-dev-subscribe@yahoogroups.com</a></tt>
                    or alternatively, if you have a Yahoo id (or don't mind creating one), 
                    join via the <a href="https://groups.yahoo.com/group/taskcoach-dev/join">webinterface</a>.</p>
                    <p>You can browse the <a href="https://groups.yahoo.com/group/taskcoach-dev/messages">archive
                    of messages</a> without subscribing to the mailing list.</p>
                    <p>The mailing list is also available as the newsgroup 
                    <a href="https://dir.gmane.org/gmane.comp.sysutils.pim.taskcoach.devel">gmane.comp.sysutils.pim.taskcoach.devel</a>
                    on <a href="https://gmane.org">Gmane</a>.</p>
                    <p>A Sourceforge mailing list is available for receiving commit messages.
                    If you are a %(name)s developer you can <a href="https://lists.sourceforge.net/lists/listinfo/taskcoach-commits">join 
                    this mailing list</a>.
            
                    <h2>Dependencies</h2>
                    <p>%(name)s is developed in <a href="https://www.python.org">Python</a>,
                    using <a href="https://www.wxpython.org">wxPython</A> for the
                    graphical user interface and <a href="https://twistedmatrix.com/">Twisted</a>. On Windows, 
                    <a href="https://sourceforge.net/projects/pywin32/">Pywin32</a> 
                    is used as well. For generating the API documentation you need to have
                    <a href="https://epydoc.sourceforge.net/">Epydoc</a> installed. For
                    generating inheritance diagrams you need to have <a
                    href="https://www.graphviz.org">Graphviz</a> installed.</p>
                    <p>The few other libraries (other than those
                    provided by Python, wxPython and Pywin32) that are used are put into the
                    taskcoachlib/thirdparty package and included in the source code
                    repository.</p>
                    
                    <h2>Development environment</h2>
                    <p>
                    You are free to use whatever IDE you want. To make use of the Makefile you
                    need to have <tt>make</tt> installed. It is installed on Linux and Mac OS X 
                    by default. On Windows we recommend you to install
                    <a href="https://www.cygwin.com">Cygwin</a> 
                    which provides a shell (bash) and a whole range of useful utilities. 
                    Make sure to explicitly include <tt>make</tt> in the Cygwin setup program 
                    because the standard install doesn't contain <tt>make</tt>.</p>
                    
                    <h2>Getting the source</h2>
                    <p>%(name)s source code is hosted in a <a
                    href="https://hg.code.sf.net/p/taskcoach/repo taskcoach-repo">Mercurial repository 
                    at SourceForge</a>. You can check out the code from the repository 
                    directly or <a href="https://sourceforge.net/p/taskcoach/repo/ci/default/tree/">browse the
                    repository</A>. Please read the file <tt>HACKING.txt</tt> after checking
                    out the sources. You can generate documentation with Epydoc and Graphviz
                    from the Makefile: <code>make dot epydoc</code>.</p>
                    
                    <h2>Tests</h2>
                    <p>Tests can be run from the Makefile. There are targets for
                    <tt>unittests</tt>, <tt>integrationtests</tt>,
                    <tt>releasetests</tt>, and <tt>alltests</tt>. These targets all
                    invoke the tests/test.py script. Run <code>tests/test.py --help</code> for 
                    many more test options (including profiling, timing, measuring test 
                    coverage, etc.).</p>
                    
                    <h2>Building the distributions</h2>
                    <p>The Makefile is used to build the different distributions of
                    %(name)s. Currently, a Windows installer is built, a Mac OS X dmg
                    file, RPM and Debian packages are created and the sources are packaged 
                    as compressed archives (.zip and .tar.gz). The Makefile contains targets 
                    for each of the distributions. Most of the code for the actual building 
                    of the distributions, using the python distutils package, is located in 
                    make.py. In turn, make.py imports setup.py. These two files were
                    split so that setup.py only contains distutils information related
                    to <i>installing</i>, while make.py contains all information related
                    to <i>building</i> the distributions. Only setup.py is included in
                    the source distributions.</p>
                    <h5>Windows</h5>
                    <p>On Windows, py2exe is used to bundle the application with the python
                    interpreter and wxPython libraries. Innosetup is used to create an
                    executable installer. 
                    All the necessary packaging code is in make.py
                    and driven from the Makefile (<tt>windist</tt> target).</p>
                    <h5>Mac OS X</h5>
                    <p>On Mac OS X, py2app is used to bundle the application. The resulting
                    application is packaged into a dmg file using the <tt>hdiutil</tt>
                    utility, which is part of Mac OS X. 
                    All the necessary packaging code is in make.py
                    and driven from the Makefile (<tt>dmg</tt> target).</p>
                    <h5>Linux</h5>
                    <p>We create RPM and Debian packages on Ubuntu (<tt>rpm</tt> and <tt>deb</tt>
                    targets) and a Fedora RPM package on Fedora (<tt>fedora</tt> target). 
                    Alternatively, Linux users that have installed python and wxPython
                    themselves (if not installed by default) can also use the source
                    distribution. The source distributions are created by the
                    <tt>sdist</tt> Makefile target.</p>
                    
                    <h2>Coding style</h2>
                    <p>Class names are StudlyCaps. Method names are camelCase, except
                    for wxPython methods that are called or overridden because those are
                    StudlyCaps. At first this looked ugly, a mixture of two
                    styles. But it turned out to be quite handy, since you can easily
                    see whether some method is a wxPython method or not.</p>
                    
                    <h2>Mercurial usage conventions</h2>
                    <p>Releases are tagged ReleaseX_Y_Z and for each ReleaseX_Y_0 a 
                    branch (ReleaseX_Y_Branch) is created to facilitate bug fix releases. 
                    The release tagging and branching is part of 
                    the release process as documented in release.py.</p>
                    <p>For new big features, feature-specific branches may be created to 
                    facilitate parallel development, checking in changes while developing, 
                    and keep the code on the main trunk releaseable. The process is as 
                    follows:</p>
                    <ul>
                    <li>The feature is discussed on taskcoach-dev.</li>
                    <li>If all agree it's a good feature to work on, a
                    Feature_&lt;FeatureName&gt;_Branch branch is created and used for
                    development of the feature.</li>
                    <li>When the feature is done, it is announced on taskcoach-dev.</li>
                    <li>The feature is tested on all platforms.</li>
                    <li>The changes are merged back to main trunk.</li>
                    </ul>
                    <p>
                    For small new features, development is done on the trunk, but all unittests
                    should succeed before committing.
                    </p>
                    
                    <h2>Blog</h2>
                    <p>Frank keeps a not very frequent 
                    <a href="https://taskcoach.blogspot.com">blog</a> about
                    lessons learned from developing %(name)s.</p>
                </div>
                <div class="span2">"""
    + ads
    + """
                </div>
            </div>"""
)


def ensureFolderExists(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)


def writeFile(folder, filename, contents):
    ensureFolderExists(folder)
    filename = os.path.join(folder, filename)
    print("Creating %s" % filename)
    fd = open(filename, "w")
    fd.write(contents.encode("UTF-8"))
    fd.close()


def expandPatterns(*patterns):
    for pattern in patterns:
        for filename in glob.glob(pattern):
            yield filename


def copyFiles(folder, *patterns):
    ensureFolderExists(folder)
    for source in expandPatterns(*patterns):
        target = os.path.join(folder, os.path.basename(source))
        print("Copying %s to %s" % (source, target))
        shutil.copyfile(source, target)


def copyDir(targetFolder, subFolder, files="*"):
    targetFolder = os.path.join(targetFolder, subFolder)
    files = os.path.join(subFolder, files)
    copyFiles(targetFolder, files)


def createPAD(folder, filename="pad.xml"):
    padTemplate = open(filename).read()
    writeFile(folder, filename, padTemplate % meta.metaDict)


def createVersionFile(folder, filename="version.txt"):
    textTemplate = open(filename).read()
    writeFile(folder, filename, textTemplate % meta.metaDict)


def createHTMLPages(targetFolder, pages):
    for title, text in list(pages.items()):
        footer = style.footer
        contents = style.header + text % meta.metaDict + footer
        writeFile(targetFolder, "%s.html" % title, contents)


def createThumbnail(
    srcFilename,
    targetFolder,
    bitmapType=wx.BITMAP_TYPE_PNG,
    thumbnailWidth=200.0,
):
    if os.path.basename(srcFilename).startswith("Thumb"):
        return
    image = wx.Image(srcFilename, bitmapType)
    scaleFactor = thumbnailWidth / image.Width
    thumbnailHeight = int(image.Height * scaleFactor)
    image.Rescale(thumbnailWidth, thumbnailHeight)
    thumbFilename = os.path.join(
        targetFolder, "Thumb-" + os.path.basename(srcFilename)
    )
    print("Creating %s" % thumbFilename)
    image.SaveFile(thumbFilename, bitmapType)


def createThumbnails(targetFolder):
    for source in expandPatterns(os.path.join(targetFolder, "*.png")):
        createThumbnail(source, targetFolder)


websiteFolder = os.path.join("..", "website.out")
createHTMLPages(websiteFolder, pages)
createPAD(websiteFolder)
createVersionFile(websiteFolder)
copyFiles(websiteFolder, "messages.txt", "robots.txt", "*.ico")
for subFolder in "images", "js", "css", "downloads":
    copyDir(websiteFolder, subFolder)
for subFolder in os.listdir("screenshots"):
    if not subFolder.startswith("."):
        copyDir(websiteFolder, os.path.join("screenshots", subFolder))
        createThumbnails(os.path.join(websiteFolder, "screenshots", subFolder))
