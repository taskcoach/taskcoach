# -*- coding: ISO-8859-1 -*-

'''
Task Coach - Your friendly task manager
Copyright (C) 2004-2012 Task Coach developers <developers@taskcoach.org>

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

from taskcoachlib import meta


header = '''
<!DOCTYPE HTML PUBLIC "-//W3C//DTD html 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />     
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.6.4/jquery.min.js"></script>
        <script type="text/javascript" src="http://twitter.github.com/bootstrap/1.4.0/bootstrap-dropdown.js"></script>
        <script type="text/javascript" src="js/prototype.js"></script>
        <script type="text/javascript" src="js/scriptaculous.js?load=effects,builder"></script>
        <script type="text/javascript" src="js/lightbox.js"></script>
        <script type="text/javascript">
/* <![CDATA[ */
    (function() {
        var s = document.createElement('script'), t = document.getElementsByTagName('script')[0];
        s.type = 'text/javascript';
        s.async = true;
        s.src = 'http://api.flattr.com/js/0.6/load.js?mode=auto';
        t.parentNode.insertBefore(s, t);
    })();
/* ]]> */
        </script>
        <link rel="stylesheet" href="http://twitter.github.com/bootstrap/1.4.0/bootstrap.min.css">
        <link rel="stylesheet" href="css/lightbox.css" type="text/css" media="screen" />
        <link rel="shortcut icon" href="favicon.ico" type="image/x-icon" />
        <link rel="canonical" href="%(url)s" />
        <title>%(name)s</title>
        <style type="text/css">
      body {
        padding-top: 60px;
      }
        </style>
    </head>
    <body>
    <script type="text/javascript">
var gaJsHost = (("https:" == document.location.protocol) ? "https://ssl." : "http://www.");
document.write(unescape("%%3Cscript src='" + gaJsHost + "google-analytics.com/ga.js' type='text/javascript'%%3E%%3C/script%%3E"));
    </script>
    <script type="text/javascript">
try {
var pageTracker = _gat._getTracker("UA-8814256-1");
pageTracker._trackPageview();
} catch(err) {}</script>
    <div class="topbar">
        <div class="topbar-inner">
            <div class="container">
                <a class="brand" href="index.html">%(name)s</a>
                <ul class="nav">
                    <li class="dropdown" data-dropdown="dropdown">
                        <a href="#" class="dropdown-toggle">About</a>
                        <ul class="dropdown-menu">
                            <li><a href="index.html" title="%(name)s overview">Overview</a></li>
                            <li><a href="screenshots.html" 
                                   title="View some screenshots of %(name)s here">Screenshots</a></li>
                            <li><a href="features.html" 
                                   title="List of features in the current version of %(name)s">Features</a></li>
                            <li><a href="i18n.html" 
                                   title="Available translations">Translations</a></li>
                            <li><a href="https://sourceforge.net/projects/taskcoach/?sort=usefulness#reviews-n-ratings"
                                   title="See what others have to say about %(name)s">User reviews</a></li>
                            <li><a href="changes.html" 
                                   title="An overview of bugs fixed and features added per version of %(name)s">Change history</a></li>
                            <li><a href="license.html" 
                                   title="Your rights and obligations when using %(name)s">License</a></li>
                        </ul>
                    </li>
                </ul>
                <ul class="nav">
                    <li class="dropdown" data-dropdown="dropdown">
                        <a href="#" class="dropdown-toggle">Download</a>
                        <ul class="dropdown-menu">
                            <li><a href="download_for_windows.html" title="Download %(name)s for Windows">Windows</a></li>
                            <li><a href="download_for_mac.html" title="Download %(name)s for Mac OS X">Mac OS X</a></li>
                            <li><a href="download_for_linux.html" title="Download %(name)s for Linux">Linux</a></li>
                            <li><a href="download_for_bsd.html" title="Download %(name)s for BSD">BSD</a></li>
                            <li><a href="download_for_iphone.html" title="Download %(name)s for iPhone and iPod Touch">iPhone and iPod Touch</a></li>
                            <li><a href="download_sources.html" title="Download %(name)s sources">Sources</a></li>
                            <li><a href="download_daily_build.html" title="Download %(name)s daily builds">Daily builds</a></li>
                            <li><a href="download_old_releases.html" title="Download old releases of %(name)s ">Old releases</a></li>
                        </ul>
                </ul>
                <ul class="nav">
                    <li><a href="getsupport.html">Get support</a></li>
                    <li><a href="givesupport.html">Give support</a></li>
                </ul>
                <ul class="nav secondary-nav">
                    <li><a href="changes.html">%(name)s %(version)s was released on %(date)s.</a></li>
                    <!--
                    <li><a class="FlattrButton" style="display:none;" rev="flattr;button:compact;" href="http://taskcoach.org"></a>
                        <noscript><a href="http://flattr.com/thing/181658/Task-Coach-Your-friendly-task-manager" 
                        target="_blank"><img src="http://api.flattr.com/button/flattr-badge-large.png" alt="Flattr this" title="Flattr this" border="0" /></a></noscript></li>
                    <li><a href="http://twitter.com/share" class="twitter-share-button" data-url="http://taskcoach.org" data-text="Check out Task Coach: a free and open source todo app for Windows, Mac, Linux and iPhone." data-count="horizontal" data-via="taskcoach">Tweet</a><script type="text/javascript" src="http://platform.twitter.com/widgets.js"></script></li>
                    li><iframe src="http://www.facebook.com/plugins/like.php?href=http%%3A%%2F%%2Ftaskcoach.org&amp;layout=button_count&amp;show_faces=true&amp;width=190&amp;action=like&amp;colorscheme=light&amp;height=21" 
                            scrolling="no" frameborder="0" 
                            style="border:none; overflow:hidden; width:190px; height:21px;" 
                            allowTransparency="true">
                    </iframe></li>
                    <li><g:plusone size="medium"></g:plusone></li>-->
                </ul>
            </div>
        </div>
    </div>
    <div class="container">
    <!--<div class="sidebar">
            <div class="well">
                <h5>Ads</h5>
                <p>
