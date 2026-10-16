<template>
  <div class="chat-area">
    <!-- 消息列表 -->
    <div class="message-list" ref="messageListRef">
      <!-- 空状态 -->
      <div v-if="displayMessages.length === 0" class="empty-state">
        <div class="empty-content">
          <div class="hero-topline">
            <div class="eyebrow"><span class="eyebrow-dot"></span>采衡 · 采购决策工作台</div>
            <span class="hero-edition">PERSONAL WORKSPACE <i>／</i> 01</span>
          </div>
          <div class="hero-copy">
            <h2>让每一笔采购，<br /><span>都有据可依。</span></h2>
            <p class="intro">从需求梳理、信息核验到方案比选与订单确认，把采购判断变成清晰、可追溯的工作流程。</p>
          </div>
          <div class="workflow-strip" aria-label="采购工作流">
            <span><b>01</b> 描述需求</span>
            <i aria-hidden="true"></i>
            <span><b>02</b> 核验与比选</span>
            <i aria-hidden="true"></i>
            <span><b>03</b> 确认执行</span>
          </div>
          <div class="direction-list">
            <section class="direction-card project-card" :class="{ 'is-selected': domain === 'car' }">
              <div class="card-topline">
                <span class="card-index">01 <i>／</i> CAR PARTS</span>
                <span class="card-monogram" aria-hidden="true">CAR</span>
              </div>
              <div class="card-copy">
                <h3>汽车零部件采购</h3>
                <p>查询模拟 ERP 零件、供应商、库存与采购记录；按车型关键词核验适配信息。</p>
              </div>
              <button type="button" class="domain-choice-button" :aria-pressed="domain === 'car'" @click="$emit('domain-select', 'car')">
                {{ domain === 'car' ? '当前领域 · 汽车采购' : '进入汽车采购' }}
              </button>
              <button type="button" class="suggestion-button" :disabled="streaming" @click="selectDomainSuggestion('car', carSuggestion)">
                <span>试用零件查询示例</span><span class="button-arrow" aria-hidden="true">↗</span>
              </button>
            </section>
            <section class="direction-card pc-card" :class="{ 'is-selected': domain === 'pc' }">
              <div class="card-topline">
                <span class="card-index">02 <i>／</i> PC BUILD</span>
                <span class="card-monogram" aria-hidden="true">PC</span>
              </div>
              <div class="card-copy">
                <h3>PC 电脑配置采购</h3>
                <p>按预算、用途、分辨率和新旧偏好规划整机；保留已有硬件并校验配置兼容。</p>
              </div>
              <button type="button" class="domain-choice-button" :aria-pressed="domain === 'pc'" @click="$emit('domain-select', 'pc')">
                {{ domain === 'pc' ? '当前领域 · PC 配置' : '进入电脑配置采购' }}
              </button>
              <div class="quick-prompts">
                <button type="button" :disabled="streaming" @click="selectDomainSuggestion('pc', pcGamingSuggestion)">8000 元 · RDR2 / 2K</button>
                <button type="button" :disabled="streaming" @click="selectDomainSuggestion('pc', gpuKeepSuggestion)">已有 RTX 4070 Super</button>
                <button type="button" :disabled="streaming" @click="selectDomainSuggestion('pc', cpuKeepSuggestion)">保留 7800X3D</button>
              </div>
            </section>
          </div>
          <p class="data-note"><span class="note-rule"></span>当前汽车 ERP 与 PC 硬件目录均为本地模拟数据；PC 性能定位为演示评分，不是实测帧率。</p>
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
  },
  domain: {
    type: String,
    default: 'car'
  }
})

const emit = defineEmits(['suggestion', 'domain-select'])
const carSuggestion = '请查询摩托车零部件“火花塞”的 ERP 物料、供应商、库存和历史采购记录，并说明当前模拟数据中是否有明确车型适配信息。'
const pcGamingSuggestion = '预算 8000 元配置一台主机，主要玩《荒野大镖客 2》和 3A 游戏，目标 2K 分辨率、60 FPS，只要全新硬件。请生成配置并检查兼容性。'
const gpuKeepSuggestion = '预算 4000 元，我已经有 RTX 4070 Super，请保留这张显卡，推荐其余硬件，检查兼容性并说明新购总价。'
const cpuKeepSuggestion = '预算 6000 元，主要玩 3A 游戏，请保留我的 Ryzen 7 7800X3D CPU，搭配其余硬件并检查兼容性。'

function selectDomainSuggestion(domain, message) {
  if (props.streaming) return
  emit('domain-select', domain)
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
  min-width: 0;
  background: #f5f4ee;
}

/* 消息列表 */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 22px 0 28px;
  scrollbar-color: #c9c9ba transparent;
  scrollbar-width: thin;
}

.message-list::-webkit-scrollbar {
  width: 6px;
}

.message-list::-webkit-scrollbar-track {
  background: transparent;
}

.message-list::-webkit-scrollbar-thumb {
  background: #c9c9ba;
  border-radius: 6px;
}

.message-list::-webkit-scrollbar-thumb:hover {
  background: #a9ad9d;
}

/* 空状态 */
.empty-state {
  min-height: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: clamp(30px, 7vh, 74px) clamp(20px, 5vw, 64px) 52px;
  background:
    radial-gradient(ellipse at 85% 8%, rgba(211, 219, 191, 0.26), transparent 29%),
    #f5f4ee;
}

.empty-content {
  width: min(100%, 920px);
  margin: 0 auto;
}

.hero-topline {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding-bottom: 15px;
  border-bottom: 1px solid #dcded2;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  color: #53654d;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.eyebrow-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #9a6c41;
  box-shadow: 0 0 0 4px rgba(154, 108, 65, 0.11);
}

