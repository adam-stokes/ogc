# From https://chocolatey.org/install
$installScript = Join-Path -Path $env:TEMP -ChildPath "$(([GUID]::NewGuid()).Guid.ToString()).ps1"
Set-ExecutionPolicy Bypass -Scope Process -Force
Invoke-WebRequest 'https://chocolatey.org/install.ps1' -UseBasicParsing -OutFile $installScript
& $installScript

#Update-SessionEnvironment
choco feature enable --name="'autouninstaller'"
# - not recommended for production systems:
choco feature enable --name="'allowGlobalConfirmation'"
# - not recommended for production systems:
choco feature enable --name="'logEnvironmentValues'"


# Set Configuration
choco config set cacheLocation $env:ALLUSERSPROFILE\choco-cache
choco config set commandExecutionTimeoutSeconds 14400