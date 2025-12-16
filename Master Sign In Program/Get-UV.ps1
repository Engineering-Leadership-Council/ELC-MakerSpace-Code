<#
Downloads just uv.exe (portable) for Windows.
Works on PowerShell 5.1+ (no PS7 features).
#>

param(
  [string] $Version = "latest",                       # e.g., v0.4.21 or "latest"
  [ValidateSet("x86_64","aarch64")]
  [string] $Arch = ($(if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "aarch64" } else { "x86_64" })),
  [string] $Dest = ".",                               # folder to place uv.exe
  [switch] $Quiet
)

# --- Setup ---
$ErrorActionPreference = "Stop"

function Write-Info([string]$msg) {
  if (-not $Quiet) { Write-Host $msg }
}

# Ensure TLS 1.2 for GitHub downloads on older Windows
try {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
} catch { }

# Resolve/create destination directory (PS5.1-safe)
try {
  $resolved = Resolve-Path -LiteralPath $Dest -ErrorAction Stop
  $DestPath = $resolved.ProviderPath
} catch {
  # Create then resolve
  New-Item -ItemType Directory -Path $Dest -Force | Out-Null
  $DestPath = (Resolve-Path -LiteralPath $Dest).ProviderPath
}

$zipPath = Join-Path $env:TEMP "uv_portable.zip"
$uvPath  = Join-Path $DestPath "uv.exe"

try {
  # Resolve version tag
  if ($Version -eq "latest") {
    Write-Info "[INFO] Resolving latest release tag..."
    try {
      $headers = @{ "User-Agent" = "ELC-UV-Getter" }
      $latest  = Invoke-RestMethod -Uri "https://api.github.com/repos/astral-sh/uv/releases/latest" -Headers $headers
      $tag     = $latest.tag_name
    } catch {
      Write-Info "[WARN] Could not query GitHub API; falling back to v0.4.21."
      $tag = "v0.4.21"
    }
  } else {
    $tag = $Version
  }

  $url = "https://github.com/astral-sh/uv/releases/download/$tag/uv-$Arch-pc-windows-msvc.zip"
  Write-Info "[INFO] Downloading: $url"
  if (Test-Path $zipPath) { Remove-Item $zipPath -Force -ErrorAction SilentlyContinue }

  # Download with IWR; fallback to WebClient; final fallback certutil via cmd
  $downloaded = $false
  try {
    Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing -Headers @{ "User-Agent" = "ELC-UV-Getter" }
    $downloaded = Test-Path $zipPath
  } catch {
    Write-Info "[WARN] Invoke-WebRequest failed, trying WebClient..."
    try {
      $wc = New-Object System.Net.WebClient
      $wc.Headers.Add("User-Agent","ELC-UV-Getter")
      $wc.DownloadFile($url, $zipPath)
      $downloaded = Test-Path $zipPath
    } catch {
      Write-Info "[WARN] WebClient failed, trying certutil..."
      cmd /c certutil -urlcache -split -f "$url" "$zipPath" | Out-Null
      $downloaded = Test-Path $zipPath
    }
  }

  if (-not $downloaded) {
    throw "Download failed: $url"
  }

  Write-Info "[INFO] Extracting uv.exe to: $DestPath"
  if (Test-Path $uvPath) { Remove-Item $uvPath -Force -ErrorAction SilentlyContinue }

  $extracted = $false
  try {
    Expand-Archive -Path $zipPath -DestinationPath $DestPath -Force
    $extracted = $true
  } catch {
    Write-Info "[WARN] Expand-Archive failed, trying tar..."
    $tar = (Get-Command tar -ErrorAction SilentlyContinue)
    if ($tar) {
      & $tar.Source -xf $zipPath -C $DestPath
      $extracted = $true
    } else {
      throw "No extractor available (Expand-Archive/tar)."
    }
  }

  if (-not (Test-Path $uvPath)) {
    throw "uv.exe was not found after extraction."
  }

  Write-Info "[OK] uv.exe ready: $uvPath"
  exit 0
}
catch {
  Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}
finally {
  if (Test-Path $zipPath) { Remove-Item $zipPath -Force -ErrorAction SilentlyContinue }
}
