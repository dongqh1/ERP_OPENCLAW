import assert from 'node:assert/strict'
import test, { afterEach } from 'node:test'

import { deleteSession, getMessages, getSessions, updateSessionTitle } from '../src/api/history.js'

const originalFetch = globalThis.fetch

afterEach(() => {
  globalThis.fetch = originalFetch
})

test('history API builds list and message URLs and returns JSON bodies', async () => {
  const requests = []
  globalThis.fetch = async url => {
    requests.push(url)
    return Response.json({ sessions: [], messages: [] })
  }

  const sessions = await getSessions(2, 10)
  const messages = await getMessages('thread-1')

  assert.deepEqual(requests, ['/api/history?page=2&limit=10', '/api/history/thread-1/messages'])
  assert.deepEqual(sessions, { sessions: [], messages: [] })
  assert.deepEqual(messages, { sessions: [], messages: [] })
})

test('history API sends delete and URL-encodes a renamed title', async () => {
  const requests = []
  globalThis.fetch = async (url, options = {}) => {
    requests.push({ url, method: options.method || 'GET' })
    return Response.json({ success: true })
  }

  await deleteSession('thread-2')
  await updateSessionTitle('thread-2', '火花塞 对比')

  assert.deepEqual(requests, [
    { url: '/api/history/thread-2', method: 'DELETE' },
    { url: '/api/history/thread-2?title=%E7%81%AB%E8%8A%B1%E5%A1%9E%20%E5%AF%B9%E6%AF%94', method: 'PATCH' }
  ])
})

test('history API reports failed HTTP responses', async () => {
  globalThis.fetch = async () => new Response('', { status: 503, statusText: 'Unavailable' })

  await assert.rejects(getSessions(), /获取会话列表失败/)
  await assert.rejects(getMessages('thread-3'), /获取会话消息失败/)
  await assert.rejects(deleteSession('thread-3'), /删除会话失败/)
  await assert.rejects(updateSessionTitle('thread-3', '标题'), /更新会话标题失败/)
})
