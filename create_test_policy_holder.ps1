# Create Test Policy Holder
# Run this before testing the frontend

$body = @{
    name = "Test User"
    email = "test@example.com"
    phone = "9876543210"
    date_of_birth = "1990-01-01"
    policy_start_date = "2024-01-01"
} | ConvertTo-Json

Write-Host "Creating test policy holder..." -ForegroundColor Yellow

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/policy-holders/" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body

Write-Host "`n✅ Policy Holder Created Successfully!" -ForegroundColor Green
Write-Host "Policy Holder ID: $($response.policy_holder_id)" -ForegroundColor Cyan
Write-Host "Name: $($response.name)" -ForegroundColor Cyan
Write-Host "Email: $($response.email)" -ForegroundColor Cyan
Write-Host "`nYou can now use the frontend at http://localhost:3000/claims" -ForegroundColor Green
