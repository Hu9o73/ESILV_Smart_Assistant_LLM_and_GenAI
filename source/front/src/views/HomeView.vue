<template>
  <div class="flex min-h-screen flex-col bg-slate-50 text-slate-900">
    <!-- 🔒 Password modal -->
    <div
      v-if="!isAuthenticated"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
    >
      <div class="rounded-3xl bg-white p-8 shadow-2xl w-full max-w-sm text-center space-y-4">
        <h2 class="text-lg font-semibold text-slate-800">Entrez le mot de passe</h2>
        <input
          v-model="passwordInput"
          type="password"
          placeholder="Mot de passe"
          class="w-full rounded-xl border border-slate-300 px-4 py-2 text-sm focus:border-sky-400 focus:ring-1 focus:ring-sky-400 outline-none"
          @keyup.enter="validatePassword"
        />
        <p v-if="passwordError" class="text-sm text-rose-500">{{ passwordError }}</p>
        <button
          @click="validatePassword"
          class="w-full rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-sky-400"
        >
          Valider
        </button>
      </div>
    </div>

    <header class="border-b border-slate-200/80 bg-white/90 backdrop-blur">
      <div class="mx-auto flex w-full max-w-4xl flex-wrap items-center justify-between gap-4 px-6 py-6">
        <div class="flex items-center gap-3">
          <img
            :src="logoSrc"
            alt="Chat'akon"
            class="h-11 w-11 rounded-2xl border border-slate-100 object-cover shadow-sm"
            loading="lazy"
          />
          <div>
            <p class="text-lg font-semibold tracking-tight text-slate-900">Chat'akon</p>
            <p class="text-sm text-slate-500">Pose tes questions sur la vie étudiante, les cours ou les services du Pôle.</p>
          </div>
        </div>
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-sky-400/70 hover:text-sky-600"
          @click="resetConversation"
        >
          <i class="fas fa-rotate-left text-xs"></i>
          Nouvelle discussion
        </button>
      </div>
    </header>

    <main class="flex flex-1 justify-center px-4 py-10 sm:px-6 lg:px-8">
      <section class="flex w-full max-w-4xl flex-col gap-6">
        <div class="rounded-3xl border border-white/60 bg-white p-6 shadow-2xl shadow-slate-200/60 backdrop-blur">
          <h2 class="text-base font-semibold text-slate-800">Bonjour !</h2>
          <p class="mt-2 text-sm text-slate-500">
            Laisse un message pour obtenir de l'aide sur les emplois du temps, la vie associative ou les services du campus à La Défense.
          </p>
          <div class="mt-4 flex flex-wrap gap-2">
            <button
              v-for="chip in suggestionChips"
              :key="chip"
              type="button"
              class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-100/80 px-3 py-1 text-xs font-medium text-slate-600 transition hover:border-sky-300/70 hover:text-sky-600"
              @click="applySuggestion(chip)"
            >
              <i class="fas fa-wand-magic-sparkles text-[10px]"></i>
              {{ chip }}
            </button>
          </div>
        </div>

        <section class="flex min-h-[28rem] flex-col overflow-hidden rounded-3xl border border-white/60 bg-white shadow-2xl shadow-slate-200/60 backdrop-blur">
          <div class="border-b border-slate-200 px-6 py-5">
            <p class="text-xs font-medium uppercase tracking-[0.25em] text-slate-500">Fil de discussion</p>
            <p class="mt-2 text-sm text-slate-500">L'assistant garde le contexte tant que la session reste ouverte.</p>
          </div>

          <div ref="chatContainer" class="flex-1 space-y-4 overflow-y-auto px-6 py-6">
            <template v-for="message in conversation" :key="message.id">
              <div :class="[message.role === 'user' ? 'justify-end' : 'justify-start', 'flex']">
                <div
                  :class="[
                    message.role === 'user'
                      ? 'bg-gradient-to-br from-sky-500 to-sky-400 text-white shadow-sky-200/80'
                      : 'bg-slate-100 text-slate-800 shadow-slate-200/80',
                    message.role === 'user' ? 'rounded-3xl rounded-br-sm' : 'rounded-3xl rounded-bl-sm',
                    'max-w-xl px-5 py-4 text-sm leading-relaxed shadow-lg backdrop-blur'
                  ]"
                >
                  <div
                    class="space-y-3 whitespace-pre-wrap break-words text-sm leading-relaxed [&_a]:text-sky-600 [&_a]:underline [&_code]:rounded [&_code]:bg-slate-200/70 [&_code]:px-1 [&_code]:py-0.5 [&_strong]:text-slate-900 [&_ul]:ml-4 [&_ul]:list-disc [&_ol]:ml-4 [&_ol]:list-decimal"
                    v-html="renderMarkdown(message.content)"
                  ></div>
                  <div
                    v-if="message.role === 'assistant' && message.meta"
                    class="mt-3 space-y-1 text-[11px] leading-relaxed text-slate-400"
                  >
                    <p v-if="message.meta.status === 'fallback'" class="text-rose-500">
                      Cette réponse n'a pas pu être validée automatiquement.
                      <span v-if="message.meta.verifierFeedback">
                        Motif : {{ message.meta.verifierFeedback }}
                      </span>
                    </p>
                    <p v-else-if="message.meta.attempts > 1">
                      Validée après {{ message.meta.attempts }} tentatives.
                    </p>
                  </div>
                  <span class="mt-3 block text-[11px] uppercase tracking-[0.25em] text-slate-400/90">
                    {{ formatTimestamp(message.createdAt) }}
                  </span>
                </div>
              </div>
            </template>

            <div v-if="isLoading" class="flex justify-start">
              <div
                class="flex items-center gap-2 rounded-3xl rounded-bl-sm bg-slate-100 px-5 py-3 text-sm text-slate-500 shadow-lg shadow-slate-200/80 backdrop-blur"
              >
                <span class="relative flex h-2.5 w-2.5">
                  <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-sky-400/70 opacity-75"></span>
                  <span class="relative inline-flex h-2.5 w-2.5 rounded-full bg-sky-400"></span>
                </span>
                {{ jobStatusLabel }}
              </div>
            </div>
          </div>

          <form class="border-t border-slate-200 p-6" @submit.prevent="sendMessage">
            <div
              class="rounded-3xl border border-slate-200 bg-slate-50 transition focus-within:border-sky-400/60 focus-within:ring-2 focus-within:ring-sky-400/15"
            >
              <textarea
                ref="messageInput"
                v-model="newMessage"
                class="h-28 w-full resize-none rounded-3xl border-0 bg-transparent px-5 py-4 text-sm leading-relaxed text-slate-800 outline-none placeholder:text-slate-400"
                placeholder="Ex: Quels sont les horaires du Learning Center cette semaine ?"
                rows="4"
                @keydown.enter.exact.prevent="handleSubmitOnEnter"
              ></textarea>
              <div class="flex flex-col gap-3 px-5 pb-4 sm:flex-row sm:items-center sm:justify-between">
                <p v-if="errorMessage" class="text-sm text-rose-500">{{ errorMessage }}</p>
                <button
                  type="submit"
                  class="inline-flex items-center gap-2 rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-300/80"
                  :disabled="isLoading || !newMessage.trim()"
                >
                  <template v-if="!isLoading">
                    <span>Envoyer</span>
                    <i class="fas fa-paper-plane text-xs"></i>
                  </template>
                  <template v-else>
                    <span class="flex items-center gap-2">
                      <span class="h-2.5 w-2.5 animate-spin rounded-full border-2 border-white/60 border-t-transparent"></span>
                      Envoi
                    </span>
                  </template>
                </button>
              </div>
            </div>
          </form>
        </section>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import SuperLogo from '@/assets/logos/logo.png'

