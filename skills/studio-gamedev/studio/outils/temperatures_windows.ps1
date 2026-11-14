# Studio gamedev : températures du processeur et des disques pour « Santé du PC » (Windows PowerShell 5.1).
# Lancé par le serveur du studio SEULEMENT après le clic « Activer » de l'utilisateur, avec élévation : Windows demande « Oui ».
#   -Action Installer    : crée %ProgramData%\StudioGamedev (écriture réservée à SYSTEM et aux administrateurs),
#                          y pose releve.ps1 et crée la tâche planifiée « Studio gamedev - temperatures » (compte SYSTEM,
#                          toutes les 2 minutes) qui écrit %ProgramData%\StudioGamedev\temperatures.json.
#   -Action Desinstaller : retire la tâche et le dossier.
#   -Journal <fichier>   : le résultat (réussite, ou cause de l'échec, étape et message de Windows) y est écrit en JSON ;
#                          le studio le montre sur la fiche « Santé du PC ».
#   -EssaiASec           : sans élévation et sans rien modifier : prépare le relevé et la tâche en mémoire, les fait
#                          valider par le planificateur (validation seule, rien n'est enregistré) et écrit le journal.
# Rien d'autre n'est modifié et rien n'est téléchargé. Disques : Get-StorageReliabilityCounter. Processeur :
# LibreHardwareMonitor ou OpenHardwareMonitor s'ils tournent (capteur « CPU Package »), sinon zone thermique ACPI
# (le studio la dit « non fiable » si elle est figée), sinon rien (« non disponible »).
# Attention : PowerShell ne distingue pas les majuscules. Aucune variable ne doit s'appeler $action : le paramètre
# $Action a un ValidateSet, y ranger autre chose arrête le script (c'était l'échec « code 1 » du 14/11).
param(
    [ValidateSet('Installer', 'Desinstaller')][string]$Action = 'Installer',
    [string]$Journal = '',
    [switch]$EssaiASec
)
$ErrorActionPreference = 'Stop'
$nomTache = 'Studio gamedev - temperatures'
$dossier = Join-Path $env:ProgramData 'StudioGamedev'
$script:etape = 'depart'

function Ecrire-Journal([hashtable]$h) {
    if (-not $Journal) { return }
    try {
        $h['quand'] = (Get-Date -Format s); $h['action'] = $Action; $h['essai_a_sec'] = [bool]$EssaiASec
        $h['powershell'] = $PSVersionTable.PSVersion.ToString()
        [IO.File]::WriteAllText($Journal, ($h | ConvertTo-Json -Depth 4), (New-Object Text.UTF8Encoding($false)))
    } catch { }
}

