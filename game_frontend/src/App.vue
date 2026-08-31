<template>
  <div class="layout">
    <!-- 顶部状态栏 -->
    <header class="topbar" v-if="state">
      <h1>《崇祯历史模拟器》 - {{ state.title }}</h1>
      <div class="stats">
        <span>国库: {{ formatMoney(state.treasury) }} 两</span>
        <span>内帑: {{ formatMoney(state.neitang) }} 两</span>
        <span>建州威胁: {{ state.jianzhou_threat }}%</span>
      </div>
      <div class="actions">
        <button @click="saveGame">存档</button>
        <button @click="loadGame">读档</button>
        <button @click="advanceTurn" :disabled="loading" class="primary-btn">
          {{ loading ? '推演中...' : '推进回合' }}
        </button>
      </div>
    </header>

    <!-- 主体区域 -->
    <div class="main-content" v-if="state">

      <!-- 左侧：天下十三布政使司（行省简略地图） -->
      <div class="provinces-panel">
        <h2>天下形势</h2>
        <div class="provinces-grid">
          <div
            v-for="prov in state.provinces"
            :key="prov.name"
            class="province-card"
            :class="{'danger': prov.status === '饥荒' || prov.status === '战乱' || prov.owner === '起义军'}"
            @click="selectProvince(prov)"
          >
            <h3>{{ prov.name }}</h3>
            <p>状态: {{ prov.status }}</p>
            <p>民心: {{ prov.stability }}</p>
            <p>流寇: {{ prov.rebel_risk }}%</p>
            <p v-if="prov.troops.length > 0">驻军: {{ prov.troops.length }}支</p>
          </div>
        </div>
      </div>

      <!-- 右侧：内阁、军队与诏书系统 -->
      <div class="right-panel">
        <!-- 军队信息 -->
        <div class="armies-box">
          <h2>大明经制之军</h2>
          <ul>
            <li v-for="army in state.armies" :key="army.id">
              {{ army.name }} - 驻扎: {{ army.location }} (人数: {{ army.count }}, 士气: {{ army.morale }})
            </li>
          </ul>
        </div>

        <!-- 大臣与派系 -->
        <div class="ministers-box">
          <h2>内阁大臣</h2>
          <ul>
            <li v-for="min in state.ministers" :key="min.name" @click="chatMinister(min)">
              {{ min.name }} ({{ min.title }}) - {{ min.faction }} [忠诚:{{ min.loyalty }}]
            </li>
          </ul>
        </div>

        <!-- 诏书拟定 -->
        <div class="edicts-box">
          <h2>拟定诏书</h2>
          <textarea v-model="newEdict" placeholder="请输入你要下达的诏书，如：调关宁铁骑入卫京师，并从内帑拨10万两犒军。"></textarea>
          <button @click="addEdict">加入队列</button>

          <ul class="edict-queue">
            <li v-for="(e, i) in edictsQueue" :key="i">
              {{ i+1 }}. {{ e }}
              <button @click="edictsQueue.splice(i, 1)">x</button>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- 弹窗：最新奏折报告 -->
    <div v-if="showReportModal" class="modal">
      <div class="modal-content">
        <h2>司礼监呈递：回合推演结果</h2>
        <div class="report-text" v-html="formatReport(lastReport)"></div>
        <button @click="showReportModal = false">朕已阅</button>
      </div>
    </div>

    <!-- 弹窗：大臣密谈 -->
    <div v-if="showChatModal" class="modal">
      <div class="modal-content">
        <h2>密诏：{{ currentChatMinister?.name }}</h2>
        <div class="chat-history">
          <div v-for="(msg, i) in currentChatMinister?.chat_history" :key="i" :class="'msg ' + (msg.role==='皇上' ? 'emperor' : 'minister')">
            <b>{{ msg.role }}:</b> {{ msg.content }}
          </div>
        </div>
        <input v-model="chatMsg" @keyup.enter="sendChat" placeholder="对大臣说些什么..." :disabled="chatting"/>
        <button @click="sendChat" :disabled="chatting">发送</button>
        <button @click="showChatModal = false">退下</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const state = ref(null)
const loading = ref(false)
const newEdict = ref('')
const edictsQueue = ref([])
const showReportModal = ref(false)
const lastReport = ref('')

const showChatModal = ref(false)
const currentChatMinister = ref(null)
const chatMsg = ref('')
const chatting = ref(false)