// === 🔒 Password handling ===
const password = ref('')
const passwordInput = ref('')
const passwordError = ref('')
const isAuthenticated = ref(false)

const validatePassword = () => {
  if (passwordInput.value.trim() === '') {
    passwordError.value = 'Le mot de passe est requis.'
    return
  }
  password.value = passwordInput.value.trim()
  isAuthenticated.value = true
  passwordError.value = ''
}

// ============================

const rawBackendUrl = (import.meta.env.VITE_BACKEND_URL ?? '').trim()
const normalizedBackendUrl = rawBackendUrl.replace(/\/+$/, '')
const RELATIVE_API_BASE = '/api'

let backendBase = ''

if (normalizedBackendUrl) {
  if (normalizedBackendUrl.startsWith('/')) {
    backendBase = normalizedBackendUrl
  } else {
    try {
      backendBase = new URL(normalizedBackendUrl).toString().replace(/\/+$/, '')
    } catch (error) {
      console.warn('[home-view] Ignoring invalid VITE_BACKEND_URL value:', normalizedBackendUrl, error)
    }
  }
}

if (!backendBase) {
  backendBase = RELATIVE_API_BASE
}

const chatContainer = ref(null)
const messageInput = ref(null)
const newMessage = ref('')
const isLoading = ref(false)
const errorMessage = ref('')
const activeJobStatus = ref(null)
const jobStatusLabel = computed(() => {
  if (activeJobStatus.value === JOB_STATUS.QUEUED) {
    return "Message en file d'attente..."
  }
  return 'Réflexion en cours...'
})

