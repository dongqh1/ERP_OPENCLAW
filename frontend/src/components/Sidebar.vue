<template>
  <aside class="sidebar" aria-label="采购工作台侧边栏">
    <div class="sidebar-header">
      <div class="brand-lockup">
        <div class="brand-mark" aria-hidden="true">采</div>
        <div class="brand-copy">
          <span class="brand-name">采衡</span>
          <span class="brand-subtitle">个人采购工作台</span>
        </div>
      </div>

      <button class="new-chat-btn" type="button" @click="$emit('new-chat')">
        <span class="new-chat-icon" aria-hidden="true">＋</span>
        新建采购对话
      </button>
      <div class="domain-status">
        当前领域 <strong>{{ currentDomain === 'pc' ? 'PC 配置采购' : currentDomain === 'car' ? '汽车零部件采购' : '由 Router Agent 判断' }}</strong>
      </div>
    </div>

    <div class="search-box">
      <label class="search-label" for="session-search">工作记录</label>
      <div class="search-field">
        <span class="search-icon" aria-hidden="true">⌕</span>
        <input
          id="session-search"
          v-model="searchKeyword"
          type="search"
          placeholder="搜索采购会话"
          class="search-input"
        />
      </div>
    </div>

    <div class="session-list">
      <div class="session-list-header">
        <span>最近会话</span>
        <span class="session-count">{{ filteredSessions.length.toString().padStart(2, '0') }}</span>
      </div>

      <div class="session-items">
        <div
          v-for="session in filteredSessions"
          :key="session.thread_id"
          class="session-item"
          role="button"
          tabindex="0"
          :class="{ active: session.thread_id === currentThreadId }"
          @click="$emit('select-session', session.thread_id)"
          @keydown.enter="$emit('select-session', session.thread_id)"
          @keydown.space.prevent="$emit('select-session', session.thread_id)"
        >
          <span class="session-marker" aria-hidden="true"></span>
          <span class="session-info">
            <span class="session-title">{{ session.title }}</span>
            <span class="session-domain" :class="session.domain === 'pc' ? 'pc-domain' : 'car-domain'">
              {{ session.domain === 'pc' ? 'PC 配置' : '汽车采购' }}
            </span>
            <span class="session-time">{{ formatTime(session.updated_at) }}</span>
          </span>
          <button
            class="delete-btn"
            type="button"
            title="删除会话"
            aria-label="删除会话"
            @click.stop="handleDelete(session.thread_id)"
            @keydown.stop
          >×</button>
        </div>

        <div v-if="sessions.length === 0" class="empty-sessions">
          <span class="empty-session-mark" aria-hidden="true">＋</span>
          <p>这里还没有采购记录</p>
          <p class="empty-session-hint">新建对话后会自动保存在这里</p>
        </div>
        <div v-else-if="filteredSessions.length === 0" class="empty-sessions search-empty">
          <p>没有匹配的会话</p>
        </div>
      </div>
    </div>

    <footer class="sidebar-footer">
      <span class="footer-mark" aria-hidden="true">衡</span>
      <div class="footer-copy">
        <span>独立个人项目</span>
        <span>采购决策工作台 · v1.0</span>
      </div>
    </footer>
  </aside>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  currentThreadId: { type: String, default: null },
  currentDomain: { type: String, default: 'car' }
})

const emit = defineEmits(['select-session', 'new-chat', 'delete-session'])
const searchKeyword = ref('')

const filteredSessions = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return props.sessions
  return props.sessions.filter(session =>
    session.title.toLowerCase().includes(keyword)
  )
})

function formatTime(timestamp) {
  if (!timestamp) return ''

  const date = new Date(timestamp)
  const diff = Date.now() - date.getTime()
  if (diff < 24 * 60 * 60 * 1000) {
    const hours = Math.floor(diff / (60 * 60 * 1000))
    if (hours < 1) {
      const minutes = Math.floor(diff / (60 * 1000))
      return minutes < 1 ? '刚刚' : `${minutes} 分钟前`
    }
    return `${hours} 小时前`
  }
  return `${date.getMonth() + 1}/${date.getDate()}`
}

function handleDelete(threadId) {
  if (confirm('确定要删除这个会话吗？')) {
    emit('delete-session', threadId)
  }
}
</script>

