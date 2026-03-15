Write-Host "Starting Jekyll local preview..."

# Stop on errors
$ErrorActionPreference = "Stop"

try {

    # Optional: choose config
    $config = "_config.yml,_config_dev.yml"

    # Build once (sanity check)
    Write-Host "Running initial Jekyll build..."
    bundle exec jekyll build --config $config


    # ------------------------------------------------
    # Detect Python
    # ------------------------------------------------

    $pythonCmd = $null

    foreach ($cmd in @("python","python3","py")) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            $pythonCmd = $cmd
            break
        }
    }

    if (-not $pythonCmd) {
        throw "Python not found. Install Python or add it to PATH."
    }

    Write-Host "Using Python command: $pythonCmd"


    # ------------------------------------------------
    # Start save server
    # ------------------------------------------------

    Write-Host "Starting save server..."

    $pythonProcess = Start-Process `
        -FilePath $pythonCmd `
        -ArgumentList "save_server.py" `
        -PassThru `
        -NoNewWindow


    # ------------------------------------------------
    # Launch browser
    # ------------------------------------------------

    $firefox = "C:\Program Files\Mozilla Firefox\firefox.exe"

    $url = "http://127.0.0.1:4000/Gallery/dev/"

    Start-Process $firefox -ArgumentList "-P `"Pdev`" -no-remote $url"


    # ------------------------------------------------
    # Start Jekyll server
    # ------------------------------------------------

    Write-Host "Starting Jekyll server..."

    $jekyllProcess = Start-Process `
        -FilePath "bundle" `
        -ArgumentList "exec jekyll serve --config $config --livereload" `
        -PassThru `
        -NoNewWindow


    Write-Host ""
    Write-Host "Development environment running."
    Write-Host "Press CTRL+C to stop."
    Write-Host ""


    # Monitor processes
    while ($true) {

        Start-Sleep -Seconds 1

        if ($pythonProcess.HasExited -or $jekyllProcess.HasExited) {
            break
        }

    }

}
finally {

    Write-Host ""
    Write-Host "Shutting down services..."

    if ($pythonProcess -and !$pythonProcess.HasExited) {
        Stop-Process -Id $pythonProcess.Id -Force
        Write-Host "Save server stopped."
    }

    if ($jekyllProcess -and !$jekyllProcess.HasExited) {
        Stop-Process -Id $jekyllProcess.Id -Force
        Write-Host "Jekyll server stopped."
    }

    Write-Host "Environment closed."
}