const suggestionChips = [
  'Quels sont les prochains événements associatifs ?',
  'Comment réserver une salle de travail au campus ?',
  'Qui contacter pour une question de scolarité ?'
]

const JOB_POLL_INTERVAL_MS = 1500
const MAX_POLL_DURATION_MS = 120000

const JOB_STATUS = Object.freeze({
  QUEUED: 'queued',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  ERROR: 'error'
})

const buildAssistantMeta = (payload = {}) => {
  const status = typeof payload.status === 'string' ? payload.status : 'approved'
  const attempts = Number.isFinite(Number(payload.attempts)) ? Number(payload.attempts) : 1
  const reformulatedQuery =
    typeof payload.reformulated_query === 'string' && payload.reformulated_query.trim() !== ''
      ? payload.reformulated_query
      : null
  const verifierFeedback =
    typeof payload.verifier_feedback === 'string' && payload.verifier_feedback.trim() !== ''
      ? payload.verifier_feedback
      : null

  return {
    status,
    attempts,
    reformulatedQuery,
    verifierFeedback
  }
}

const createId = (prefix) => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  const randomSuffix = Math.random().toString(16).slice(2, 10)
  return `${prefix}-${Date.now()}-${randomSuffix}`
}

const initialAssistantMessage = () => ({
  id: createId('assistant'),
  role: 'assistant',
  content:
    "Salut ! Je suis l'assistant du Pôle Léonard de Vinci. Je peux t'aider pour la scolarité, la vie de campus ou l'organisation de tes études.",
  createdAt: new Date().toISOString()
})

const conversation = ref([initialAssistantMessage()])
const logoSrc = SuperLogo

const formatTimestamp = (isoString) => {
  const date = new Date(isoString)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const scrollToBottom = () => nextTick(() => {
  if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight
})

watch(conversation, scrollToBottom, { deep: true })

// === 🔒 Modified to include password ===
const buildJobCreationUrl = (messageContent) => {
  const search = new URLSearchParams({ message: messageContent, password: password.value })
  return backendBase ? `${backendBase}/message?${search.toString()}` : `/message?${search.toString()}`
}

const buildJobStatusUrl = (jobId) => {
  const search = new URLSearchParams({ password: password.value })
  return backendBase ? `${backendBase}/message/${jobId}?${search.toString()}` : `/message/${jobId}?${search.toString()}`
}
// ========================================

const renderMarkdown = (rawText) =>
  DOMPurify.sanitize(marked.parse(typeof rawText === 'string' ? rawText : '', { breaks: true }))
const appendMessage = (payload) => conversation.value.push(payload)

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const requestJson = async (url, options = {}, defaultErrorMessage = 'Une erreur est survenue.') => {
  let response

  try {
    response = await fetch(url, options)
  } catch (networkError) {
    console.error('[home-view] network error:', networkError)
    throw new Error(defaultErrorMessage)
  }

  const payload = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(payload?.detail ?? payload?.error ?? defaultErrorMessage)
  }

  return payload
}

