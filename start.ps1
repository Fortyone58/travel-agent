# start.ps1 —— 一键启动旅行规划多Agent系统（后端 + 前端 + 打开浏览器）
# 用法：右键"使用 PowerShell 运行" 或 在终端执行 ./start.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "🚀 启动后端（FastAPI :8000）..."
$backend = Start-Process -FilePath ".\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "web:app", "--port", "8000" `
    -WindowStyle Minimized -PassThru

Start-Sleep 3

Write-Host "🚀 启动前端（Vue :5173）..."
Set-Location "$PSScriptRoot\frontend"
$frontend = Start-Process -FilePath "npm.cmd" `
    -ArgumentList "run", "dev" `
    -WindowStyle Minimized -PassThru

Start-Sleep 5
Write-Host ""
Write-Host "✅ 已启动！浏览器自动打开 http://localhost:5173/"
Start-Process "http://localhost:5173/"
Write-Host ""
Write-Host "提示：关闭本窗口不会停止服务；停止服务请在任务管理器中结束 python/node 进程。"
