# Task Coach - Your friendly task manager
# Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
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


# Makefile to create binary and source distributions and generate the 
# simple website (intermediate files are in ./build, distributions are
# put in ./dist, the files for the website end up in ./website.out)

DOT="dot"       # dot should be on the path

# Python should be on the path. On 64 bits Mac OS X, use the 32-bits version
# (wx only works in 32 bits mode and the environment/default write trick to
# make it the default does not seem to work on Lion).

ifeq "$(shell uname -s)" "Darwin"
BITS=$(shell python -c "import struct; print len(struct.pack('L', 0))")
ifeq "$(BITS)" "8"
    PYTHON?="python-32"
else
    PYTHON?="python"
endif
else
    PYTHON?="python"
endif

ifeq (CYGWIN_NT,$(findstring CYGWIN_NT,$(shell uname)))
    INNOSETUP="/cygdrive/c/Program Files/Inno Setup 5/ISCC.exe"
    PORTABLEAPPSINSTALLER="/cygdrive/c/Program Files/PortableApps.comInstaller/PortableApps.comInstaller.exe"
    EPYDOC=$(PYTHON) $(shell python -c "import os, sys; print(\"'\" + os.path.join(os.path.split(sys.executable)[0], 'Scripts', 'epydoc.py') + \"'\")")
else
    EPYDOC="epydoc"
endif

TCVERSION=$(shell python -c "import taskcoachlib.meta.data as data; print(data.version)")
TCPORTABLE=$(shell python -c "import os; print \"'\" + os.path.join(os.getcwd(), 'build', 'TaskCoachPortable') + \"'\"")

ifeq ($(PGPID)x,x)
PGPID=a3e41706
endif

revision:
	echo "revision='$(TCREV)'" > taskcoachlib/meta/revision.py

prepare: thirdpartymodules icons i18n templates

windists: windist winpenpack portableapps sdist_windows

windist: py2exe
	$(INNOSETUP) build/taskcoach.iss

py2exe: prepare
	$(PYTHON) pymake.py py2exe

sdist_windows: prepare changes templates dist/TaskCoach-$(TCVERSION).zip

dist/TaskCoach-$(TCVERSION).zip:
	$(PYTHON) pymake.py sdist --formats=zip --no-prune --template=build.in/windows/MANIFEST.in

sdist_linux: prepare changes templates dist/TaskCoach-$(TCVERSION).tar.gz

sdist_ubuntu: sdist_linux
	# Launchpad does not support one size fits all packages...
	cp dist/TaskCoach-$(TCVERSION).tar.gz dist/taskcoach_$(TCVERSION)-0ubuntu12~precise.tar.gz
	cp dist/TaskCoach-$(TCVERSION).tar.gz dist/taskcoach_$(TCVERSION)-0ubuntu14~trusty.tar.gz
	cp dist/TaskCoach-$(TCVERSION).tar.gz dist/taskcoach_$(TCVERSION)-0ubuntu16~xenial.tar.gz
	cp dist/TaskCoach-$(TCVERSION).tar.gz dist/taskcoach_$(TCVERSION)-0ubuntu18~bionic.tar.gz

sdist_raw:
	mkdir -p dist
	cp -a . ../../tmp-sdist
	cd ../../tmp-sdist; make nuke; find . -name ".hg" | xargs -d '\n' rm -rf
	mv ../../tmp-sdist dist/TaskCoach-$(TCVERSION)
	cd dist; tar czf TaskCoach-$(TCVERSION)-raw.tgz TaskCoach-$(TCVERSION); rm -rf TaskCoach-$(TCVERSION)

dist/TaskCoach-$(TCVERSION).tar.gz:
	$(PYTHON) pymake.py sdist --formats=gztar --no-prune --template=build.in/debian/MANIFEST.in
	echo Created dist/TaskCoach-$(TCVERSION).tar.gz

rpm: prepare changes templates
	cp build.in/debian/MANIFEST.in .
	$(PYTHON) pymake.py bdist_rpm --requires "python2.5,python-wxgtk2.8" --group "Applications/Productivity"
	rm MANIFEST.in

fedora: prepare changes templates
	cp build.in/debian/MANIFEST.in .
	$(PYTHON) pymake.py bdist_rpm_fedora
	rm MANIFEST.in

opensuse: sdist_linux
	cp build.in/debian/MANIFEST.in .
	$(PYTHON) pymake.py bdist_rpm_opensuse 
	mv dist/taskcoach-$(TCVERSION)-1.noarch.rpm dist/taskcoach-$(TCVERSION)-1.opensuse.i386.rpm
	mv dist/taskcoach-$(TCVERSION)-1.src.rpm dist/taskcoach-$(TCVERSION)-1.opensuse.src.rpm

