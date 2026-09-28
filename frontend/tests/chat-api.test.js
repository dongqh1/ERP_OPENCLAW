import assert from 'node:assert/strict'
import test, { afterEach } from 'node:test'

import { resumeChat, streamChat } from '../src/api/chat.js'

const originalFetch = globalThis.fetch
const originalLog = console.log
const originalError = console.error

afterEach(() => {
  globalThis.fetch = originalFetch
  console.log = originalLog
  console.error = originalError
})

function streamResponse(events, chunkSizes = []) {
  const content = events.map(event => `data: ${JSON.stringify(event)}\n\n`).join('')
  const bytes = new TextEncoder().encode(content)
  const chunks = []
  let offset = 0
  for (const size of chunkSizes) {
    if (offset >= bytes.length) break
    chunks.push(bytes.slice(offset, offset + size))
    offset += size
  }
  if (offset < bytes.length) chunks.push(bytes.slice(offset))

  const body = new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(chunk)
      controller.close()
    }
  })
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

test('streamChat parses fragmented SSE tokens and done events', async () => {
  let request
  const tokens = []
  let done
  globalThis.fetch = async (url, options) => {
    request = { url, options }
    return streamResponse([
      { type: 'token', content: '采购', source: 'main' },
      { type: 'done', thread_id: 'thread-1', content: '采购建议' }
    ], [9, 4, 12, 3])
  }

  const result = await streamChat('帮我分析', null, {
    onToken: content => tokens.push(content),
    onDone: value => { done = value }
  })

  assert.equal(request.url, '/api/chat/stream')
  assert.deepEqual(JSON.parse(request.options.body), { message: '帮我分析', thread_id: null })
  assert.deepEqual(tokens, ['采购'])
  assert.equal(result.thread_id, 'thread-1')
  assert.equal(result.content, '采购建议')
  assert.deepEqual(done, result)
})

test('streamChat correlates tool start, argument, result, and end events', async () => {
  const started = []
  const args = []
  const results = []
  const ended = []
  globalThis.fetch = async () => streamResponse([
    { type: 'tool_start', tool_call_id: 'tool-1', tool_name: 'supplier_query', source: 'analyst' },
    { type: 'tool_args', args: '{"name":', source: 'analyst' },
    { type: 'tool_args', args: '"Bosch"}', source: 'analyst' },
    { type: 'tool_result', text: '[{"id":1}]', images: [] },
    { type: 'tool_end', tool_call_id: 'tool-1', tool_name: 'supplier_query', source: 'analyst' },
    { type: 'done', thread_id: 'thread-2', content: '' }
  ])

  const result = await streamChat('查供应商', 'thread-2', {
    onToolStart: tool => started.push(tool),
    onToolArgs: value => args.push(value),
    onToolResult: tool => results.push(tool),
    onToolEnd: tool => ended.push(tool)
  })

  assert.equal(started[0].name, 'supplier_query')
  assert.deepEqual(args, ['{"name":', '"Bosch"}'])
  assert.equal(results[0].args, '{"name":"Bosch"}')
  assert.equal(results[0].text, '[{"id":1}]')
  assert.equal(ended[0].id, 'tool-1')
  assert.equal(result.tool_calls.length, 1)
})

test('resumeChat returns interrupt data without marking the turn done', async () => {
  console.log = () => {}
  let interrupt
  let done = false
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/chat/thread-3/resume')
    assert.deepEqual(JSON.parse(options.body), { resume: { supplement: '供应商是博世' } })
    return streamResponse([
      { type: 'interrupt', interrupt_type: 'hitl_approval', thread_id: 'thread-3', action_requests: [] }
    ])
  }

  const result = await resumeChat('thread-3', { supplement: '供应商是博世' }, {
    onInterrupt: value => { interrupt = value },
    onDone: () => { done = true }
  })

  assert.equal(result.interrupted, true)
  assert.equal(result.interrupt_data.interrupt_type, 'hitl_approval')
  assert.equal(interrupt.thread_id, 'thread-3')
  assert.equal(done, false)
})

test('streamChat reports server error events to the caller', async () => {
  console.error = () => {}
  let reported
  globalThis.fetch = async () => streamResponse([
    { type: 'error', message: '模型服务不可用' }
  ])

  await assert.rejects(
    streamChat('你好', null, { onError: error => { reported = error } }),
    /模型服务不可用/
  )
  assert.match(reported.message, /模型服务不可用/)
})

test('streamChat treats an aborted request as a completed partial result', async () => {
  console.log = () => {}
  let done
  globalThis.fetch = async () => { throw new DOMException('Aborted', 'AbortError') }

  const result = await streamChat('你好', 'thread-4', {
    onDone: value => { done = value }
  })

  assert.equal(result.aborted, true)
  assert.deepEqual(done, result)
})
