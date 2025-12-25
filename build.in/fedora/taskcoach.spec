# Task Coach - Your friendly task manager
# Fedora RPM Spec File
#
# Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
# Copyright (C) 2008 Marcin Zajaczkowski <mszpak@wp.pl>
# Copyright (C) 2024 Réal Carbonneau <https://github.com/realcarbonneau>
#
# Task Coach is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

Name:           taskcoach
Version:        2.0.0.75
Release:        1%{?dist}
Summary:        Your friendly task manager

License:        GPL-3.0-or-later
URL:            https://github.com/taskcoach/taskcoach
Source0:        %{url}/archive/refs/heads/main.tar.gz#/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-pip
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib

# Dependency Installation Strategy:
# 1. Use Fedora packages for all available dependencies
# 2. Bundle via pip: squaremap (not in repos), pyparsing (version too old)
# 3. Filter auto-generated deps for bundled packages
# See docs/PACKAGING.md for full dependency strategy.
%global __requires_exclude ^python3\\.?[0-9]*dist\\((squaremap|pyparsing)\\)
%global __provides_exclude ^python3\\.?[0-9]*dist\\((squaremap|pyparsing)\\)

# Runtime dependencies - from Fedora repos
Requires:       python3 >= 3.8
Requires:       python3-wxpython4 >= 4.2.0
Requires:       python3-six
Requires:       python3-pypubsub
Requires:       python3-watchdog
Requires:       python3-chardet
Requires:       python3-dateutil
Requires:       python3-lxml
Requires:       python3-pyxdg
Requires:       python3-keyring
Requires:       python3-numpy
Requires:       python3-fasteners
Requires:       python3-zeroconf
Requires:       libXScrnSaver
Requires:       xdg-utils

# Optional dependencies
Recommends:     espeak-ng

# Bundled via pip:
# - squaremap: not in Fedora repos
# - pyparsing>=3.1.3: Fedora has older version, need pp.Tag() API

%description
Task Coach is a simple open source todo manager to keep track of personal
tasks and todo lists. It is designed for composite tasks, and also offers
effort tracking, categories, notes and more.

Features:
- Composite tasks (subtasks)
- Effort tracking per task
- Categories and tags
- Notes attachments
- Reminders and recurring tasks
- Multiple views (tree, list, calendar, timeline)
- Import/Export capabilities
- Cross-platform (Linux, Windows, macOS)

%prep
%autosetup -n taskcoach-main

%build
%py3_build

%install
%py3_install

# Remove __pycache__ from bin directory if present
rm -rfv %{buildroot}%{_bindir}/__pycache__

# Ensure wheel is available for proper dist-info creation
pip3 install --no-cache-dir wheel

# Bundle packages not in Fedora repos or with version issues
# - squaremap: not in Fedora repos
# - pyparsing>=3.1.3: Fedora 40 has 3.0.x, need 3.1.3+ for pp.Tag() API
pip3 install --no-cache-dir --no-deps --target=%{buildroot}%{python3_sitelib} \
    squaremap \
    "pyparsing>=3.1.3"

# Install desktop file
install -Dm644 build.in/linux_common/taskcoach.desktop \
    %{buildroot}%{_datadir}/applications/%{name}.desktop

# Validate desktop file
desktop-file-validate %{buildroot}%{_datadir}/applications/%{name}.desktop

# Install AppStream metadata
install -Dm644 build.in/debian/taskcoach.appdata.xml \
    %{buildroot}%{_metainfodir}/%{name}.appdata.xml

# Validate AppStream metadata
appstream-util validate-relax --nonet %{buildroot}%{_metainfodir}/%{name}.appdata.xml

# Install icon
install -Dm644 icons.in/taskcoach.png \
    %{buildroot}%{_datadir}/pixmaps/%{name}.png

# Install Welcome.tsk for first-run experience
install -Dm644 Welcome.tsk \
    %{buildroot}%{_datadir}/%{name}/Welcome.tsk

%files
%license COPYRIGHT.txt
%doc README.md
%{_bindir}/taskcoach.py
%{python3_sitelib}/taskcoachlib/
%{python3_sitelib}/TaskCoach-*.egg-info/
%{python3_sitelib}/squaremap/
%{python3_sitelib}/SquareMap-*.dist-info/
%{python3_sitelib}/pyparsing/
%{python3_sitelib}/pyparsing-*.dist-info/
%{_datadir}/applications/%{name}.desktop
%{_metainfodir}/%{name}.appdata.xml
%{_datadir}/pixmaps/%{name}.png
%{_datadir}/%{name}/

%changelog
* Wed Dec 25 2024 Task Coach Developers <developers@taskcoach.org> - 2.0.0.75-1
- Major version bump to 2.0.0 reflecting Python 3 modernization
- Merged detached fork with 600+ patches and improvements
- Full GTK3/wxPython 4.x compatibility
- New GitHub Actions CI/CD workflows
- Comprehensive packaging for Debian, Fedora, Arch, AppImage

* Tue Dec 24 2024 Task Coach Developers <developers@taskcoach.org> - 1.6.1.74-1
- Modernized spec file for Fedora 39+
- Consistent dependency strategy: distro packages first, pip fallback
- Bundled: squaremap (not in repos), pyparsing>=3.1.3 (version too old)
- Added AppStream metadata validation

* Mon Aug 15 2011 Jerome Laheurte <fraca7@free.fr> - 1.2.26-1
- Legacy: Apply patch from Oleg Tsarev for x64 systems
