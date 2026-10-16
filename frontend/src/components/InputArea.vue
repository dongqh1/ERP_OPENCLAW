<template>
  <div class="input-area">
    <div class="input-container">
      <!-- 工具调用开关 -->
      <div class="tool-toggle">
        <label class="toggle-label">
          <input
            type="checkbox"
            :checked="showToolCalls"
            @change="emit('toggle-tool-calls', $event.target.checked)"
            class="toggle-checkbox"
          />
          <span class="toggle-switch"></span>
          <span class="toggle-text">显示工具调用</span>
        </label>
      </div>

      <!-- 输入框 -->
      <div class="input-wrapper" :class="{ focused: isFocused, streaming: streaming }">
        <textarea
          ref="textareaRef"
          v-model="inputText"
          @focus="isFocused = true"
          @blur="isFocused = false"
          @keydown.enter.exact.prevent="handleSend"
          @input="autoResize"
          :placeholder="domain === 'pc'
            ? '输入预算、用途、分辨率，或说明要保留的硬件…'
            : domain === 'car'
              ? '描述汽车零件、车型或采购需求…'
              : '先选采购领域，或直接描述你的采购需求…'"
          rows="1"
          :disabled="streaming"
          class="input-textarea"
        ></textarea>
        <!-- 发送按钮：流式时变为停止按钮 -->
        <button
          v-if="!streaming"
          class="send-btn"
          @click="handleSend"
          :disabled="!inputText.trim()"
        >
          <span>发送需求</span>
        </button>
        <button
          v-else
          class="stop-btn"
          @click="handleStop"
        >
          <span class="stop-icon">■</span>
          <span>停止生成</span>
        </button>
      </div>

      <!-- 提示信息 -->
      <div class="input-hint">
        <span v-if="!streaming">Enter 发送 <i>·</i> Shift + Enter 换行</span>
        <span v-else class="streaming-hint">正在整理采购信息…</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

/**
 * 输入区域组件
 *
 * 提供消息输入功能：
 * - 正常状态：显示"发送"按钮
 * - 流式输出时：输入框禁用，按钮变为"停止"
 */

const props = defineProps({
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

const emit = defineEmits(['send', 'stop', 'toggle-tool-calls'])

// 输入文本
const inputText = ref('')
// 是否获取焦点
const isFocused = ref(false)
// textarea 引用
const textareaRef = ref(null)

/**
 * 发送消息
 */
function handleSend() {
  const text = inputText.value.trim()
  if (!text) return

  emit('send', text)
  inputText.value = ''

  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.style.height = 'auto'
    }
  })
}

/**
 * 停止对话
 */
function handleStop() {
  emit('stop')
}

/**
 * 自动调整 textarea 高度
 */
function autoResize() {
  const textarea = textareaRef.value
  if (!textarea) return

  textarea.style.height = 'auto'
  textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px'
}
</script>

<style scoped>
.input-area {
  padding: 13px 28px 19px;
  background: #f5f4ee;
  border-top: 1px solid #e2e0d5;
}

.input-container {
  max-width: 960px;
  margin: 0 auto;
}

/* 工具调用开关 */
.tool-toggle { margin-bottom: 9px; }

.toggle-label {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.toggle-checkbox {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.toggle-switch {
  position: relative;
  width: 33px;
  height: 18px;
  background: #d7d8cc;
  border-radius: 10px;
  transition: all 0.2s ease;
}

.toggle-switch::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  background: #fffef9;
  border-radius: 50%;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(20, 35, 25, 0.18);
}

.toggle-checkbox:checked + .toggle-switch {
  background: #607452;
}

.toggle-checkbox:checked + .toggle-switch::after {
  transform: translateX(15px);
  background: #fff;
}

.toggle-checkbox:focus-visible + .toggle-switch { outline: 2px solid #71815a; outline-offset: 3px; }

.toggle-text {
  font-size: 11px;
  color: #777d70;
  font-weight: 550;
}

/* 输入框包装 */
.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 11px 12px 11px 16px;
  background: #fffef9;
  border: 1px solid #deded2;
  border-radius: 13px;
  transition: all 0.2s ease;
  box-shadow: 0 5px 15px rgba(44, 51, 39, 0.035);
}

.input-wrapper.focused {
  border-color: #84916d;
  box-shadow: 0 0 0 3px rgba(111, 129, 85, 0.11);
}

.input-wrapper.streaming {
  background: #f8f4e9;
  border-color: #d9c7a8;
}

/* 输入框 */
.input-textarea {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 14px;
  line-height: 1.6;
  resize: none;
  outline: none;
  min-height: 24px;
  max-height: 200px;
  color: #29352b;
  font-weight: 450;
}

.input-textarea::placeholder { color: #999b8e; }

.input-textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 发送按钮 */
.send-btn {
  flex-shrink: 0;
  padding: 9px 15px;
  background: #465a40;
  color: #fff;
  border: none;
  border-radius: 9px;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 7px rgba(40, 61, 43, 0.18);
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  background: #384b35;
  box-shadow: 0 4px 11px rgba(40, 61, 43, 0.23);
}

.send-btn:active:not(:disabled) {
  transform: translateY(0);
}

.send-btn:disabled {
  background: #e3e3d9;
  color: #a2a394;
  cursor: not-allowed;
  box-shadow: none;
}

/* 停止按钮 */
.stop-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 13px;
  background: #a65e4b;
  color: #fff;
  border: none;
  border-radius: 9px;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(134, 73, 57, 0.22);
}

.stop-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(134, 73, 57, 0.3);
}

.stop-btn:active {
  transform: translateY(0);
}

.stop-icon {
  font-size: 12px;
}

/* 提示信息 */
.input-hint {
  margin-top: 8px;
  text-align: right;
}

.input-hint span {
  font-size: 10px;
  color: #929487;
}

.input-hint i { padding: 0 4px; color: #b6b6a9; font-style: normal; }
.streaming-hint { color: #936b48 !important; }

@media (max-width: 560px) {
  .input-area { padding: 10px 14px calc(12px + env(safe-area-inset-bottom)); }
  .input-wrapper { gap: 8px; padding-left: 11px; }
  .input-textarea { font-size: 13px; }
  .send-btn, .stop-btn { padding: 9px 11px; font-size: 11px; }
}

@media (prefers-reduced-motion: reduce) {
  .input-wrapper, .send-btn, .stop-btn { transition: none; animation: none; }
}
</style>
