Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
launcherPath = fso.BuildPath(scriptDir, "codex_balance_widget_launcher.pyw")
pythonwPath = "C:\Program Files\Python310\pythonw.exe"

If fso.FileExists(pythonwPath) Then
    shell.Run """" & pythonwPath & """ """ & launcherPath & """", 0, False
Else
    shell.Run "pyw.exe -3 """ & launcherPath & """", 0, False
End If
