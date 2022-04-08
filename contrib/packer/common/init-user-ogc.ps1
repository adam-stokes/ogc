$ProfilePath = '{0}\Users\ogc\.ssh' -f $env:SystemDrive
$AuthKeys = Join-Path $ProfilePath 'authorized_keys'
if (!(Test-Path -Path $ProfilePath)) {
    mkdir -Path $ProfilePath
}

$keyUrl = "http://169.254.169.254/latest/meta-data/public-keys/0/openssh-key"

$ErrorActionPreference = 'SilentlyContinue'
Do {
	Start-Sleep 1
	Invoke-WebRequest $keyUrl -UseBasicParsing -OutFile $AuthKeys
} While ( -Not (Test-Path $AuthKeys) )

Restart-Service sshd