<style scoped>
.sidebar {
  --side-bg: #18251f;
  --side-panel: #202f28;
  --side-line: rgba(241, 238, 222, 0.11);
  --side-text: #f1efe5;
  --side-muted: #a6afa0;
  width: 286px;
  height: 100vh;
  display: flex;
  flex: 0 0 286px;
  flex-direction: column;
  color: var(--side-text);
  background:
    radial-gradient(ellipse at 0 0, rgba(174, 190, 137, 0.1), transparent 38%),
    var(--side-bg);
  border-right: 1px solid rgba(23, 37, 30, 0.2);
  position: relative;
  z-index: 2;
}

.sidebar-header {
  padding: 27px 22px 22px;
  border-bottom: 1px solid var(--side-line);
}

.brand-lockup {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 2px 26px;
}

.brand-mark,
.footer-mark {
  display: grid;
  place-items: center;
  color: #17251e;
  background: #d4dfb6;
  font-family: 'Noto Serif SC', 'Songti SC', serif;
  font-weight: 800;
}

.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 13px 13px 13px 4px;
  font-size: 22px;
  box-shadow: 0 7px 18px rgba(0, 0, 0, 0.16);
}

.brand-copy,
.footer-copy {
  display: flex;
  flex-direction: column;
}

.brand-name {
  color: #f7f5ea;
  font-size: 19px;
  line-height: 1.2;
  font-weight: 750;
  letter-spacing: 0.08em;
}

.brand-subtitle {
  margin-top: 5px;
  color: var(--side-muted);
  font-size: 11px;
  letter-spacing: 0.05em;
}

.new-chat-btn {
  width: 100%;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  border: 1px solid rgba(218, 228, 193, 0.42);
  border-radius: 10px;
  color: #e7edda;
  background: rgba(218, 228, 193, 0.08);
  font: inherit;
  font-size: 13px;
  font-weight: 650;
  letter-spacing: 0.025em;
  cursor: pointer;
  transition: background 180ms ease, border-color 180ms ease, transform 180ms ease;
}

.new-chat-btn:hover {
  background: rgba(218, 228, 193, 0.15);
  border-color: rgba(218, 228, 193, 0.75);
  transform: translateY(-1px);
}

.domain-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 9px;
  color: #aab7a9;
  font-size: 10px;
}

.domain-status strong {
  color: #dce5d5;
  font-size: 10px;
  font-weight: 650;
}

.new-chat-btn:focus-visible,
.session-item:focus-visible,
.delete-btn:focus-visible {
  outline: 2px solid #d4dfb6;
  outline-offset: 3px;
}

.new-chat-icon {
  font-size: 19px;
  line-height: 1;
  font-weight: 350;
}

.search-box {
  padding: 22px 22px 8px;
}

.search-label,
.session-list-header {
  color: #b3bcad;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.13em;
}

.search-label {
  display: block;
  margin: 0 0 10px 2px;
}

.search-field {
  height: 39px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 11px;
  border: 1px solid var(--side-line);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.045);
  transition: border-color 180ms ease, background 180ms ease;
}

.search-field:focus-within {
  border-color: rgba(212, 223, 182, 0.62);
  background: rgba(255, 255, 255, 0.075);
}

.search-icon {
  color: #a7b49b;
  font-size: 22px;
  line-height: 1;
}

.search-input {
  width: 100%;
  border: 0;
  outline: 0;
  color: #f1efe5;
  background: transparent;
  font: inherit;
  font-size: 12px;
}

.search-input::placeholder { color: #89968b; }
.search-input::-webkit-search-cancel-button { cursor: pointer; }

.session-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 12px 12px;
}

.session-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 11px 10px;
}

.session-count {
  color: #748278;
  font: 11px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: 0.04em;
}

.session-items { display: flex; flex-direction: column; gap: 4px; }

.session-item {
  width: 100%;
  min-height: 56px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  text-align: left;
  border: 1px solid transparent;
  border-radius: 9px;
  color: var(--side-text);
  background: transparent;
  cursor: pointer;
  transition: background 160ms ease, border-color 160ms ease;
}

.session-item:hover { background: rgba(255, 255, 255, 0.055); }

.session-item.active {
  border-color: rgba(208, 221, 178, 0.19);
  background: rgba(212, 223, 182, 0.115);
}

.session-marker {
  width: 6px;
  height: 6px;
  flex: 0 0 6px;
  border: 1px solid #849286;
  border-radius: 50%;
}

