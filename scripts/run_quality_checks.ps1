$ErrorActionPreference = "Stop"

Write-Host "1/3 Python compile check" -ForegroundColor Cyan
python -m py_compile `
  integration\python_api\app.py `
  integration\python_api\test_auth_api.py `
  engenharia_automacao\app\auth.py

Write-Host "2/3 Auth API tests" -ForegroundColor Cyan
python -m pytest integration\python_api\test_auth_api.py -p no:cacheprovider

Write-Host "3/3 Frontend type check" -ForegroundColor Cyan
Push-Location frontend
try {
  cmd /c npx tsc --noEmit
}
finally {
  Pop-Location
}

Write-Host "Quality checks passed." -ForegroundColor Green
