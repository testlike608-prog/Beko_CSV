# Build standalone Windows exe with Nuitka (output: build_nuitka\main.dist\BekoVision.exe)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Installing/upgrading Nuitka..." -ForegroundColor Cyan
python -m pip install --upgrade "nuitka>=2.1" ordered-set zstandard

$outDir = "build_nuitka"
$distName = "main.dist"
$dataArgs = @(
    "--include-data-dir=templates=templates",
    "--include-data-dir=static=static",
    "--include-data-dir=CreateProgram=CreateProgram",
    "--include-data-file=config.json=config.json",
    "--include-data-file=time_settings.json=time_settings.json",
    "--include-data-file=logins.csv=logins.csv",
    "--include-data-file=last_db1_settings.txt=last_db1_settings.txt",
    "--include-data-file=last_db2_settings.txt=last_db2_settings.txt",
    "--include-data-file=Station1.csv=Station1.csv",
    "--include-data-file=Station2.csv=Station2.csv",
    "--include-data-file=Station2_dummies.csv=Station2_dummies.csv",
    "--include-data-file=meeserve.ico=meeserve.ico"
)
if (Test-Path "msodbcsql.msi") {
    $dataArgs += "--include-data-file=msodbcsql.msi=msodbcsql.msi"
}

Write-Host "Starting Nuitka (standalone + MinGW64, folder dist, not onefile)..." -ForegroundColor Cyan
python -m nuitka `
    --standalone `
    --mingw64 `
    --disable-ccache `
    --experimental=force-dependencies-pefile `
    --assume-yes-for-downloads `
    --windows-console-mode=force `
    --output-dir=$outDir `
    --output-filename=BekoVision.exe `
    @dataArgs `
    main.py

$exe = Join-Path (Join-Path $outDir $distName) "BekoVision.exe"
if (Test-Path $exe) {
    Write-Host "Done: $exe" -ForegroundColor Green
} else {
    Write-Host "Build finished but exe not found at expected path: $exe" -ForegroundColor Yellow
}
