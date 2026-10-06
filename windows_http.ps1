$ErrorActionPreference = 'Stop'
try {
    Add-Type -AssemblyName System.Net.Http
    $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json
    $handler = New-Object System.Net.Http.HttpClientHandler
    $client = New-Object System.Net.Http.HttpClient($handler)
    $client.Timeout = [TimeSpan]::FromSeconds(50)
    $request = New-Object System.Net.Http.HttpRequestMessage([System.Net.Http.HttpMethod]::Post, [string]$payload.url)
    $request.Content = New-Object System.Net.Http.ByteArrayContent(,[Convert]::FromBase64String($payload.body))
    $request.Content.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse($payload.content_type)
    $response = $client.SendAsync($request).GetAwaiter().GetResult()
    $bytes = $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
    @{status=[int]$response.StatusCode; body=[Convert]::ToBase64String($bytes)} | ConvertTo-Json -Compress
    $response.Dispose()
    $request.Dispose()
    $client.Dispose()
} catch {
    # Never print the URL or exception details, which may contain the bot token.
    [Console]::Out.WriteLine('{"error":"Windows HTTPS request failed"}')
    exit 1
}
