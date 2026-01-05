# -*- coding: ISO-8859-1 -*-

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

from taskcoachlib import meta


header = (
    """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD html 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />     
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery.min.js"></script>
        <script type="text/javascript" src="js/bootstrap-dropdown.js"></script>
        <script type="text/javascript" src="js/jquery.lightbox-0.5.min.js"></script>
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
        <link rel="stylesheet" href="css/bootstrap.min.css">
        <link rel="stylesheet" href="css/jquery.lightbox-0.5.css" type="text/css" media="screen" />
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
$(function() {
    $('a.lightbox').lightBox(); // Select all links with class lightbox
});
    </script>
    <script type="text/javascript">
var gaJsHost = (("https:" == document.location.protocol) ? "https://ssl." : "http://www.");
document.write(unescape("%%3Cscript src='" + gaJsHost + "google-analytics.com/ga.js' type='text/javascript'%%3E%%3C/script%%3E"));
    </script>
    <script type="text/javascript">
try {
var pageTracker = _gat._getTracker("UA-8814256-1");
pageTracker._trackPageview();
} catch(err) {}</script>
    <div class="navbar navbar-fixed-top">
        <div class="navbar-inner">
            <div class="container">
                <a class="brand" title="Your friendly task manager" href="index.html">%(name)s</a>
                <ul class="nav">
                    <li class="dropdown" id="about_menu">
                        <a title="About %(name)s" href="#about_menu" class="dropdown-toggle" data-toggle="dropdown">About</a>
                        <ul class="dropdown-menu">
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
                    <li class="dropdown" id="download_menu">
                        <a href="#download_menu" title="Download %(name)s for free" class="dropdown-toggle" data-toggle="dropdown">Download</a>
                        <ul class="dropdown-menu">
                            <li><a href="download_for_windows.html" title="Download %(name)s for Windows">Windows</a></li>
                            <li><a href="download_for_mac.html" title="Download %(name)s for Mac OS X">Mac OS X</a></li>
                            <li><a href="download_for_linux.html" title="Download %(name)s for Linux">Linux</a></li>
                            <li><a href="download_for_bsd.html" title="Download %(name)s for BSD">BSD</a></li>
                            <li class="divider"></li>
                            <li><a href="download_sources.html" title="Download %(name)s sources">Sources</a></li>
                            <li><a href="download_daily_build.html" title="Download %(name)s daily builds">Daily builds</a></li>
                            <li><a href="download_old_releases.html" title="Download old releases of %(name)s ">Old releases</a></li>
                        </ul>
                </ul>
                <ul class="nav">
                    <li><a title="Support options" href="getsupport.html">Get support</a></li>
                    <li><a title="How you can help us" href="givesupport.html">Give support</a></li>
                </ul>
                <ul class="nav pull-right">
                    <li><a href="changes.html">%(name)s %(version)s was released on %(date)s.</a></li>
                </ul>
            </div>
        </div>
    </div>
    <div class="container">
        <div class="content">                
"""
    % meta.metaDict
)

footer = (
    """        
        </div><!-- end of content div -->
        <script type="text/javascript" src="http://apis.google.com/js/plusone.js"></script>
        <footer class="footer">
            <hr>
            <p style="text-align: center">
                %(name)s is made possible by:
                <br>
                <a href="https://www.python.org"><img src="images/python-powered-w-70x28.png" alt="Python"
                   valign="middle" align=middle width="70" height="28" border="0"></a>
                &nbsp;
                <a href="https://www.wxpython.org"><img valign="middle" src="images/powered-by-wxpython-80x15.png"
                   alt="wxPython" width="80" height="15" border="0"></a>
                &nbsp;
                <a href="https://www.icon-king.com">Nuvola</a> (icons)
                &nbsp;
                <a href="https://www.jrsoftware.org">Inno Setup</a>
                &nbsp;
                <a href="https://sourceforge.net/projects/taskcoach"><img src="http://sflogo.sourceforge.net/sflogo.php?group_id=130831&type=8" 
                    width="80" height="15" border="0" alt="Task Coach at SourceForge.net"/></a>
                &nbsp;
                <script type='text/javascript' language='JavaScript' 
                    src='https://www.ohloh.net/projects/5109;badge_js'></script>
            </p>
        </footer>
    </body>
</html>
"""
    % meta.metaDict
)
