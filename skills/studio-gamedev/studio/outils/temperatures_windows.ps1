# Studio gamedev : températures du processeur et des disques pour « Santé du PC » (Windows).
# Lancé par le serveur du studio SEULEMENT après le clic « Activer » de l'utilisateur, avec élévation : Windows demande « Oui ».
#   -Action Installer    : crée %ProgramData%\StudioGamedev (écriture réservée à SYSTEM et aux administrateurs),
#                          y pose releve.ps1 et crée la tâche planifiée « Studio gamedev - temperatures » (compte SYSTEM,
#                          toutes les 2 minutes) qui écrit %ProgramData%\StudioGamedev\temperatures.json.
#   -Action Desinstaller : retire la tâche et le dossier.
# Rien d'autre n'est modifié. Disques : Get-StorageReliabilityCounter. Processeur : LibreHardwareMonitor ou
# OpenHardwareMonitor s'ils tournent (capteur « CPU Package »), sinon zone thermique ACPI (le studio la dit
# « non fiable » si elle est figée), sinon rien (« non disponible »).
param([ValidateSet('Installer', 'Desinstaller')][string]$Action = 'Installer')
$ErrorActionPreference = 'Stop'
$nomTache = 'Studio gamedev - temperatures'
$dossier = Join-Path $env:ProgramData 'StudioGamedev'

if ($Action -eq 'Desinstaller') {
    Unregister-ScheduledTask -TaskName $nomTache -Confirm:$false -ErrorAction SilentlyContinue
    if (Test-Path $dossier) { Remove-Item -Recurse -Force $dossier }
    exit 0
}

# un dossier créé à l'avance par un compte sans droits n'est jamais réutilisé : on le recrée (il ne contient que nos fichiers)
if (Test-Path $dossier) { Remove-Item -Recurse -Force $dossier }
New-Item -ItemType Directory -Force $dossier | Out-Null
& icacls.exe $dossier /setowner '*S-1-5-32-544' | Out-Null
# droits : SYSTEM et Administrateurs en contrôle total, Utilisateurs en lecture seule (SID : indépendant de la langue)
& icacls.exe $dossier /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-32-545:(OI)(CI)RX' | Out-Null
if ($LASTEXITCODE -ne 0) { throw "icacls : code $LASTEXITCODE" }

$releve = Join-Path $dossier 'releve.ps1'
@'
$ErrorActionPreference = 'SilentlyContinue'
$sortie = @{}
foreach ($pd in Get-PhysicalDisk) {
    $t = $null
    try { $t = ($pd | Get-StorageReliabilityCounter).Temperature } catch { }
    if ($t -eq 0) { $t = $null }
    foreach ($part in (Get-Partition -DiskNumber $pd.DeviceId | Where-Object DriveLetter)) {
        $sortie[[string]$part.DriveLetter] = @{ temp = $t; disque = $pd.FriendlyName }
    }
}
$cpu = $null
foreach ($ns in 'root/LibreHardwareMonitor', 'root/OpenHardwareMonitor') {
    try {
        $s = Get-CimInstance -Namespace $ns -ClassName Sensor -ErrorAction Stop |
            Where-Object { $_.SensorType -eq 'Temperature' -and $_.Name -match 'CPU Package|Core Max|Tctl|Tdie' } |
            Sort-Object Value -Descending | Select-Object -First 1
        if ($s) { $cpu = @{ c = [math]::Round([double]$s.Value, 1); source = ($ns -replace 'root/', '') }; break }
    } catch { }
}
if (-not $cpu) {
    try {
        $z = Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction Stop |
            Sort-Object CurrentTemperature -Descending | Select-Object -First 1
        if ($z) { $cpu = @{ c = [math]::Round($z.CurrentTemperature / 10 - 273.15, 1); source = 'acpi' } }
    } catch { }
}
$json = @{ maj = (Get-Date -Format s); disques = $sortie; cpu = $cpu } | ConvertTo-Json -Depth 4
$f = Join-Path $env:ProgramData 'StudioGamedev\temperatures.json'
[IO.File]::WriteAllText($f + '.tmp', $json, [Text.UTF8Encoding]::new($false))
Move-Item -Force ($f + '.tmp') $f
'@ | Set-Content -Path $releve -Encoding UTF8

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$releve`""
$maintenant = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 2)
$demarrage = New-ScheduledTaskTrigger -AtStartup           # après un redémarrage : même répétition toutes les 2 min
$demarrage.Repetition = $maintenant.Repetition
$declencheurs = @($maintenant, $demarrage)
$compte = New-ScheduledTaskPrincipal -UserId 'S-1-5-18' -LogonType ServiceAccount -RunLevel Highest
$reglages = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $nomTache -Action $action -Trigger $declencheurs -Principal $compte -Settings $reglages -Force | Out-Null
Start-ScheduledTask -TaskName $nomTache
exit 0
