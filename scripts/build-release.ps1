#$WhatIfPreference = $true

function Install-Dependencies {
    pip install bumpversion
    pip install wheel
}

function Update-Version($part, $file) {
    bumpversion $part --allow-dirty $file

    if($LASTEXITCODE -ne 0) {
        throw "Bumpversion failed to increment part '$part' for '$file' with code ($LASTEXITCODE)"
    }
}

function Invoke-Python {
    python setup.py sdist
    python setup.py bdist_wheel
}

function Build {

    Write-Output "Python version is '$(python --version)'"

    $sourceFiles = $env:sources  # sdk repo top folder
    $dist = $env:dist  # release artifacts top folder

    $package = [PSCustomObject]@{
        File = "azure-iot-device\azure\iot\device\constant.py"
        Version = $env:device_version_part
    }

    New-Item $dist -Force -ItemType Directory
    Install-Dependencies


    $part = $package.Version

    if ($part -and $part -ne "") {

        Write-Output "Increment '$part' version for '$key' "
        
        Set-Location $sourceFiles
        Update-Version $part $package.File
        Invoke-Python

        $distfld = Join-Path $sourceFiles "dist"
        $files = Get-ChildItem $distfld

        if ($files.Count -lt 1) {
            throw "$key : expected to find release artifacts"
        }
    }
    else {
        Write-Output "Skipping '$key'"
    }
}