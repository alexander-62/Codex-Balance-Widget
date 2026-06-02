Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
launcherPath = fso.BuildPath(scriptDir, "codex_balance_widget_launcher.pyw")

shell.Run "pyw.exe -3 """ & launcherPath & """", 0, False