deb: sdist_linux
	mv dist/TaskCoach-$(TCVERSION).tar.gz dist/TaskCoach_$(TCVERSION).tar.gz
	LC_ALL=C $(PYTHON) pymake.py bdist_deb --sdist=dist/TaskCoach_$(TCVERSION).tar.gz
	mv dist/taskcoach_$(TCVERSION)-1_all.deb dist/taskcoach_$(TCVERSION)-1.deb

ubuntu: sdist_ubuntu
	LC_ALL=C $(PYTHON) pymake.py bdist_ubuntu precise 12 --sdist=dist/taskcoach_$(TCVERSION)-0ubuntu12~precise.tar.gz
	mv build build-precise
	LC_ALL=C $(PYTHON) pymake.py bdist_ubuntu trusty 14 --sdist=dist/taskcoach_$(TCVERSION)-0ubuntu14~trusty.tar.gz
	mv build build-trusty
	LC_ALL=C $(PYTHON) pymake.py bdist_ubuntu xenial 16 --sdist=dist/taskcoach_$(TCVERSION)-0ubuntu16~xenial.tar.gz
	mv build build-xenial
	LC_ALL=C $(PYTHON) pymake.py bdist_ubuntu bionic 18 --sdist=dist/taskcoach_$(TCVERSION)-0ubuntu18~bionic.tar.gz
	mv build build-bionic

ppa_sign: ubuntu
	cd build-precise; debsign --re-sign -k0x$(PGPID) taskcoach_$(TCVERSION)-0ubuntu12~precise-1_source.changes
	cd build-trusty; debsign --re-sign -k0x$(PGPID) taskcoach_$(TCVERSION)-0ubuntu14~trusty-1_source.changes
	cd build-xenial; debsign --re-sign -k0x$(PGPID) taskcoach_$(TCVERSION)-0ubuntu16~xenial-1_source.changes
	cd build-bionic; debsign --re-sign -k0x$(PGPID) taskcoach_$(TCVERSION)-0ubuntu18~bionic-1_source.changes

# Split PPA by version because the upload has a tendency to fail so the buildbot must retry

ppa_rel_precise:
	cd build-precise; dput ppa:taskcoach-developers/release-snapshot taskcoach_$(TCVERSION)-0ubuntu12~precise-1_source.changes

ppa_rel_trusty:
	cd build-trusty; dput ppa:taskcoach-developers/release-snapshot taskcoach_$(TCVERSION)-0ubuntu14~trusty-1_source.changes

ppa_rel_xenial:
	cd build-xenial; dput ppa:taskcoach-developers/release-snapshot taskcoach_$(TCVERSION)-0ubuntu16~xenial-1_source.changes

ppa_rel_bionic:
	cd build-bionic; dput ppa:taskcoach-developers/release-snapshot taskcoach_$(TCVERSION)-0ubuntu18~bionic-1_source.changes

ppa_relnext_precise:
	cd build-precise; dput ppa:taskcoach-developers/nextrelease-snapshot taskcoach_$(TCVERSION)-0ubuntu12~precise-1_source.changes

ppa_relnext_trusty:
	cd build-trusty; dput ppa:taskcoach-developers/nextrelease-snapshot taskcoach_$(TCVERSION)-0ubuntu14~trusty-1_source.changes

ppa_relnext_xenial:
	cd build-xenial; dput ppa:taskcoach-developers/nextrelease-snapshot taskcoach_$(TCVERSION)-0ubuntu16~xenial-1_source.changes

ppa_relnext_bionic:
	cd build-bionic; dput ppa:taskcoach-developers/nextrelease-snapshot taskcoach_$(TCVERSION)-0ubuntu18~bionic-1_source.changes

ppa_release_precise:
	cd build-precise; dput ppa:taskcoach-developers/ppa taskcoach_$(TCVERSION)-0ubuntu12~precise-1_source.changes

ppa_release_trusty:
	cd build-trusty; dput ppa:taskcoach-developers/ppa taskcoach_$(TCVERSION)-0ubuntu14~trusty-1_source.changes

ppa_release_xenial:
	cd build-xenial; dput ppa:taskcoach-developers/ppa taskcoach_$(TCVERSION)-0ubuntu16~xenial-1_source.changes

ppa_release_bionic:
	cd build-bionic; dput ppa:taskcoach-developers/ppa taskcoach_$(TCVERSION)-0ubuntu18~bionic-1_source.changes

app: prepare
	$(PYTHON) pymake.py py2app
	chmod 644 "build/Task Coach/TaskCoach.app/Contents/Resources/taskcoach.py"