const queueMessageJob = async (messageContent) => {
  const payload = await requestJson(
    buildJobCreationUrl(messageContent),
    { method: 'POST' },
    "Impossible de mettre en file d'attente votre requête, merci de réessayer."
  )

  const jobId = payload?.job_id
  if (!jobId) {
    throw new Error('Réponse invalide du serveur : identifiant de job manquant.')
  }

  return jobId
}

const pollJobUntilComplete = async (jobId, onStatusChange = () => {}) => {
  const deadline = Date.now() + MAX_POLL_DURATION_MS
  let lastKnownStatus = null

  while (Date.now() < deadline) {
    const payload = await requestJson(
      buildJobStatusUrl(jobId),
      {},
      "Impossible de récupérer l'état du traitement."
    )

    const currentStatus = payload?.status ?? null
    if (currentStatus && currentStatus !== lastKnownStatus && typeof onStatusChange === 'function') {
      onStatusChange(currentStatus)
    }
    lastKnownStatus = currentStatus

    if (currentStatus === JOB_STATUS.COMPLETED) {
      return payload
    }

    if (currentStatus === JOB_STATUS.ERROR) {
      throw new Error(payload?.error ?? 'La génération a échoué, veuillez réessayer.')
    }

    if (currentStatus === JOB_STATUS.QUEUED || currentStatus === JOB_STATUS.PROCESSING) {
      await wait(JOB_POLL_INTERVAL_MS)
      continue
    }

    throw new Error('Réponse inattendue du serveur, merci de réessayer.')
  }

  const timeoutMessage =
    lastKnownStatus === JOB_STATUS.QUEUED
      ? "La file d'attente est temporairement saturée, merci de réessayer dans un instant."
      : "Le délai d'attente a été dépassé, merci de réessayer."

  throw new Error(timeoutMessage)
}

const applySuggestion = (prompt) => {
  newMessage.value = prompt
  nextTick(() => messageInput.value?.focus())
}

const handleSubmitOnEnter = () => {
  if (!isLoading.value && newMessage.value.trim() !== '') sendMessage()
}

const resetConversation = () => {
  newMessage.value = ''
  errorMessage.value = ''
  conversation.value = [initialAssistantMessage()]
  nextTick(() => messageInput.value?.focus())
}

const sendMessage = async () => {
  const trimmedMessage = newMessage.value.trim()
  if (trimmedMessage === '' || isLoading.value) return
  if (!isAuthenticated.value) {
    errorMessage.value = 'Veuillez entrer le mot de passe avant de discuter.'
    return
  }

  const userMessage = {
    id: createId('user'),
    role: 'user',
    content: trimmedMessage,
    createdAt: new Date().toISOString()
  }

  appendMessage(userMessage)
  newMessage.value = ''
  errorMessage.value = ''
  isLoading.value = true
  activeJobStatus.value = JOB_STATUS.QUEUED

  try {
    const jobId = await queueMessageJob(trimmedMessage)
    const jobResult = await pollJobUntilComplete(jobId, (status) => {
      activeJobStatus.value = status
    })

    let assistantMessage = jobResult?.message ?? null
    if (assistantMessage && typeof assistantMessage === 'string') {
      assistantMessage = {
        message: assistantMessage,
        created_at: new Date().toISOString(),
        status: 'approved',
        attempts: jobResult?.attempts ?? 1
      }
    }

    if (!assistantMessage || !assistantMessage.message) {
      throw new Error('Le serveur a terminé sans réponse valide.')
    }

    appendMessage({
      id: createId('assistant'),
      role: 'assistant',
      content: assistantMessage?.message ?? 'I could not generate a response, please try again.',
      createdAt: assistantMessage?.created_at ?? new Date().toISOString(),
      meta: buildAssistantMeta(assistantMessage ?? {})
    })
  } catch (error) {
    errorMessage.value = error.message ?? 'Something went wrong while contacting the agent.'
    appendMessage({
      id: createId('assistant'),
      role: 'assistant',
      content: `⚠️ ${errorMessage.value}`,
      createdAt: new Date().toISOString(),
      meta: buildAssistantMeta({
        status: 'error',
        attempts: 0,
        verifier_feedback: errorMessage.value
      })
    })
  } finally {
    isLoading.value = false
    activeJobStatus.value = null
    nextTick(() => messageInput.value?.focus())
  }
}
</script>
