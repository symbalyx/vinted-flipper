# Installe le monde "Site B" et ses mods dans l'instance CurseForge.
# Usage : clic droit > "Executer avec PowerShell", ou dans PowerShell :
#   powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\installer_site_b.ps1"
# Avant : telecharger site_b_monde.zip et spinosaure-0.4.0.jar dans le dossier Telechargements.

$Instance = "C:\Users\maxva\curseforge\minecraft\Instances\cave dweller sandbox"
$Dl = Join-Path $env:USERPROFILE "Downloads"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'

if (-not (Test-Path $Instance)) { Write-Host "Instance introuvable : $Instance" -ForegroundColor Red; exit 1 }
$Mods  = Join-Path $Instance "mods"
$Saves = Join-Path $Instance "saves"
New-Item -ItemType Directory -Force -Path $Mods, $Saves | Out-Null

# ---------------------------------------------------------------- le monde
$Zip = Join-Path $Dl "site_b_monde.zip"
if (-not (Test-Path $Zip)) { Write-Host "Il manque $Zip" -ForegroundColor Red; exit 1 }
$Monde = Join-Path $Saves "Site B"
if (Test-Path $Monde) {
    $Sauve = "$Monde (ancien $(Get-Date -Format yyyyMMdd-HHmm))"
    Rename-Item $Monde $Sauve
    Write-Host "Ancien monde garde sous : $Sauve"
}
Expand-Archive -Path $Zip -DestinationPath $Saves -Force
Write-Host "Monde installe : $Monde" -ForegroundColor Green

# ---------------------------------------------------------------- le mod spinosaure
$Spino = Get-ChildItem $Dl -Filter "spinosaure*.jar" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($Spino) {
    Get-ChildItem $Mods -Filter "spinosaure*.jar" -ErrorAction SilentlyContinue | Remove-Item     # l'ancien, seulement maintenant
    Copy-Item $Spino.FullName (Join-Path $Mods "spinosaure-0.4.0.jar")
    Write-Host "Mod spinosaure : $($Spino.Name)" -ForegroundColor Green
}
else { Write-Host "spinosaure-0.4.0.jar introuvable dans Telechargements" -ForegroundColor Red }

# ---------------------------------------------------------------- les autres mods (Modrinth, Forge 1.20.1)
$Liste = @(
  @{ n = "BiomesOPlenty";     f = "BiomesOPlenty-forge-1.20.1-19.0.0.96.jar";   u = "https://cdn.modrinth.com/data/HXF82T3G/versions/jxUqRzSD/BiomesOPlenty-forge-1.20.1-19.0.0.96.jar" },
  @{ n = "TerraBlender";      f = "TerraBlender-forge-1.20.1-3.0.1.10.jar";     u = "https://cdn.modrinth.com/data/kkmrDlKT/versions/zGconCHG/TerraBlender-forge-1.20.1-3.0.1.10.jar" },
  @{ n = "GlitchCore";        f = "GlitchCore-forge-1.20.1-0.0.1.1.jar";        u = "https://cdn.modrinth.com/data/s3dmwKy5/versions/pYPZ5MNI/GlitchCore-forge-1.20.1-0.0.1.1.jar" },
  @{ n = "geckolib";          f = "geckolib-forge-1.20.1-4.8.4.jar";            u = "https://cdn.modrinth.com/data/8BmcQJ2H/versions/aC5KMoNg/geckolib-forge-1.20.1-4.8.4.jar" },
  @{ n = "zipline";           f = "zipline-forge-1.20.1-1.3.0.jar";             u = "https://cdn.modrinth.com/data/C1MoWQlb/versions/AZLF926r/zipline-forge-1.20.1-1.3.0.jar" },
  @{ n = "connectiblechains"; f = "connectiblechains-forge-1.20.1-2.2.5.jar";   u = "https://cdn.modrinth.com/data/5pzBXDS3/versions/nwJ6Xxt3/connectiblechains-forge-1.20.1-2.2.5.jar" },
  @{ n = "cloth-config";      f = "cloth-config-11.1.136-forge.jar";            u = "https://cdn.modrinth.com/data/9s6osm5g/versions/t8TXrZvZ/cloth-config-11.1.136-forge.jar" },
  @{ n = "ParCool";           f = "ParCool-1.20.1-4.0.0.5.jar";                 u = "https://cdn.modrinth.com/data/Fsvx2bdR/versions/eDWn3zad/ParCool-1.20.1-4.0.0.5.jar" }
)
foreach ($m in $Liste) {
    $deja = Get-ChildItem $Mods -Filter "$($m.n)*.jar" -ErrorAction SilentlyContinue
    if ($deja) { Write-Host "Deja present, on garde : $($deja.Name -join ', ')"; continue }
    try {
        Invoke-WebRequest -Uri $m.u -OutFile (Join-Path $Mods $m.f) -UseBasicParsing
        Write-Host "Telecharge : $($m.f)" -ForegroundColor Green
    } catch { Write-Host "Echec du telechargement : $($m.f) ($($_.Exception.Message))" -ForegroundColor Red }
}

Write-Host ""
Write-Host "Mods dans l'instance :"
Get-ChildItem $Mods -Filter *.jar | ForEach-Object { Write-Host "  $($_.Name)" }
Write-Host ""
Write-Host "Forge : 1.20.1-47.2.30 minimum (tyroliennes) ; 47.4.23 si ParCool 4.x est installe." -ForegroundColor Yellow
Write-Host "CurseForge > profil > ... > Profile Options > Modloader pour changer de version." -ForegroundColor Yellow
Write-Host "Puis Jouer > Solo > 'Site B'."
