param(
    [string]$RequirementsFile = "requirements.txt",
    [string]$CondaEnv = "qrproj",
    [string]$PythonExe = $null
)

# Si no se especifica PythonExe, intentar detectar el Python del entorno conda
if (-not $PythonExe) {
    try {
        # Intentar obtener la ruta base de conda
        $condaInfo = & conda info --json 2>$null | ConvertFrom-Json
        $condaBase = $condaInfo.conda_prefix
        
        # Construir la ruta al Python del entorno
        $envPath = Join-Path $condaBase "envs\$CondaEnv\python.exe"
        
        if (Test-Path $envPath) {
            $PythonExe = $envPath
            Write-Host "[OK] Usando Python del entorno conda '$CondaEnv': $PythonExe" -ForegroundColor Green
        } else {
            Write-Warning "No se encontro el entorno conda '$CondaEnv'. Usando 'python' por defecto."
            $PythonExe = "python"
        }
    } catch {
        Write-Warning "No se pudo detectar conda. Usando 'python' por defecto."
        $PythonExe = "python"
    }
}

if (-not (Test-Path $RequirementsFile)) {
    Write-Error "Archivo no encontrado: $RequirementsFile"
    exit 1
}

Write-Host "`n=== Analizando dependencias de: $RequirementsFile ===`n" -ForegroundColor Cyan

# --- Parsear el requirements (ignora comentarios y lineas vacias)
$lines = Get-Content $RequirementsFile -Encoding UTF8 | ForEach-Object { ($_ -split '#')[0].Trim() } | Where-Object { $_ -ne "" }

$pkgs = @()
foreach ($l in $lines) {
    if ($l -match '^\s*([^\s>=<\[]+(?:\[[^\]]+\])?)\s*(>=|==|<=|>|<|~=)?\s*([0-9A-Za-z\.\*]+)?\s*$') {
        $name = $matches[1]
        $op   = if ($matches[2]) { $matches[2] } else { $null }
        $ver  = if ($matches[3]) { $matches[3] } else { $null }

        # Normaliza: quita extras y pasa a minusculas para la busqueda en el mapa
        $baseName = $name -replace '\[.*\]',''
        $baseNameLc = $baseName.ToLower()

        # Mapa de nombres de paquete a nombres de importacion (claves en minusculas)
        $imap = @{
            "opencv-python" = "cv2"
            "opencv"        = "cv2"
            "pyzbar"        = "pyzbar"
            "pillow"        = "PIL"
            "pil"           = "PIL"
            "qrcode"        = "qrcode"
            "numpy"         = "numpy"
            "pyside6"       = "PySide6"
            "sqlalchemy"    = "sqlalchemy"
            "pytest"        = "pytest"
            "pytest-cov"    = "pytest_cov"
            "black"         = "black"
            "flake8"        = "flake8"
            "mypy"          = "mypy"
        }

        $import_name = if ($imap.ContainsKey($baseNameLc)) { $imap[$baseNameLc] } else { $baseName }

        $pkgs += [pscustomobject]@{
            name = $name
            import_name = $import_name
            op = $op
            ver = $ver
        }
    } else {
        Write-Warning "No se pudo parsear la linea (se ignora): $l"
    }
}

if ($pkgs.Count -eq 0) {
    Write-Error "No se encontraron paquetes validos en $RequirementsFile"
    exit 1
}

$json = $pkgs | ConvertTo-Json -Compress

# --- Script Python mejorado (usa importlib.metadata)
$py = @'
import sys
import json
import importlib

try:
    from importlib.metadata import version, PackageNotFoundError
    use_importlib = True
except ImportError:
    try:
        from pkg_resources import get_distribution, parse_version
        use_importlib = False
    except ImportError:
        print(json.dumps({"error": "No se pudo importar importlib.metadata ni pkg_resources"}), file=sys.stderr)
        sys.exit(1)

def parse_version_str(v):
    """Parseo simple de version para comparaciones"""
    try:
        parts = []
        for part in v.split('.'):
            # Intentar convertir a entero, si no, dejar como string
            try:
                parts.append(int(part))
            except ValueError:
                parts.append(part)
        return tuple(parts)
    except Exception:
        return (v,)

def get_installed_version(pkg_name, import_name):
    """Obtiene la version instalada del paquete"""
    if use_importlib:
        try:
            return version(pkg_name)
        except PackageNotFoundError:
            pass
    else:
        try:
            return get_distribution(pkg_name).version
        except Exception:
            pass
    
    # Fallback: intentar obtener __version__ del modulo
    try:
        mod = importlib.import_module(import_name)
        return getattr(mod, "__version__", None)
    except Exception:
        pass
    
    return None

def cmp_version(installed, op, required):
    """Compara versiones segun el operador"""
    if not op or not required:
        return True
    if installed is None:
        return False
    
    try:
        iv = parse_version_str(installed)
        rv = parse_version_str(required)
        
        if op == "==":
            return iv == rv
        elif op == ">=":
            return iv >= rv
        elif op == "<=":
            return iv <= rv
        elif op == ">":
            return iv > rv
        elif op == "<":
            return iv < rv
        elif op == "~=":
            # Compatible release: ~=1.2.3 permite >=1.2.3,<1.3.0
            return iv >= rv and iv[:len(rv)-1] == rv[:len(rv)-1]
        else:
            return False
    except Exception as e:
        return False

