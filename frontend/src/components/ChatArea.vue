<template>
  <div class="chat-area">
    <!-- 消息列表 -->
    <div class="message-list" ref="messageListRef">
      <!-- 空状态 -->
      <div v-if="displayMessages.length === 0" class="empty-state">
        <div class="empty-content">
          <div class="eyebrow">采购分析 · 方案评估 · 人工审批</div>
          <h2>企业采购决策助手</h2>
          <p class="intro">描述采购需求，结合可核实的业务数据分析预算、交期和配置约束。</p>
          <div class="direction-list">
            <section class="direction-card">
              <span class="direction-icon" aria-hidden="true">📋</span>
              <h3>研发项目采购</h3>
              <p>围绕项目预算与交付期限，对物料、供应商和报价进行约束分析。</p>
              <button type="button" class="suggestion-button" :disabled="streaming" @click="selectSuggestion(projectSuggestion)">
                试试项目采购分析 <span aria-hidden="true">→</span>
              </button>
            </section>
            <section class="direction-card">
              <span class="direction-icon" aria-hidden="true">💻</span>
              <h3>企业 IT 设备采购</h3>
              <p>按设备配置、数量、总预算、到货期与保修要求筛选已核实的候选方案。</p>
              <button type="button" class="suggestion-button" :disabled="streaming" @click="selectSuggestion(itSuggestion)">
                试试 IT 设备采购 <span aria-hidden="true">→</span>
              </button>
            </section>
          </div>
          <p class="data-note">分析结果取决于 ERP、供应商报价或用户提供的真实数据；订单操作需人工确认。</p>
        </div>
      </div>

      <!-- 消息列表（user / assistant / tool 按时间顺序混合展示）-->
      <div v-else class="messages">
        <MessageItem
          v-for="(message, index) in displayMessages"
          :key="message.id || index"
          :message="message"
          :is-streaming="isStreamingForMessage(message)"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import MessageItem from './MessageItem.vue'

/**
 * 对话区域组件
 *
 * 显示消息列表（user / assistant / tool 按时间顺序混合展示）
 * 当 showToolCalls 为 false 时，过滤掉 tool 消息只显示 AI 回复
 */

const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  streaming: {
    type: Boolean,
    default: false
  },
  showToolCalls: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['suggestion'])
const projectSuggestion = '请分析一个研发项目的采购方案：预算 8 万元，计划在 2026-11-30 前到货。请先查询 ERP 中的物料、库存和供应商报价，列出缺失信息，再比较符合预算与交期的方案。'
const itSuggestion = '请分析企业 IT 设备采购：笔记本电脑数量 20 台，配置至少 8 核 CPU、16GB 内存、512GB 存储，操作系统为 Windows 11，总预算 16 万元，希望在 2026-11-30 前到货，保修至少 24 个月。请查询已核实的设备型号、报价和交期，标出待确认信息，不要使用未核实报价生成订单。'

function selectSuggestion(message) {
  if (props.streaming) return
  emit('suggestion', message)
}

// 根据开关过滤展示的消息
const displayMessages = computed(() => {
  if (props.showToolCalls) {
    return props.messages
  }
  // 过滤掉 tool 消息，只保留 user 和 assistant
  return props.messages.filter(m => m.role !== 'tool')
})

// 消息列表引用
const messageListRef = ref(null)

/**
 * 判断当前消息是否处于流式输出状态
 * 只有最后一条 assistant 消息在 streaming 时才显示光标
 */
function isStreamingForMessage(msg) {
  if (!props.streaming || msg.role !== 'assistant') return false
  // 找到 messages 中最后一条 assistant 消息
  const lastAssistant = [...props.messages].reverse().find(m => m.role === 'assistant')
  return lastAssistant === msg
}

// 监听消息变化，自动滚动到底部
watch(
  () => props.messages.length,
  () => {
    nextTick(() => {
      scrollToBottom()
    })
  }
)

// 深度监听消息内容变化（流式更新时也会触发滚动）
watch(
  () => props.messages,
  () => {
    nextTick(() => {
      scrollToBottom()
    })
  },
  { deep: true }
)

/**
 * 滚动到底部
 */
function scrollToBottom() {
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}
</script>

<style scoped>
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
}

/* 消息列表 */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px 0;
}

.message-list::-webkit-scrollbar {
  width: 6px;
}

.message-list::-webkit-scrollbar-track {
  background: transparent;
}

.message-list::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.message-list::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* 空状态 */
.empty-state {
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
}

.empty-content {
  width: min(100%, 880px);
}

.eyebrow {
  margin-bottom: 12px;
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.empty-state h2 {
  font-size: clamp(26px, 4vw, 36px);
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 12px;
}

.intro {
  font-size: 15px;
  color: #64748b;
  line-height: 1.7;
  margin-bottom: 28px;
}

.direction-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.direction-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-height: 246px;
  padding: 24px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
}

.direction-icon {
  font-size: 26px;
  margin-bottom: 16px;
}

.direction-card h3 {
  font-size: 18px;
  color: #0f172a;
  margin-bottom: 10px;
}

.direction-card p {
  font-size: 14px;
  color: #64748b;
  line-height: 1.6;
  margin-bottom: 22px;
}

.suggestion-button {
  margin-top: auto;
  padding: 10px 14px;
  color: #0f766e;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  border-radius: 9px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.suggestion-button:hover:not(:disabled) {
  background: #ccfbf1;
}

.suggestion-button:focus-visible {
  outline: 2px solid #0f766e;
  outline-offset: 2px;
}

.suggestion-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.data-note {
  margin-top: 20px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 680px) {
  .empty-state { padding: 32px 18px; }
  .direction-list { grid-template-columns: 1fr; }
  .direction-card { min-height: 0; }
}

/* 消息列表 */
.messages {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
