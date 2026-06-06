[Setup]
AppName=SCAD Forecast Tool
AppVersion=1.0.0
DefaultDirName={autopf}\SCAD Forecast Tool
DefaultGroupName=SCAD Forecast Tool
OutputBaseFilename=SCAD-Forecast-Tool-Setup
OutputDir=dist
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "dist\SCAD Forecast Tool\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\SCAD Forecast Tool"; Filename: "{app}\SCAD Forecast Tool.exe"
Name: "{commondesktop}\SCAD Forecast Tool"; Filename: "{app}\SCAD Forecast Tool.exe"

[Run]
Filename: "{app}\SCAD Forecast Tool.exe"; Description: "Launch SCAD Forecast Tool"; Flags: nowait postinstall skipifsilent