.session-item.active .session-marker {
  border-color: #d4dfb6;
  background: #d4dfb6;
  box-shadow: 0 0 0 3px rgba(212, 223, 182, 0.1);
}

.session-info { min-width: 0; flex: 1; }

.session-title {
  display: block;
  overflow: hidden;
  color: #e7e9df;
  font-size: 12px;
  font-weight: 550;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-domain {
  display: inline-block;
  margin-top: 4px;
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 9px;
  line-height: 1.2;
}

.car-domain {
  color: #d7e4d1;
  background: rgba(111, 143, 111, 0.2);
}

.pc-domain {
  color: #f0d8bd;
  background: rgba(169, 126, 87, 0.2);
}

.session-time {
  display: block;
  margin-top: 4px;
  color: #8c9a8e;
  font-size: 10px;
}

.delete-btn {
  display: grid;
  width: 22px;
  height: 22px;
  flex: 0 0 22px;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 5px;
  color: #bdc7b9;
  background: transparent;
  font-family: inherit;
  font-size: 17px;
  line-height: 1;
  opacity: 0;
  cursor: pointer;
  transition: color 150ms ease, background 150ms ease, opacity 150ms ease;
}

.session-item:hover .delete-btn,
.session-item:focus-within .delete-btn { opacity: 1; }
.delete-btn:hover { color: #fff0e9; background: rgba(173, 94, 71, 0.35); }

.empty-sessions {
  padding: 38px 12px 24px;
  text-align: center;
  color: #c2cabc;
  font-size: 12px;
}

.empty-session-mark {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  margin: 0 auto 12px;
  border: 1px solid rgba(212, 223, 182, 0.28);
  border-radius: 9px;
  color: #d4dfb6;
  font-size: 18px;
}

.empty-sessions p { margin: 0; }
.empty-sessions .empty-session-hint { margin-top: 7px; color: #88958a; font-size: 10px; }
.search-empty { padding-top: 24px; color: #aab5a8; }

.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 17px 22px 19px;
  border-top: 1px solid var(--side-line);
}

.footer-mark {
  width: 29px;
  height: 29px;
  border-radius: 8px 8px 8px 3px;
  color: #d9e1c3;
  background: rgba(212, 223, 182, 0.12);
  font-size: 14px;
}

.footer-copy { gap: 3px; }
.footer-copy span:first-child { color: #d8dfd0; font-size: 10px; font-weight: 650; }
.footer-copy span:last-child { color: #8f9b8e; font-size: 9px; letter-spacing: 0.035em; }

@media (max-width: 760px) {
  .sidebar { width: 238px; flex-basis: 238px; }
  .sidebar-header { padding-right: 17px; padding-left: 17px; }
  .search-box { padding-right: 17px; padding-left: 17px; }
  .sidebar-footer { padding-right: 17px; padding-left: 17px; }
}

@media (max-width: 560px) {
  .sidebar {
    width: 100%;
    height: auto;
    flex: 0 0 auto;
    border-right: 0;
    border-bottom: 1px solid rgba(23, 37, 30, 0.2);
  }

  .sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 11px 15px;
    border-bottom: 0;
  }

  .brand-lockup { gap: 9px; margin: 0; }
  .brand-mark { width: 35px; height: 35px; border-radius: 11px 11px 11px 4px; font-size: 19px; }
  .brand-name { font-size: 16px; }
  .brand-subtitle { margin-top: 2px; font-size: 9px; }
  .new-chat-btn { width: auto; min-height: 37px; padding: 0 12px; font-size: 11px; }
  .new-chat-icon { font-size: 16px; }
  .domain-status { display: none; }
  .search-box, .sidebar-footer { display: none; }
  .session-list { max-height: 58px; overflow-x: auto; overflow-y: hidden; padding: 0 12px 9px; }
  .session-list-header, .empty-sessions { display: none; }
  .session-items { width: max-content; min-width: 100%; flex-direction: row; gap: 6px; }
  .session-item { width: 168px; min-height: 42px; gap: 7px; padding: 6px 8px; background: rgba(255, 255, 255, 0.035); }
  .session-time { display: none; }
  .session-title { font-size: 10px; }
  .delete-btn { width: 18px; height: 18px; flex-basis: 18px; opacity: 0.65; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition-duration: 0.01ms !important; }
}
</style>