<script type="text/javascript"><!--
google_ad_client = "pub-2371570118755412";
/* 120x240, gemaakt 10-5-09 */
google_ad_slot = "6528039249";
google_ad_width = 120;
google_ad_height = 240;
//->
</script>
<script type="text/javascript"
src="http://pagead2.googlesyndication.com/pagead/show_ads.js">
</script>
                </p>                 
                <h5>Credits</h5>
                <ul>
                    <li>Web hosting courtesy of <a href="http://www.hostland.com">Hostland</a> and
                        <a href="http://henry.olders.ca">Henry Olders</a></li>
                    <li><a href="http://www.python.org"><img src="images/python-powered-w-70x28.png" alt="Python"
                           align=middle width="70" height="28" border="0"></a></li>
                    <li><a href="http://www.wxpython.org"><img
                           src="images/powered-by-wxpython-80x15.png"
                           alt="wxPython" width="80" height="15" border="0"></a></li>
                    <li><a href="http://www.icon-king.com">Nuvola icon set</a></li>
                    <li><a href="http://www.jrsoftware.org">Inno Setup</a></li>
                    <li><a href="http://twitter.github.com/bootstrap/">Twitter Bootstrap</a></li>
                    <li><a href="http://sourceforge.net/projects/taskcoach"><img src="http://sflogo.sourceforge.net/sflogo.php?group_id=130831&type=8" 
                           width="80" height="15" border="0" alt="Task Coach at SourceForge.net"/>
                        </a></li>
                    <li><script type='text/javascript' language='JavaScript' 
                                src='http://www.ohloh.net/projects/5109;badge_js'></script></li>
                </ul>
            </div>
        </div>-->
        <div class="content">                
'''%meta.metaDict

footer = '''        
        </div><!-- end of content div -->
        <script type="text/javascript" src="http://apis.google.com/js/plusone.js"></script>
        <footer>
            <p style="text-align: center">
                %(name)s is made possible by
            </p>
            <p style="text-align: center">
                <a href="http://www.hostland.com">Hostland</a> and
                <a href="http://henry.olders.ca">Henry Olders</a> (web hosting)
                <a href="http://www.python.org"><img src="images/python-powered-w-70x28.png" alt="Python"
                   valign="middle" align=middle width="70" height="28" border="0"></a>
                <a href="http://www.wxpython.org"><img valign="middle" src="images/powered-by-wxpython-80x15.png"
                   alt="wxPython" width="80" height="15" border="0"></a>
                <a href="http://www.icon-king.com">Nuvola</a> (icons)
                <a href="http://www.jrsoftware.org">Inno Setup</a>
                <a href="http://sourceforge.net/projects/taskcoach"><img src="http://sflogo.sourceforge.net/sflogo.php?group_id=130831&type=8" 
                    width="80" height="15" border="0" alt="Task Coach at SourceForge.net"/></a>
                <script type='text/javascript' language='JavaScript' 
                    src='http://www.ohloh.net/projects/5109;badge_js'></script>
            </p>
        </footer>
    </body>
</html>
'''%meta.metaDict
