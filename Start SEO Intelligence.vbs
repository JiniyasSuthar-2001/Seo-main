' ONE-CLICK LAUNCHER FOR SEO INTELLIGENCE PLATFORM
' This script starts the backend and frontend invisibly and opens the browser.

Set WshShell = CreateObject("WScript.Shell")
Dim fso
Set fso = CreateObject("Scripting.FileSystemObject")
Dim currentDir
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

' 1. Start Backend Server (Hidden)
' Checks if virtual environment exists, otherwise uses global python
Dim pythonExec
If fso.FileExists(currentDir & "\backend\.venv\Scripts\python.exe") Then
    pythonExec = """" & currentDir & "\backend\.venv\Scripts\python.exe"""
Else
    pythonExec = "python"
End If

Dim backendCmd
backendCmd = "cmd.exe /c cd """ & currentDir & "\backend"" && " & pythonExec & " -m uvicorn app.main:app --port 8000"
WshShell.Run backendCmd, 0, False ' 0 = Hidden Window, False = Do not wait

' 2. Start Frontend Server (Hidden)
Dim frontendCmd
frontendCmd = "cmd.exe /c cd """ & currentDir & "\frontend"" && python -m http.server 8001"
WshShell.Run frontendCmd, 0, False

' 3. Wait 3 seconds for servers to spin up
WScript.Sleep 3000

' 4. Open Browser
WshShell.Run "http://localhost:8001"
