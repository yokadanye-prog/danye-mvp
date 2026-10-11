#!/usr/bin/env node
import fs from 'node:fs'
import path from 'node:path'

const themesDirectory = process.argv[2]
if (!themesDirectory) {
  console.error('Usage: node list-themes.mjs <themes-directory> [--json output.json]')
  process.exit(2)
}

const outputIndex = process.argv.indexOf('--json')
const output = outputIndex >= 0 ? process.argv[outputIndex + 1] : undefined
const errors = []
const themes = []

for (const entry of fs.readdirSync(themesDirectory, { withFileTypes: true })) {
  if (!entry.isDirectory()) continue
  const metadataPath = path.join(themesDirectory, entry.name, 'theme.json')
  if (!fs.existsSync(metadataPath)) continue
  try {
    const theme = JSON.parse(fs.readFileSync(metadataPath, 'utf8'))
    for (const field of ['id', 'name', 'nameZh', 'descriptionZh', 'mood', 'bestFor', 'preview']) {
      if (theme[field] === undefined) errors.push(`${entry.name}/theme.json missing ${field}`)
    }
    if (theme.id !== entry.name) errors.push(`${entry.name}/theme.json id mismatch: ${theme.id}`)
    themes.push(theme)
  } catch (error) {
    errors.push(`${metadataPath}: ${error.message}`)
  }
}

themes.sort((a, b) => a.id.localeCompare(b.id))

if (output) {
  fs.mkdirSync(path.dirname(path.resolve(output)), { recursive: true })
  fs.writeFileSync(output, `${JSON.stringify(themes, null, 2)}\n`, 'utf8')
}

console.log(JSON.stringify({
  status: errors.length === 0 ? 'PASS' : 'FAIL',
  themesDirectory: path.resolve(themesDirectory),
  themeCount: themes.length,
  themes: themes.map(({ id, nameZh, mood, bestFor, preview }) => ({ id, nameZh, mood, bestFor, preview })),
  errors,
}, null, 2))

if (errors.length > 0) process.exit(1)