dmg-goodies: app
	mkdir "build/Task Coach/.Resources"
	cp -f dist.in/macos/dmg-background.png "build/Task Coach/.Resources/"
	cp -f dist.in/macos/config "build/Task Coach/.DS_Store"
	ln -s /Applications "build/Task Coach/Applications"

dmgbase:
	hdiutil create -ov -imagekey zlib-level=9 -fs "HFS+" -srcfolder "build/Task Coach" dist/TaskCoach-$(TCVERSION).dmg

dmg: dmg-goodies dmgbase

dmg-signed: dmg-goodies
	for target in Contents/Frameworks/*.dylib Contents/Frameworks/Python.framework Contents/MacOS/python .; do \
		codesign -f --verify --verbose --sign "Mac Developer:" --entitlements TaskCoach.entitlements "build/Task Coach/TaskCoach.app/$$target"; \
	done
	make dmgbase

winpenpack: py2exe 
	$(PYTHON) pymake.py bdist_winpenpack

portableapps: py2exe
	$(PYTHON) pymake.py bdist_portableapps
	$(PORTABLEAPPSINSTALLER) $(TCPORTABLE)
	mv build/TaskCoachPortable_$(TCVERSION).paf.exe dist

icons: icons.in/iconmap.py icons.in/nuvola.zip icons.in/splash.png
	cd icons.in; $(PYTHON) make.py

templates: 
	cd templates.in; $(PYTHON) make.py

thirdpartymodules:
	$(PYTHON) fixinit.py

website: changes
	cd website.in; $(PYTHON) make.py; cd ..
	$(PYTHON) tools/webchecker.py website.out/index.html

epydoc:
	$(EPYDOC) --parse-only -v --simple-term -o epydoc.out taskcoachlib taskcoach.py

dot:
	$(PYTHON) tools/dot.py taskcoachlib/gui/viewer > doc/viewer.dot
	$(PYTHON) tools/dot.py taskcoachlib/gui/dialog > doc/dialog.dot
	$(DOT) -Tpng -Kdot -O doc/*.dot

i18n: templates taskcoachlib/i18n/nl.py

taskcoachlib/i18n/nl.py: i18n.in/messages.pot $(shell find i18n.in -name '*.po')
	cd i18n.in; $(PYTHON) make.py

i18n.in/messages.pot: $(shell find taskcoachlib -name '*.py' | grep -v i18n)
	$(PYTHON) tools/pygettext.py --output-dir i18n.in taskcoachlib

changes:
	$(PYTHON) changes.in/make.py text > CHANGES.txt
	$(PYTHON) changes.in/make.py debian > changelog_content
	$(PYTHON) changes.in/make.py html 7 > website.in/changes.html
	$(PYTHON) changes.in/make.py html > website.in/all_changes.html

unittests: thirdpartymodules icons templates
	cd tests; $(PYTHON) test.py --unittests --verbose

integrationtests: thirdpartymodules icons templates
	cd tests; $(PYTHON) test.py --integrationtests

languagetests: thirdpartymodules icons i18n
	cd tests; $(PYTHON) test.py --languagetests

releasetests: thirdpartymodules icons i18n sdist_linux
	cd tests; $(PYTHON) test.py --releasetests

# FIXME: disttests should depend on either windist, deb, rpm or dmg...
disttests:
	cd tests; $(PYTHON) test.py --disttests

alltests: prepare sdist_linux
	cd tests; $(PYTHON) test.py --alltests

coverage: coverage_run coverage_report

coverage_run:
	cd tests; $(PYTHON) -m coverage run --source=../taskcoachlib,unittests test.py

coverage_report:
	cd tests; $(PYTHON) -m coverage html -d coverage.out --omit=../taskcoachlib/i18n/po2dict.py,../taskcoachlib/i18n/??.py,../taskcoachlib/i18n/???.py,../taskcoachlib/i18n/??_??.py,../taskcoachlib/thirdparty/*.py,../taskcoachlib/meta/debug.py,test.py

pylint:
	-pylint --rcfile=.pylintrc -f html taskcoachlib > pylint.html

CLEANFILES=build build-* website.out MANIFEST README.txt INSTALL.txt LICENSE.txt CHANGES.txt @webchecker.pickle .profile tests/.coverage tests/coverage.out
REALLYCLEANFILES=dist taskcoachlib/gui/icons.py taskcoachlib/persistence/xml/templates.py \
	taskcoachlib/i18n/??.py taskcoachlib/i18n/???.py taskcoachlib/i18n/??_??.py .\#* */.\#* */*/.\#*

clean:
	$(PYTHON) pymake.py clean
	rm -rf $(CLEANFILES)

reallyclean:
	$(PYTHON) pymake.py clean --really-clean
	rm -rf $(CLEANFILES) $(REALLYCLEANFILES)

nuke:
	hg purge --all
