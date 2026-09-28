# JARVIS voice preview — uses the same Windows SAPI preference as the application.
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$preferred = @('Microsoft George','George','Microsoft Ryan','Ryan','Microsoft David','David')
$chosen = $null
foreach ($p in $preferred) {
  $chosen = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Name -eq $p } | Select-Object -First 1
  if ($chosen) { break }
}
if ($chosen) {
  $s.SelectVoice($chosen.VoiceInfo.Name)
  Write-Host ("Using voice: " + $chosen.VoiceInfo.Name)
} else {
  Write-Host "George/Ryan not installed; Windows default voice will be used."
}
$s.Rate = -1
$s.Volume = 100
$s.Speak("Good morning, Sir. JARVIS is online. Ollama is connected and your local systems are ready. How may I assist you today?")
