[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InputVideo,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [string]$CutTimes = '',
    [ValidateSet(15, 30)]
    [int]$Fps = 30,
    [int]$InputSize = 280,
    [int]$MaxRes = 512,
    [string]$ToolRoot = $env:VIDEO_DEPTH_ANYTHING_HOME,
    [string]$PythonPath = $env:VIDEO_DEPTH_ANYTHING_PYTHON
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($ToolRoot)) {
    throw 'Set VIDEO_DEPTH_ANYTHING_HOME or pass -ToolRoot with your Video Depth Anything installation directory.'
}
$toolRoot = [System.IO.Path]::GetFullPath($ToolRoot)
$python = if ($PythonPath) { [System.IO.Path]::GetFullPath($PythonPath) } else { Join-Path $toolRoot '.venv\Scripts\python.exe' }
$runner = Join-Path $toolRoot 'run_streaming.py'
$checkpoint = Join-Path $toolRoot 'checkpoints\video_depth_anything_vits.pth'

foreach ($requiredPath in @($InputVideo, $python, $runner, $checkpoint)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required path not found: $requiredPath"
    }
}
foreach ($mediaCommand in @('ffmpeg','ffprobe')) {
    if (-not (Get-Command $mediaCommand -ErrorAction SilentlyContinue)) {
        throw "Missing command on PATH: $mediaCommand"
    }
}

$resolvedInput = (Resolve-Path -LiteralPath $InputVideo).Path
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputDir)
New-Item -ItemType Directory -Force -Path $resolvedOutput | Out-Null

$baseName = [System.IO.Path]::GetFileNameWithoutExtension($resolvedInput)
$workDir = Join-Path $resolvedOutput ('.vda-work-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $workDir | Out-Null

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Executable"
    }
}

function Get-DurationSeconds {
    param([string]$Path)
    $value = & ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $Path
    if ($LASTEXITCODE -ne 0 -or -not $value) {
        throw "Could not read video duration: $Path"
    }
    return [double]::Parse($value.Trim(), [Globalization.CultureInfo]::InvariantCulture)
}

function Invoke-DepthSegment {
    param(
        [string]$SegmentPath,
        [string]$SegmentOutput,
        [int]$PreferredSize
    )

    $sizes = @($PreferredSize, 252, 224) | Select-Object -Unique
    foreach ($size in $sizes) {
        Write-Host "Depth inference: $([System.IO.Path]::GetFileName($SegmentPath)); input_size=$size; fps=$Fps"
        Push-Location $toolRoot
        try {
            & $python $runner `
                --input_video $SegmentPath `
                --output_dir $SegmentOutput `
                --encoder vits `
                --input_size $size `
                --max_res $MaxRes `
                --target_fps $Fps `
                --grayscale
            if ($LASTEXITCODE -eq 0) {
                return
            }
        }
        finally {
            Pop-Location
        }
        Write-Warning "Inference failed at input_size=$size; retrying with a smaller size."
    }
    throw "Depth inference failed for segment: $SegmentPath"
}

try {
    $duration = Get-DurationSeconds -Path $resolvedInput
    $cuts = @()
    if ($CutTimes.Trim()) {
        $cuts = $CutTimes.Split(',') |
            ForEach-Object { [double]::Parse($_.Trim(), [Globalization.CultureInfo]::InvariantCulture) } |
            Where-Object { $_ -gt 0 -and $_ -lt $duration } |
            Sort-Object -Unique
    }

    $boundaries = @([double]0) + @($cuts) + @($duration)
    $depthSegments = [System.Collections.Generic.List[string]]::new()

    for ($index = 0; $index -lt $boundaries.Count - 1; $index++) {
        $start = $boundaries[$index]
        $segmentDuration = $boundaries[$index + 1] - $start
        $segmentName = 'segment_{0:D2}' -f ($index + 1)
        $segmentPath = Join-Path $workDir ($segmentName + '.mp4')
        $segmentOutDir = Join-Path $workDir ($segmentName + '_out')

        $startText = $start.ToString('0.000000', [Globalization.CultureInfo]::InvariantCulture)
        $durationText = $segmentDuration.ToString('0.000000', [Globalization.CultureInfo]::InvariantCulture)
        Invoke-Checked -Executable 'ffmpeg' -Arguments @(
            '-y', '-ss', $startText, '-i', $resolvedInput, '-t', $durationText,
            '-an', '-vf', "fps=$Fps", '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
            $segmentPath
        )

        New-Item -ItemType Directory -Force -Path $segmentOutDir | Out-Null
        Invoke-DepthSegment -SegmentPath $segmentPath -SegmentOutput $segmentOutDir -PreferredSize $InputSize

        $depthPath = Join-Path $segmentOutDir ($segmentName + '_vis.mp4')
        if (-not (Test-Path -LiteralPath $depthPath)) {
            throw "Expected depth segment was not created: $depthPath"
        }
        $depthSegments.Add($depthPath)
    }

    $finalPath = Join-Path $resolvedOutput ($baseName + '_depth_gray.mp4')
    if ($depthSegments.Count -eq 1) {
        Invoke-Checked -Executable 'ffmpeg' -Arguments @(
            '-y', '-i', $depthSegments[0], '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', $finalPath
        )
    }
    else {
        $ffmpegArgs = [System.Collections.Generic.List[string]]::new()
        $ffmpegArgs.Add('-y')
        for ($index = 0; $index -lt $depthSegments.Count; $index++) {
            $ffmpegArgs.Add('-i')
            $ffmpegArgs.Add($depthSegments[$index])
        }
        $inputs = (0..($depthSegments.Count - 1) | ForEach-Object { "[$($_):v]" }) -join ''
        $filter = "${inputs}concat=n=$($depthSegments.Count):v=1:a=0[outv]"
        foreach ($argument in @('-filter_complex', $filter, '-map', '[outv]', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', $finalPath)) {
            $ffmpegArgs.Add($argument)
        }
        Invoke-Checked -Executable 'ffmpeg' -Arguments $ffmpegArgs.ToArray()
    }

    Write-Host "Depth video created: $finalPath"
    & ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate -of default=noprint_wrappers=1 $finalPath
    if ($LASTEXITCODE -ne 0) {
        throw "Output verification failed: $finalPath"
    }
}
finally {
    if (Test-Path -LiteralPath $workDir) {
        $checkedWorkDir = [System.IO.Path]::GetFullPath($workDir)
        $outputPrefix = $resolvedOutput.TrimEnd([char[]]@('\','/')) + [System.IO.Path]::DirectorySeparatorChar
        $workLeaf = [System.IO.Path]::GetFileName($checkedWorkDir)
        $workItem = Get-Item -LiteralPath $checkedWorkDir -Force
        if (-not $checkedWorkDir.StartsWith($outputPrefix, [StringComparison]::OrdinalIgnoreCase) -or
            $workLeaf -notmatch '^\.vda-work-[0-9a-f]{32}$' -or
            ($workItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw 'Refusing cleanup outside the verified temporary output directory.'
        }
        Remove-Item -LiteralPath $workDir -Recurse -Force
    }
}
