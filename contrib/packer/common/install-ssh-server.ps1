$ErrorActionPreference = "Stop"

write-host "Installing OpenSSH"
choco install openssh -params '"/SSHServerFeature"' -confirm

Stop-Service sshd
$sshd_config = "$($env:ProgramData)\ssh\sshd_config"
(Get-Content $sshd_config).Replace("Match Group administrators", "# Match Group administrators") | Set-Content $sshd_config
(Get-Content $sshd_config).Replace("AuthorizedKeysFile", "# AuthorizedKeysFile") | Set-Content $sshd_config
(Get-Content $sshd_config).Replace("#PubkeyAuthentication yes", "PubkeyAuthentication yes") | Set-Content $sshd_config
Start-Service sshd