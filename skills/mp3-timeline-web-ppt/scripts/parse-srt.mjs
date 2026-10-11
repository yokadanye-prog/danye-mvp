#!/usr/bin/env node
import fs from 'node:fs'
import path from 'node:path'

const args = process.argv.slice(2)
const input = args[0]

if (!input || input.startsWith('--')) {
  console.error('Usage: node parse-srt.mjs <captions.srt> [--json output.json] [--audio-duration seconds]')
  process.exit(2)
}

const option = (name) => {
  const index = args.indexOf(name)
  return index >= 0 ? args[index + 1] : undefined
}

const jsonOutput = option('--json')
const audioDurationRaw = option('--audio-duration')
const audioDuration = audioDurationRaw === undefined ? undefined : Number(audioDurationRaw)

const toSeconds = (value) => {
  const match = value.trim().match(/^(\d{2}):(\d{2}):(\d{2})[,.](\d{3})$/)
  if (!match) throw new Error(`Invalid SRT timestamp: ${value}`)
  return Number(match[1]) * 3600 + Number(match[2]) * 60 + Number(match[3]) + Number(match[4]) / 1000
}

const source = fs.readFileSync(input, 'utf8').replace(/^\uFEFF/, '').trim()
const blocks = source ? source.split(/\r?\n\s*\r?\n/) : []
const cues = []
const errors = []

for (const block of blocks) {
  const lines = block.split(/\r?\n/)
  const id = Number(lines[0]?.trim())
  const timing = lines[1]?.match(/^\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*$/)
  if (!Number.isInteger(id) || !timing) {
    errors.push(`Malformed cue block: ${block.slice(0, 80)}`)
    continue
  }
  try {
    const start = toSeconds(timing[1])
    const end = toSeconds(timing[2])
    if (end < start) errors.push(`Cue ${id} ends before it starts`)
    cues.push({ id, start, end, text: lines.slice(2).join('\n').trim() })
  } catch (error) {
    errors.push(`Cue ${id}: ${error.message}`)
  }
}

for (let index = 0; index < cues.length; index += 1) {
  const cue = cues[index]
  if (index > 0) {
    const previous = cues[index - 1]
    if (cue.id <= previous.id) errors.push(`Cue id order fails at ${cue.id}`)
    if (cue.start < previous.start) errors.push(`Cue time order fails at ${cue.id}`)
  }
}

const first = cues[0]
const last = cues.at(-1)
if (audioDuration !== undefined) {
  if (!Number.isFinite(audioDuration) || audioDuration <= 0) errors.push('Invalid --audio-duration value')
  if (last && last.end > audioDuration + 0.001) errors.push(`Final cue ${last.end} exceeds audio duration ${audioDuration}`)
}

if (jsonOutput) {
  fs.mkdirSync(path.dirname(path.resolve(jsonOutput)), { recursive: true })
  fs.writeFileSync(jsonOutput, `${JSON.stringify(cues, null, 2)}\n`, 'utf8')
}

const report = {
  status: errors.length === 0 ? 'PASS' : 'FAIL',
  input: path.resolve(input),
  cueCount: cues.length,
  firstStart: first?.start ?? null,
  lastEnd: last?.end ?? null,
  audioDuration: audioDuration ?? null,
  jsonOutput: jsonOutput ? path.resolve(jsonOutput) : null,
  errors,
}

console.log(JSON.stringify(report, null, 2))
if (errors.length > 0) process.exit(1)

