' Double-click this to launch the app with no console window.
Dim fso, sh, here, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

here = fso.GetParentFolderName(WScript.ScriptFullName)
cmd  = """" & here & "\ELC_Launcher.cmd"""

' 0 = hidden window, False = don’t wait (non-blocking)
sh.Run cmd, 0, False