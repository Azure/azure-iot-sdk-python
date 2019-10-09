#$WhatIfPreference = $true

function Install-Dependencies {
    pip install bumpversion
    pip install wheel
}

function Update-Version($part, $file) {
    bumpversion.exe $part --config-file .\.bumpverion.cfg --allow-dirty $file

    if($LASTEXITCODE -ne 0) {
        throw "Bumpversion failed to increment part '$part' for '$file' with code ($LASTEXITCODE)"
    }
}

function Invoke-Python {
    python setup.py sdist
    python setup.py bdist_wheel
}

function Build {

    Write-Output "Python version is '$(python.exe --version)'"

    $sourceFiles = $env:sources  # sdk repo top folder
    $dist = $env:dist  # release artifacts top folder

    # hashtable key is package folder name in repository root

    $packages = @{ } # TODO add new packages to this hashtable

    $packages["azure-iot-device"] = [PSCustomObject]@{
        File = "azure\iot\device\constant.py"
        Version = $env:device_version_part
    }

    $packages["azure-iot-nspkg"] = [PSCustomObject]@{
        File = "setup.py"
        Version = $env:nspkg_version_part
    }

    $packages["azure-iot-hub"] = [PSCustomObject]@{
        File = "azure\iot\hub\constant.py"
        Version = $env:hub_version_part
    }

    New-Item $dist -Force -ItemType Directory
    Install-Dependencies

    foreach ($key in $packages.Keys) {

        $part = $packages[$key].Version

        if ($part -and $part -ne "") {

            $packageFolder = $(Join-Path $sourceFiles $key)

            Write-Output "Increment '$part' version for '$key' "
            Write-Output "Package folder: $packageFolder"
            
            $file = Join-Path $packageFolder $packages[$key].File
            Set-Location $packageFolder
            Update-Version $part $file
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