function Est-Admin {
    $p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

$texteReleve = @'
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
[IO.File]::WriteAllText($f + '.tmp', $json, (New-Object Text.UTF8Encoding($false)))
Move-Item -Force ($f + '.tmp') $f
'@

function Nouvelle-Tache([string]$releve) {
    $tacheAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$releve`""
    $maintenant = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 2)
    $demarrage = New-ScheduledTaskTrigger -AtStartup           # après un redémarrage : même répétition toutes les 2 min
    $demarrage.Repetition = $maintenant.Repetition
    $compte = New-ScheduledTaskPrincipal -UserId 'S-1-5-18' -LogonType ServiceAccount -RunLevel Highest
    $reglages = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
    return @{ Action = $tacheAction; Trigger = @($maintenant, $demarrage); Principal = $compte; Settings = $reglages }
}

try {
    if ($EssaiASec) {
        # rien n'est créé : relevé analysé, tâche construite et validée par le planificateur sans être enregistrée
        $script:etape = 'releve'
        $null = [ScriptBlock]::Create($texteReleve)
        $script:etape = 'tache'
        $t = Nouvelle-Tache (Join-Path $dossier 'releve.ps1')
        $null = New-ScheduledTask @t
        $script:etape = 'validation'
        $svc = New-Object -ComObject Schedule.Service; $svc.Connect()
        $def = $svc.NewTask(0)
        $def.Principal.UserId = 'S-1-5-18'; $def.Principal.LogonType = 5; $def.Principal.RunLevel = 1
        $tr = $def.Triggers.Create(1); $tr.StartBoundary = (Get-Date -Format s); $tr.Repetition.Interval = 'PT2M'
        $tb = $def.Triggers.Create(8); $tb.Repetition.Interval = 'PT2M'
        $ex = $def.Actions.Create(0); $ex.Path = 'powershell.exe'; $ex.Arguments = '-NoProfile -File x.ps1'
        $null = $svc.GetFolder('\').RegisterTaskDefinition($nomTache, $def, 1, $null, $null, 5)   # 1 = validation seule
        Ecrire-Journal @{ ok = $true; etape = 'fini'; cause = 'essai'; message = "essai à sec réussi : rien n'a été modifié"; admin = (Est-Admin) }
        exit 0
    }

    $script:etape = 'droits'
    if (-not (Est-Admin)) { throw (New-Object System.UnauthorizedAccessException("PowerShell n'a pas les droits d'administrateur")) }

    if ($Action -eq 'Desinstaller') {
        $script:etape = 'desinstallation'
        Unregister-ScheduledTask -TaskName $nomTache -Confirm:$false -ErrorAction SilentlyContinue
        if (Test-Path $dossier) { Remove-Item -Recurse -Force $dossier }
        Ecrire-Journal @{ ok = $true; etape = 'fini'; message = 'tâche et dossier retirés' }
        exit 0
    }

    # un dossier créé à l'avance par un compte sans droits n'est jamais réutilisé : on le recrée (il ne contient que nos fichiers)
    $script:etape = 'dossier'
    Unregister-ScheduledTask -TaskName $nomTache -Confirm:$false -ErrorAction SilentlyContinue
    if (Test-Path $dossier) { Remove-Item -Recurse -Force $dossier }
    New-Item -ItemType Directory -Force $dossier | Out-Null
    & icacls.exe $dossier /setowner '*S-1-5-32-544' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "icacls /setowner : code $LASTEXITCODE" }
    # droits : SYSTEM et Administrateurs en contrôle total, Utilisateurs en lecture seule (SID : indépendant de la langue)
    & icacls.exe $dossier /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-32-545:(OI)(CI)RX' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "icacls : code $LASTEXITCODE" }

    $script:etape = 'releve'
    $releve = Join-Path $dossier 'releve.ps1'
    $texteReleve | Set-Content -Path $releve -Encoding UTF8

    $script:etape = 'tache'
    $t = Nouvelle-Tache $releve
    Register-ScheduledTask -TaskName $nomTache @t -Force | Out-Null

    $script:etape = 'premier_releve'
    Start-ScheduledTask -TaskName $nomTache
    $sortie = Join-Path $dossier 'temperatures.json'
    $fin = (Get-Date).AddSeconds(45)
    while (-not (Test-Path $sortie) -and (Get-Date) -lt $fin) { Start-Sleep -Milliseconds 500 }
    if (Test-Path $sortie) {
        Ecrire-Journal @{ ok = $true; etape = 'fini'; message = 'tâche créée, premier relevé écrit' }
    } else {
        $info = Get-ScheduledTaskInfo -TaskName $nomTache -ErrorAction SilentlyContinue
        $dernier = if ($info) { $info.LastTaskResult } else { '?' }
        Ecrire-Journal @{ ok = $true; etape = 'premier_releve'; message = "tâche créée ; premier relevé pas encore écrit (dernier résultat de la tâche : $dernier)" }
    }
    exit 0
} catch {
    $e = $_.Exception
    $msg = $e.Message
    $refus = ($e -is [System.UnauthorizedAccessException]) -or ($msg -match 'acc[eè]s refus|access is denied|0x80070005')
    $cause = switch ($script:etape) {
        'droits' { 'droits_absents' }
        'dossier' { if ($refus) { 'windows_refuse' } else { 'dossier' } }
        'releve' { 'releve' }
        'tache' { if ($refus) { 'windows_refuse' } else { 'tache_planifiee' } }
        'premier_releve' { 'premier_releve' }
        'validation' { 'tache_planifiee' }
        default { 'script' }
    }
    Ecrire-Journal @{ ok = $false; etape = $script:etape; cause = $cause; message = $msg; ligne = $_.InvocationInfo.ScriptLineNumber }
    exit 3
}
