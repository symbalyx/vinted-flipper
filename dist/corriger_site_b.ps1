# Corrige l'installation de "Site B" dans l'instance CurseForge :
#  - remet le mod spinosaure (le premier script l'avait retire sans trouver le nouveau)
#  - affiche la version de Forge de l'instance et dit si elle suffit
# Usage (Minecraft ferme) :
#   powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\corriger_site_b.ps1"

$Instance = "C:\Users\maxva\curseforge\minecraft\Instances\cave dweller sandbox"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'
$Mods = Join-Path $Instance "mods"

# ---------------------------------------------------------------- 1. le mod spinosaure
$ou = @((Join-Path $env:USERPROFILE "Downloads"), (Join-Path $env:USERPROFILE "Desktop"), (Join-Path $env:USERPROFILE "OneDrive\Bureau"),
        (Join-Path $env:USERPROFILE "OneDrive\Desktop"), (Join-Path $env:USERPROFILE "Documents"))
$Spino = $null
foreach ($d in $ou) {
    if (Test-Path $d) {
        $Spino = Get-ChildItem $d -Recurse -Depth 2 -Filter "spinosaure*.jar" -ErrorAction SilentlyContinue |
                 Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($Spino) { break }
    }
}
if ($Spino) {
    Copy-Item $Spino.FullName (Join-Path $Mods "spinosaure-0.4.0.jar") -Force
    Write-Host "Mod spinosaure remis : $($Spino.FullName)" -ForegroundColor Green
} else {
    Write-Host "spinosaure-0.4.0.jar introuvable (Telechargements, Bureau, Documents)." -ForegroundColor Red
    Write-Host "Telecharge-le depuis la conversation, puis relance ce script." -ForegroundColor Red
}

# ---------------------------------------------------------------- 3. Forge
$json = Join-Path $Instance "minecraftinstance.json"
if (Test-Path $json) {
    $inst = Get-Content $json -Raw | ConvertFrom-Json
    $nom = $inst.baseModLoader.name
    Write-Host ""
    Write-Host "Forge de l'instance : $nom"
    if ($nom -match '47\.(\d+)\.(\d+)') {
        $v = [int]$Matches[1] * 1000 + [int]$Matches[2]
        if ($v -ge 2030) { Write-Host "Forge suffit pour les mods de la carte." -ForegroundColor Green }
        else { Write-Host "Forge trop ancien : il faut 1.20.1-47.2.30 ou plus (CurseForge > profil > ... > Profile Options > Modloader)." -ForegroundColor Yellow }
    }
}
Write-Host ""
Write-Host "Mods de la carte presents :"
foreach ($p in "spinosaure", "BiomesOPlenty", "TerraBlender", "GlitchCore", "geckolib", "zipline", "connectiblechains", "cloth-config", "ParCool") {
    $f = Get-ChildItem $Mods -Filter "$p*.jar" -ErrorAction SilentlyContinue
    if ($f) { Write-Host "  OK    $($f.Name -join ', ')" -ForegroundColor Green } else { Write-Host "  MANQUE $p" -ForegroundColor Red }
}
