# Task Coach - Your friendly task manager
# Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
# Copyright (C) 2008 Marcin Zajaczkowski <mszpak@wp.pl>
# 
# Task Coach is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Task Coach is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


%%define		originalName	TaskCoach

Name: 		%(filename_lower)s
Summary: 	%(description)s
Version: 	%(version)s
Release: 	1%%{?dist}
License: 	%(license_abbrev)s
Group: 		Applications/Productivity
URL: 		%(url)s
Source:		%(dist_download_prefix)s/TaskCoach-%%{version}.tar.gz
Source1:	taskcoach.png
Source2:	build.in/linux_common/taskcoach.desktop
BuildRoot: 	%%{_tmppath}/%%{name}-%%{version}-%%{release}-root-%%(%%{__id_u} -n)
BuildArch:	noarch
Requires: 	python >= %(pythonversion)s
Requires:	python-wxGTK >= %(wxpythonversionnumber)s
Requires:	python-twisted >= %(twistedversionnumber)s
Requires:	python-igraph >= %(igraphversionnumber)s

# Must have setuptools to build the package
BuildRequires: python-setuptools

%%description
%(long_description)s


%%prep
%%setup -q -n %%{originalName}-%%{version}

%%build
CFLAGS="%%{optflags}" %%{__python} pymake.py build

%%install
%%{__rm} -rf %%{buildroot}
# --root $RPM_BUILD_ROOT makes the package install with a single, expanded
# directory in %%{python_sitelib} and a separate egginfo directory.
%%{__python} setup.py install --skip-build --root="%%{buildroot}" --prefix="%%{_prefix}"
%%{__mkdir} -p %%{buildroot}%%{_datadir}/pixmaps
%%{__cp} -a %%{SOURCE1} %%{buildroot}%%{_datadir}/pixmaps/

desktop-file-install --vendor opensuse \
        --dir %%{buildroot}%%{_datadir}/applications \
        %%{SOURCE2}

# Install Welcome.tsk for first-run experience
%%{__mkdir} -p %%{buildroot}%%{_datadir}/taskcoach
%%{__cp} -a Welcome.tsk %%{buildroot}%%{_datadir}/taskcoach/

%%clean
%%{__rm} -rf %%{buildroot}

%%files
%%defattr(0644,root,root,0755)
%%attr(0755,root,root) %%{_bindir}/taskcoach.py
%%{_libdir}/python*/site-packages/taskcoachlib/*
%%{_libdir}/python*/site-packages/%%{originalName}-%%{version}-py*.egg-info
%%{_datadir}/applications/opensuse-taskcoach.desktop
%%{_datadir}/pixmaps/taskcoach.png
%%{_datadir}/taskcoach/Welcome.tsk
%%doc CHANGES.txt LICENSE.txt PUBLICITY.txt README.txt Welcome.tsk

%%exclude %%{_libdir}/python*/site-packages/buildlib/*.py*

%%changelog
* Sun Jul 3 2011 Frank Niessink <frank ATT niessink DOTT com> - 1.0.2-1
- fix unstalled but unpackaged file issue

* Fri Mar 26 2010 Frank Niessink <frank ATT niessink DOTT com> - 1.0.1-1
- no need to exclude pysyncml library here, it is no longer included upstream

* Sun Mar 13 2010 Frank Niessink <frank ATT niessink DOTT com> - 1.0.0-1
- integrate OpenSuse RPM build step into Task Coach build process
