$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$servicePath = Join-Path $repoRoot 'pc-hardware-service'

# Spring Boot 3 requires Java 17. Prefer the configured JDK when it is suitable,
# otherwise use an installed Java 17 JDK without changing the user's settings.
$configuredJavaHome = $env:JAVA_HOME
$java17Home = $null
if ($configuredJavaHome -and (Test-Path (Join-Path $configuredJavaHome 'bin\javac.exe'))) {
    $versionText = & (Join-Path $configuredJavaHome 'bin\java.exe') -version 2>&1 | Out-String
    if ($versionText -match 'version "17\.') {
        $java17Home = $configuredJavaHome
    }
}
if (-not $java17Home) {
    $java17Home = Get-ChildItem 'C:\Program Files\Java' -Directory -ErrorAction SilentlyContinue |
        Where-Object Name -Match '^jdk-17' |
        Sort-Object Name -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $java17Home) {
    throw 'PC 模拟硬件服务需要 Java 17。请安装 JDK 17 并设置 JAVA_HOME。'
}

$env:JAVA_HOME = $java17Home
$env:Path = "$(Join-Path $java17Home 'bin');$env:Path"
Push-Location $servicePath
try {
    mvn spring-boot:run
}
finally {
    Pop-Location
}