def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Error parsing JSON: {e}"}), file=sys.stderr)
        sys.exit(1)
    
    results = []
    for item in data:
        name = item.get("name", "")
        imp = item.get("import_name", "")
        op = item.get("op")
        ver = item.get("ver")
        
        # Intentar importar el modulo
        can_import = False
        try:
            importlib.import_module(imp)
            can_import = True
        except Exception:
            pass
        
        # Obtener version instalada
        installed_version = get_installed_version(name.replace('[pil]', ''), imp)
        
        # Determinar estado
        if not can_import:
            status = "MISSING"
        elif not installed_version:
            status = "OK (sin version)"
        elif cmp_version(installed_version, op, ver):
            status = "OK"
        else:
            status = "VERSION_MISMATCH"
        
        results.append({
            "name": name,
            "import_name": imp,
            "status": status,
            "installed_version": installed_version,
            "required_op": op if op else "",
            "required_ver": ver if ver else ""
        })
    
    print(json.dumps(results))

if __name__ == "__main__":
    main()
'@

# Escribir a archivo temporal con codificacion UTF-8
$tmp = Join-Path $env:TEMP ("check_deps_" + ([guid]::NewGuid().ToString()) + ".py")
Set-Content -Path $tmp -Value $py -Encoding UTF8

# Ejecutar Python pasando el JSON por stdin
try {
    # Metodo mas simple y confiable
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $PythonExe
    $psi.Arguments = $tmp
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    
    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    $proc.Start() | Out-Null
    
    # Escribir JSON al stdin
    $proc.StandardInput.Write($json)
    $proc.StandardInput.Close()
    
    # Leer salidas
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()
    
    if ($stderr) {
        Write-Warning "Errores de Python:`n$stderr"
    }
    
    if ($proc.ExitCode -ne 0) {
        Write-Error "Python finalizo con codigo de error: $($proc.ExitCode)"
        Remove-Item -Force $tmp -ErrorAction SilentlyContinue
        exit 2
    }
    
} catch {
    Write-Error "Error al ejecutar Python: $_"
    Write-Host "`nPuedes especificar la ruta al Python manualmente:" -ForegroundColor Yellow
    Write-Host "  .\check_deps.ps1 -PythonExe 'C:\ruta\a\tu\python.exe'" -ForegroundColor Yellow
    Remove-Item -Force $tmp -ErrorAction SilentlyContinue
    exit 2
}

# Limpiar archivo temporal
Remove-Item -Force $tmp -ErrorAction SilentlyContinue

# --- Parsear y mostrar resultados
try {
    $res = $stdout | ConvertFrom-Json
    
    # Contar estados
    $ok = ($res | Where-Object { $_.status -like "OK*" }).Count
    $missing = ($res | Where-Object { $_.status -eq "MISSING" }).Count
    $mismatch = ($res | Where-Object { $_.status -eq "VERSION_MISMATCH" }).Count
    
    Write-Host "`n=== RESULTADOS ===" -ForegroundColor Cyan
    Write-Host "Total: $($res.Count) | OK: $ok " -NoNewline -ForegroundColor Green
    Write-Host "| Faltantes: $missing " -NoNewline -ForegroundColor Red
    Write-Host "| Version incorrecta: $mismatch" -ForegroundColor Yellow
    Write-Host ""
    
    # Ordenar: primero MISSING, luego VERSION_MISMATCH, luego OK
    $sortOrder = @{
        "MISSING" = 1
        "VERSION_MISMATCH" = 2
    }
    
    $sorted = $res | Sort-Object { 
        $order = $sortOrder[$_.status]
        if ($order) { $order } else { 3 }
    }
    
    # Mostrar tabla con colores
    foreach ($item in $sorted) {
        $color = switch ($item.status) {
            "MISSING" { "Red" }
            "VERSION_MISMATCH" { "Yellow" }
            default { "Green" }
        }
        
        $reqInfo = if ($item.required_op -and $item.required_ver) {
            "$($item.required_op) $($item.required_ver)"
        } else {
            "cualquiera"
        }
        
        $instInfo = if ($item.installed_version) {
            $item.installed_version
        } else {
            "N/A"
        }
        
        Write-Host ("[{0,-18}]" -f $item.status) -ForegroundColor $color -NoNewline
        Write-Host (" {0,-20} -> {1,-15} | Instalada: {2,-12} | Requerida: {3}" -f $item.name, $item.import_name, $instInfo, $reqInfo)
    }
    
    Write-Host ""
    
    # Mensaje final
    if ($missing -gt 0 -or $mismatch -gt 0) {
        Write-Host "[ADVERTENCIA] Instala las dependencias faltantes con:" -ForegroundColor Yellow
        Write-Host "   pip install -r $RequirementsFile" -ForegroundColor Cyan
        exit 1
    } else {
        Write-Host "[OK] Todas las dependencias estan instaladas correctamente!" -ForegroundColor Green
        exit 0
    }
    
} catch {
    Write-Host "`n[ERROR] Error al parsear la salida de Python." -ForegroundColor Red
    Write-Host "Salida cruda (util para debugging):" -ForegroundColor Yellow
    Write-Host $stdout
    if ($stderr) {
        Write-Host "`nErrores:" -ForegroundColor Red
        Write-Host $stderr
    }
    exit 3
}
