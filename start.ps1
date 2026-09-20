$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$dockerPath = if ($dockerCommand) { $dockerCommand.Source } else { "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe" }
& $dockerPath compose up -d --build --force-recreate
if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar o chat. Confira se o Docker Desktop está aberto.' }
Write-Host 'Chat disponível em http://localhost:8501'
