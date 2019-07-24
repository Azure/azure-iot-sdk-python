#$WhatIfPreference = $true

function Install-Dependencies {
    pip install bumpversion
    pip install wheel
}

function Update-Version($part) {
    bumpversion.exe $part --config-file .\.bumpverion.cfg --allow-dirty .\setup.py
}

function Invoke-Python {
    python setup.py sdist
    python setup.py bdist_wheel
}

function Build {

    Write-Output "Python version is '$(python.exe --version)'"

    $sourceFiles = $env:sources  # sdk repo top folder
    $dist = $env:dist  # release artifacts top folder

    # hashset key is package folder name in repo

    $packages = @{ }
    $packages["azure-iot-device"] = $env:device_version_part
    $packages["azure-iot-nspkg"] = $env:nspkg_version_part
    # TODO add new packages to this list

    New-Item $dist -Force -ItemType Directory
    Install-Dependencies

    foreach ($key in $packages.Keys) {

        $part = $packages[$key]

        if ($part -and $part -ne "") {

            $packageFolder = $(Join-Path $sourceFiles $key)

            Write-Output "Increment '$part' version for '$key' "
            Write-Output "Package folder: $packageFolder"
            
            Set-Location $packageFolder
            Update-Version $part
            Invoke-Python

            $distfld = Join-Path $packageFolder "dist"
            $files = Get-ChildItem $distfld

            if ($files.Count -lt 1) {
                throw "$key : expected to find release artifacts"
            }

            $packagefld = Join-Path $dist $key
            New-Item $packagefld -Force -ItemType Directory
            Write-Output "Copying ($($files.Count)) package files to output folder"

            foreach ($file in $files) {

                $target = $(Join-Path $packagefld $file.Name)
                Write-Output "$($file.FullName) >> $target"
                Copy-Item $file.FullName $target
            }
        }
        else {
            Write-Output "Skipping '$key'"
        }
    }
}