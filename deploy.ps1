# ============================================================
# Deploy to Cloudflare Pages (official wrangler tool)
# Usage: open PowerShell in this folder, run  .\deploy.ps1
# Only index.html / manifest.json / icon.svg get deployed.
# ============================================================

$root = $PSScriptRoot

# Node 22 (required by wrangler), already installed locally
$env:PATH = "C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2-6;$env:PATH"

# npm mirror for faster download in CN
$env:NPM_CONFIG_REGISTRY = "https://registry.npmmirror.com"

# Account ID (fixed)
$env:CLOUDFLARE_ACCOUNT_ID = "726a4d97823f76d3a794d804f7c1655d"

if (-not $env:CLOUDFLARE_API_TOKEN) {
    Write-Host "CLOUDFLARE_API_TOKEN not set. Run first:" -ForegroundColor Yellow
    Write-Host '  $env:CLOUDFLARE_API_TOKEN = "your-token"'
    exit 1
}

# Build a clean dist/ folder with only the 3 site files
$dist = Join-Path $root "dist"
if (Test-Path $dist) { Remove-Item $dist -Recurse -Force }
New-Item -ItemType Directory $dist | Out-Null
Copy-Item (Join-Path $root "index.html") $dist
Copy-Item (Join-Path $root "manifest.json") $dist
Copy-Item (Join-Path $root "icon.svg") $dist
Copy-Item (Join-Path $root "icon-180.png") $dist
Copy-Item (Join-Path $root "icon-192.png") $dist
Copy-Item (Join-Path $root "icon-512.png") $dist

Write-Host "Deploying dist/ ..." -ForegroundColor Cyan
npx --yes wrangler@latest pages deploy $dist --project-name jiafen --branch main --commit-dirty true

Write-Host ""
Write-Host "Done. Open https://jiafen-era.pages.dev (Ctrl+F5 to force refresh)" -ForegroundColor Green