.hero-edition {
  color: #96998e;
  font: 9px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: 0.12em;
  white-space: nowrap;
}

.hero-edition i,
.card-index i {
  color: #b6b7a9;
  font-style: normal;
  padding: 0 3px;
}

.hero-copy {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 32px;
  padding: clamp(29px, 5vh, 49px) 0 27px;
}

.empty-state h2 {
  color: #1e2e25;
  font-family: 'Noto Serif SC', 'Songti SC', serif;
  font-size: clamp(32px, 4.2vw, 48px);
  font-weight: 700;
  letter-spacing: 0.045em;
  line-height: 1.38;
  white-space: nowrap;
}

.empty-state h2 span { color: #78875c; }

.intro {
  max-width: 330px;
  margin: 0 0 5px;
  color: #73796d;
  font-size: 13px;
  line-height: 1.95;
}

.workflow-strip {
  display: flex;
  align-items: center;
  gap: 13px;
  margin-bottom: 18px;
  padding: 12px 0;
  border-top: 1px solid #e2e2d8;
  border-bottom: 1px solid #e2e2d8;
  color: #686f62;
  font-size: 10px;
  letter-spacing: 0.04em;
}

.workflow-strip span { white-space: nowrap; }
.workflow-strip b { margin-right: 5px; color: #8a6749; font: 10px ui-monospace, SFMono-Regular, Menlo, monospace; }
.workflow-strip i { width: 24px; height: 1px; background: #c8cbbd; }

.direction-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 13px;
}

.direction-card {
  display: flex;
  flex-direction: column;
  min-height: 211px;
  padding: 18px 20px 17px;
  border: 1px solid #e1e0d4;
  border-radius: 12px;
  background: rgba(255, 254, 249, 0.86);
  box-shadow: 0 7px 20px rgba(43, 50, 39, 0.035);
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}

.direction-card:hover {
  transform: translateY(-2px);
  border-color: #c5cbb5;
  box-shadow: 0 12px 28px rgba(43, 50, 39, 0.075);
}

.direction-card.is-selected {
  border-color: #77866b;
  box-shadow: 0 0 0 2px rgba(119, 134, 107, 0.13), 0 12px 28px rgba(43, 50, 39, 0.075);
}

.domain-choice-button {
  width: 100%;
  min-height: 36px;
  margin-top: auto;
  border: 1px solid #d5d9ca;
  border-radius: 7px;
  color: #354331;
  background: #f3f5ed;
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.domain-choice-button:hover {
  border-color: #9aa68d;
  background: #eaf0e2;
}

.quick-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.quick-prompts button {
  padding: 6px 8px;
  border: 1px solid #e3ddd2;
  border-radius: 999px;
  color: #665744;
  background: #fbf7f0;
  font: inherit;
  font-size: 10px;
  cursor: pointer;
}

.quick-prompts button:hover {
  border-color: #cbbba5;
  background: #f7efe4;
}

.quick-prompts button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.card-topline {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.card-index {
  color: #85897c;
  font: 9px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: 0.08em;
}

.card-monogram {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border: 1px solid #d8ddca;
  border-radius: 9px 9px 9px 3px;
  color: #647151;
  background: #f3f5eb;
  font: 10px ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: 0.06em;
}

.pc-card .card-monogram {
  border-color: #e4d7c8;
  color: #966b47;
  background: #f8f1e9;
}

.parts-card .card-monogram {
  border-color: #d4dfd0;
  color: #557259;
  background: #eff5ed;
}

.card-copy h3 {
  margin: 0 0 8px;
  color: #29362c;
  font-family: 'Noto Serif SC', 'Songti SC', serif;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.025em;
}

.card-copy p {
  max-width: 380px;
  margin: 0 0 15px;
  color: #73796d;
  font-size: 11px;
  line-height: 1.75;
}

.suggestion-button {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  padding: 9px 0 0;
  border: 0;
  border-top: 1px solid #e7e6dc;
  color: #4e6348;
  background: transparent;
  font: inherit;
  font-size: 11px;
  font-weight: 650;
  text-align: left;
  cursor: pointer;
  transition: color 160ms ease;
}

.suggestion-button:hover:not(:disabled) { color: #986b43; }

.suggestion-button:focus-visible {
  outline: 2px solid #71815a;
  outline-offset: 2px;
}

.suggestion-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.button-arrow { font-size: 16px; line-height: 0.8; }

.data-note {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: 17px;
  color: #85897d;
  font-size: 10px;
  line-height: 1.65;
}

.note-rule { width: 17px; height: 1px; flex: 0 0 17px; background: #b4936e; }

@media (max-width: 760px) {
  .empty-state { padding-right: 28px; padding-left: 28px; }
  .hero-copy { gap: 22px; }
  .empty-state h2 { font-size: clamp(28px, 5vw, 40px); }
  .intro { max-width: 275px; font-size: 12px; }
  .direction-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .direction-card { padding: 16px; }
}

@media (max-width: 680px) {
  .empty-state { padding: 29px 18px 36px; }
  .hero-copy { align-items: flex-start; flex-direction: column; gap: 13px; padding: 28px 0 20px; }
  .empty-state h2 { font-size: clamp(31px, 8vw, 42px); }
  .intro { max-width: 440px; margin: 0; }
  .workflow-strip { gap: 8px; font-size: 9px; }
  .workflow-strip i { width: 14px; }
  .direction-list { grid-template-columns: 1fr; }
  .direction-card { min-height: 0; padding: 16px 18px; }
  .card-topline { margin-bottom: 12px; }
  .hero-edition { font-size: 8px; }
}

@media (prefers-reduced-motion: reduce) {
  .direction-card { transition: none; }
}

/* 消息列表 */
.messages {
  width: min(100%, 1050px);
  margin: 0 auto;
}
</style>