const formatMoney = (val) => {
  return (val / 10000).toFixed(1) + '万'
}

const formatReport = (text) => {
  return text.replace(/\n/g, '<br/>')
}

const fetchState = async () => {
  const res = await axios.get('/api/state')
  state.value = res.data
}

const saveGame = async () => {
  await axios.post('/api/save', { slot_id: 'manual' })
  alert('存档成功！')
}

const loadGame = async () => {
  try {
    const res = await axios.post('/api/load', { slot_id: 'manual' })
    if(res.data.status === 'ok') {
      state.value = res.data.new_state
      alert('读档成功！')
    } else {
      alert(res.data.message)
    }
  } catch (e) {
    alert('读档失败')
  }
}

const selectProvince = (prov) => {
  newEdict.value = `针对${prov.name}：`
}

const addEdict = () => {
  if (newEdict.value.trim()) {
    edictsQueue.value.push(newEdict.value.trim())
    newEdict.value = ''
  }
}

const advanceTurn = async () => {
  loading.value = true
  try {
    const res = await axios.post('/api/submit_edicts', { edicts: edictsQueue.value })
    if (res.data.status === 'ok') {
      state.value = res.data.new_state
      lastReport.value = res.data.report
      edictsQueue.value = [] // 清空诏书
      showReportModal.value = true
    }
  } catch (e) {
    alert('推演请求失败，请检查后端运行状态。')
  } finally {
    loading.value = false
  }
}

const chatMinister = (min) => {
  currentChatMinister.value = min
  showChatModal.value = true
}

const sendChat = async () => {
  if (!chatMsg.value.trim()) return
  chatting.value = true
  const msg = chatMsg.value
  chatMsg.value = ''

  // Optimistic UI
  currentChatMinister.value.chat_history.push({role: '皇上', content: msg})

  try {
    const res = await axios.post('/api/chat_minister', {
      minister_name: currentChatMinister.value.name,
      message: msg
    })
    currentChatMinister.value.chat_history.push({role: currentChatMinister.value.name, content: res.data.reply})
    fetchState() // sync state
  } catch (e) {
    alert('通信失败')
  } finally {
    chatting.value = false
  }
}

onMounted(() => {
  fetchState()
})
</script>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  background-color: #3b362a;
  border-bottom: 2px solid #5a4b31;
}
.stats span {
  margin-right: 20px;
  font-weight: bold;
  color: #ffcc00;
}
.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}
.provinces-panel {
  flex: 2;
  padding: 20px;
  background-color: #1e1c19;
  overflow-y: auto;
}
.provinces-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 15px;
}
.province-card {
  background-color: #363025;
  border: 1px solid #5a4b31;
  border-radius: 8px;
  padding: 10px;
  cursor: pointer;
  transition: transform 0.2s;
}
.province-card:hover {
  transform: scale(1.05);
}
.province-card h3 {
  margin-top: 0;
  color: #f5deb3;
}
.province-card.danger {
  border-color: #ff4444;
  background-color: #4a2525;
}
.right-panel {
  flex: 1;
  background-color: #2c2a26;
  border-left: 2px solid #5a4b31;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
}
.edicts-box textarea {
  width: 100%;
  height: 80px;
  background: #1e1c19;
  color: #e5e0d8;
  border: 1px solid #5a4b31;
}
.edict-queue li {
  margin-bottom: 5px;
}
.modal {
  position: fixed;
  top:0; left:0; width:100vw; height:100vh;
  background: rgba(0,0,0,0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.modal-content {
  background: #3b362a;
  padding: 30px;
  border: 3px solid #f5deb3;
  width: 60%;
  max-height: 80vh;
  overflow-y: auto;
}
.report-text {
  line-height: 1.6;
  font-size: 16px;
  margin-bottom: 20px;
}
.primary-btn {
  background: #aa0000;
  color: #fff;
  font-size: 18px;
  padding: 10px 20px;
  border: none;
  cursor: pointer;
}
.primary-btn:disabled {
  background: #555;
}
.chat-history {
  height: 300px;
  overflow-y: auto;
  background: #1e1c19;
  padding: 10px;
  margin-bottom: 10px;
}
.msg {
  margin-bottom: 10px;
  padding: 8px;
  border-radius: 4px;
}
.emperor { background: #4a3b2c; text-align: right; }
.minister { background: #2c3a4a; text-align: left; }
</style>
