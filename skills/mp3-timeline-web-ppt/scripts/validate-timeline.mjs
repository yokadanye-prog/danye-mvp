#!/usr/bin/env node
import fs from 'node:fs'
import path from 'node:path'

const args = process.argv.slice(2)
const timelinePath = args[0]
if (!timelinePath || timelinePath.startsWith('--')) {
  console.error('Usage: node validate-timeline.mjs <timeline.json> --duration <seconds> [--srt captions.srt]')
  process.exit(2)
}

const option = (name) => {
  const index = args.indexOf(name)
  return index >= 0 ? args[index + 1] : undefined
}

const duration = Number(option('--duration'))
const srtPath = option('--srt')
const tolerance = 0.002
const requiredPageFields = ['id', 'pageNumber', 'section', 'subsection', 'start', 'end', 'cueStart', 'cueEnd', 'narration', 'screen', 'visual', 'transition', 'priority', 'beats']
const requiredBeatFields = ['id', 'start', 'end', 'cueStart', 'cueEnd', 'action']
const errors = []

if (!Number.isFinite(duration) || duration <= 0) errors.push('A positive --duration is required')

const timeline = JSON.parse(fs.readFileSync(timelinePath, 'utf8'))
const pages = Array.isArray(timeline) ? timeline : timeline.pages
if (Array.isArray(timeline)) errors.push('Timeline top level must be an object')
if (!Array.isArray(pages) || pages.length === 0) errors.push('Timeline must contain a non-empty pages array')
if (!Array.isArray(timeline) && timeline.clock !== 'audio.currentTime') {
  errors.push(`Timeline clock is ${timeline.clock}, expected audio.currentTime`)
}
if (!Array.isArray(timeline) && !['rich', 'concise', 'custom'].includes(timeline.contentDensity)) {
  errors.push(`Timeline contentDensity is ${timeline.contentDensity}, expected rich, concise, or custom`)
}

const nearlyEqual = (a, b) => Math.abs(a - b) <= tolerance
const pageIds = new Set()
const pageNumbers = new Set()
let beatCount = 0

for (const [index, page] of (pages ?? []).entries()) {
  for (const field of requiredPageFields) {
    if (page[field] === undefined) errors.push(`Page ${index + 1} missing ${field}`)
  }
  if (pageIds.has(page.id)) errors.push(`Duplicate page id: ${page.id}`)
  pageIds.add(page.id)
  if (pageNumbers.has(page.pageNumber)) errors.push(`Duplicate page number: ${page.pageNumber}`)
  pageNumbers.add(page.pageNumber)
  if (!(page.end > page.start)) errors.push(`Page ${page.id} has an invalid range`)
  if (index === 0 && !nearlyEqual(page.start, 0)) errors.push(`First page starts at ${page.start}, expected 0`)
  if (index > 0 && !nearlyEqual(pages[index - 1].end, page.start)) {
    errors.push(`Gap or overlap between ${pages[index - 1].id} and ${page.id}`)
  }

  const beatIds = new Set()
  if (!Array.isArray(page.beats) || page.beats.length === 0) {
    errors.push(`Page ${page.id} must contain at least one beat`)
  }
  for (const [beatIndex, beat] of (page.beats ?? []).entries()) {
    beatCount += 1
    for (const field of requiredBeatFields) {
      if (beat[field] === undefined) errors.push(`Page ${page.id} beat ${beatIndex + 1} missing ${field}`)
    }
    if (beatIds.has(beat.id)) errors.push(`Duplicate beat id in ${page.id}: ${beat.id}`)
    beatIds.add(beat.id)
    if (!(beat.end > beat.start)) errors.push(`Beat ${beat.id} has an invalid range`)
    if (beat.start < page.start - tolerance || beat.end > page.end + tolerance) {
      errors.push(`Beat ${beat.id} falls outside page ${page.id}`)
    }
    if (beatIndex === 0 && !nearlyEqual(beat.start, page.start)) {
      errors.push(`First beat in ${page.id} starts at ${beat.start}, expected ${page.start}`)
    }
    if (beatIndex > 0 && !nearlyEqual(page.beats[beatIndex - 1].end, beat.start)) {
      errors.push(`Beat gap or overlap before ${beat.id}`)
    }
  }
  const finalBeat = page.beats?.at(-1)
  if (finalBeat && !nearlyEqual(finalBeat.end, page.end)) {
    errors.push(`Final beat in ${page.id} ends at ${finalBeat.end}, expected ${page.end}`)
  }
}

const finalPage = pages?.at(-1)
if (finalPage && Number.isFinite(duration) && !nearlyEqual(finalPage.end, duration)) {
  errors.push(`Final page ends at ${finalPage.end}, expected ${duration}`)
}

let srtLastEnd = null
if (srtPath) {
  const source = fs.readFileSync(srtPath, 'utf8').replace(/^\uFEFF/, '')
  const matches = [...source.matchAll(/\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})/g)]
  const last = matches.at(-1)
  if (!last) errors.push('Could not parse any SRT timing lines')
  if (last) {
    srtLastEnd = Number(last[1]) * 3600 + Number(last[2]) * 60 + Number(last[3]) + Number(last[4]) / 1000
    if (Number.isFinite(duration) && srtLastEnd > duration + tolerance) {
      errors.push(`SRT last end ${srtLastEnd} exceeds duration ${duration}`)
    }
  }
}

console.log(JSON.stringify({
  status: errors.length === 0 ? 'PASS' : 'FAIL',
  timeline: path.resolve(timelinePath),
  audioDuration: duration,
  pageCount: pages?.length ?? 0,
  beatCount,
  coverage: pages?.length ? [pages[0].start, finalPage.end] : null,
  srtLastEnd,
  errors,
}, null, 2))

if (errors.length > 0) process.exit(1)
