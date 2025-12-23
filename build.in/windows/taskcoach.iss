; Task Coach - Your friendly task manager
; Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
; 
; Task Coach is free software: you can redistribute it and/or modify
; it under the terms of the GNU General Public License as published by
; the Free Software Foundation, either version 3 of the License, or
; (at your option) any later version.
; 
; Task Coach is distributed in the hope that it will be useful,
; but WITHOUT ANY WARRANTY; without even the implied warranty of
; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
; GNU General Public License for more details.
; 
; You should have received a copy of the GNU General Public License
; along with this program.  If not, see <http://www.gnu.org/licenses/>.
 
; Inno Setup Script

[Setup]
AppName=%(name)s
AppVerName=%(name)s %(version)s
AppMutex=%(filename)s
AppPublisher=%(author)s
AppPublisherURL=%(url)s
AppSupportURL=%(url)s
AppUpdatesURL=%(url)s
DefaultDirName={pf}\%(filename)s
DefaultGroupName=%(name)s
AllowNoIcons=yes
Compression=lzma
SolidCompression=yes
OutputDir=../dist
OutputBaseFilename=%(filename)s-%(version)s-win32
ChangesAssociations=yes 
WizardImageFile=..\icons.in\splash_inno.bmp
PrivilegesRequired=none

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: associate; Description: "{cm:AssocFileExtension,{app},.tsk}"; GroupDescription: "Other tasks:"; Flags: unchecked
Name: userstartup; Description: "Run %(name)s every time Windows is started"; GroupDescription: "Other tasks:"; Flags: unchecked

[Files]
Source: "%(filename)s-%(version)s-win32exe\%(filename)s.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "%(filename)s-%(version)s-win32exe\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
; Welcome.tsk for first-run experience
Source: "..\Welcome.tsk"; DestDir: "{app}"; Flags: ignoreversion
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[INI]
Filename: "{app}\%(filename)s.url"; Section: "InternetShortcut"; Key: "URL"; String: "%(url)s"

[InstallDelete]
Type: files; Name: "{app}\UxTheme.dll"
Type: files; Name: "{app}\%(filename_lower)s.exe.log"

[Registry]
Root: HKCR; Subkey: ".tsk"; ValueType: string; ValueName: ""; ValueData: "%(filename)s"; Flags: uninsdeletevalue; Check: IsAdminLoggedOn
Root: HKCR; Subkey: "%(filename)s"; ValueType: string; ValueName: ""; ValueData: "%(name)s File"; Flags: uninsdeletekey; Check: IsAdminLoggedOn
Root: HKCR; Subkey: "%(filename)s\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\%(filename)s.EXE,0"; Check: IsAdminLoggedOn
Root: HKCR; Subkey: "%(filename)s\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\%(filename)s.EXE"" ""%%1"""; Check: IsAdminLoggedOn
Root: HKCU; Subkey: "Software\Classes\.tsk"; ValueType: string; ValueName: ""; ValueData: "%(filename)sFile"; Flags: uninsdeletevalue; Check: not IsAdminLoggedOn
Root: HKCU; Subkey: "Software\Classes\%(filename)sFile"; ValueType: string; ValueName: ""; ValueData: "%(name)s File"; Flags: uninsdeletekey; Check: not IsAdminLoggedOn
Root: HKCU; Subkey: "Software\Classes\%(filename)sFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\%(filename)s.EXE,0"; Check: not IsAdminLoggedOn
Root: HKCU; Subkey: "Software\Classes\%(filename)sFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\%(filename)s.EXE"" ""%%1"""; Check: not IsAdminLoggedOn

[Icons]
Name: "{group}\%(name)s"; Filename: "{app}\%(filename)s.exe"; WorkingDir: "{app}"
Name: "{group}\{cm:ProgramOnTheWeb,%(name)s}"; Filename: "{app}\%(filename)s.url"
Name: "{group}\{cm:UninstallProgram,%(name)s}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\%(name)s"; Filename: "{app}\%(filename)s.exe"; Tasks: desktopicon; WorkingDir: "{app}"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\%(name)s"; Filename: "{app}\%(filename)s.exe"; Tasks: quicklaunchicon; WorkingDir: "{app}"
Name: "{userstartup}\%(name)s"; Filename: "{app}\%(filename)s.exe"; Tasks: userstartup

[Run]
Filename: "{app}\%(filename)s.exe"; Description: "{cm:LaunchProgram,%(name)s}"; Flags: nowait postinstall skipifsilent
Filename: "%(url)s/changes.html"; Description: "Show recent changes (opens a webbrowser)"; Flags: shellexec nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\%(filename)s.url"
