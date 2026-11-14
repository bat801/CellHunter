[CmdletBinding()]
param(
    [ValidateSet('Build', 'Publish')]
    [string]$Task = 'Build',

    [ValidateSet('Debug', 'Release')]
    [string]$Configuration = 'Release',

    [string]$Runtime = 'win-x64',

    [string]$Output = ''
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$cacheDir = Join-Path $root '.cache'
$tempDir = Join-Path $cacheDir 'temp'
$project = Join-Path $root 'src\CellHunter.Desktop\CellHunter.Desktop\CellHunter.Desktop.csproj'

# Keep MSBuild, NuGet, and package-download artifacts inside the workspace.
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
$env:TMP = $tempDir
$env:TEMP = $tempDir
$env:NUGET_HTTP_CACHE_PATH = Join-Path $cacheDir 'nuget\http-cache'
$env:NUGET_PACKAGES = Join-Path $cacheDir 'nuget\packages'

switch ($Task) {
    'Build' {
        dotnet build $project --configuration $Configuration
    }
    'Publish' {
        if ([string]::IsNullOrWhiteSpace($Output)) {
            $Output = Join-Path $cacheDir 'publish'
        }
        dotnet publish $project `
            --configuration $Configuration `
            --runtime $Runtime `
            --self-contained true `
            --output $Output
    }
}
