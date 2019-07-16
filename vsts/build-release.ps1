$sourceFiles = $env:sources  # sdk repo top folder
$dist = $env:dist  # release artifacts top folder

New-Item $dist -Force -ItemType Directory

pip install bumpversion
pip install wheel

# hashset key is package folder name in repo

$packages = @{ }
$packages["azure-iot-device"] = $env:device_version_part
$packages["azure-iot-nspkg"] = $env:nspkg_version_part

foreach ($key in $packages.Keys) {

    $part = $packages[$key]

    Write-Host "package '$key' version '$part'"

    if ($part -ne "") {
        Write-Host "version part: $part"

        $packageFolder = $(Join-Path $sourceFiles $key)

        Write-Host "package folder: $packageFolder"

        Set-Location $packageFolder
        bumpversion.exe $part --config-file .\.bumpverion.cfg --allow-dirty .\setup.py
        
        python setup.py sdist
        python setup.py bdist_wheel

        $distfld = Join-Path $packageFolder "dist"
        $files = Get-ChildItem $distfld

        if ($files.Count -lt 1) {
            throw "$key : expected to find release artifacts"
        }

        $packagefld = Join-Path $dist $key
        New-Item $packagefld -Force -ItemType Directory

        foreach ($file in $files) {
            Copy-Item $file.FullName $(Join-Path $packagefld $file.Name)
        }
    } else {
        Write-Host "no version bump for package '$key'"
    }
}