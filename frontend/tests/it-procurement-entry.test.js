import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse } from '@vue/compiler-sfc'

const chatAreaSource = readFileSync(new URL('../src/components/ChatArea.vue', import.meta.url), 'utf8')
const appSource = readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8')
const chatArea = parse(chatAreaSource).descriptor
const app = parse(appSource).descriptor

test('empty state presents both procurement directions and a sendable IT request', () => {
  const template = chatArea.template.content
  assert.match(template, /研发项目采购/)
  assert.match(template, /企业 IT 设备采购/)
  assert.match(template, /<button\b[^>]*@click="selectSuggestion\([^)]*\)"/)
  assert.match(chatArea.scriptSetup.content, /数量.*配置.*预算.*到货|配置.*数量.*预算.*到货/s)
})

test('suggestion click emits to App and reuses the existing send flow', () => {
  assert.match(chatArea.scriptSetup.content, /defineEmits\(\['suggestion'\]\)/)
  assert.match(chatArea.scriptSetup.content, /emit\('suggestion',\s*[^)]+\)/)
  assert.match(chatArea.template.content, /:disabled="streaming"/)
  assert.match(chatArea.scriptSetup.content, /if \(props\.streaming\) return/)
  assert.match(app.template.content, /<ChatArea[\s\S]*?@suggestion="handleSend"[\s\S]*?\/>/)
})
