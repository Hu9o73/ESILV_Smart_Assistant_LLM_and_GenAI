import Head from 'next/head';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import createDOMPurify from 'dompurify';
import { marked } from 'marked';

type Role = 'user' | 'assistant';

type AssistantMeta = {
  status: 'approved' | 'fallback' | 'error';
  attempts: number;
  reformulatedQuery: string | null;
  verifierFeedback: string | null;
};

type ChatMessage = {
  id: string;
  role: Role;
  content: string;
  createdAt: string;
  meta?: AssistantMeta;
};

type JobStatus = 'queued' | 'processing' | 'completed' | 'error' | null;

type JobCreateResponse = {
  job_id: string;
  status: 'queued';
};

type JobStatusResponse = {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'error';
  created_at: string;
  finished_at?: string | null;
  message?: {
    message: string;
    created_at: string;
    status: 'approved' | 'fallback';
    attempts: number;
    reformulated_query?: string | null;
    verifier_feedback?: string | null;
  } | null;
  error?: string | null;
};

const JOB_STATUS = Object.freeze({
  QUEUED: 'queued',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  ERROR: 'error',
} as const);

const JOB_POLL_INTERVAL_MS = 1500;
const MAX_POLL_DURATION_MS = 120000;

const normalizeBackendBase = (raw: string | undefined | null): string => {
  const fallback = '/api';
  if (!raw) return fallback;
  const trimmed = raw.trim().replace(/\/+$/, '');
  if (!trimmed) return fallback;
  if (trimmed.startsWith('http')) return trimmed;
  if (trimmed.startsWith('/')) return trimmed;
  return fallback;
};

const createId = (prefix: string) => {
  try {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
  } catch {
    // ignore
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
};

const initialAssistantMessage = (): ChatMessage => ({
  id: createId('assistant'),
  role: 'assistant',
  content:
    "Salut ! Je suis l'assistant du Pôle Léonard de Vinci. Pose tes questions sur la scolarité, les services du campus ou la vie associative.",
  createdAt: new Date().toISOString(),
});

const Index: React.FC = () => {
  const chatContainerRef = useRef<HTMLDivElement | null>(null);
  const messageInputRef = useRef<HTMLTextAreaElement | null>(null);
  const [passwordInput, setPasswordInput] = useState('');
  const [password, setPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [newMessage, setNewMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeJobStatus, setActiveJobStatus] = useState<JobStatus>(null);
  const [conversation, setConversation] = useState<ChatMessage[]>(() => [initialAssistantMessage()]);

  const backendBase = useMemo(
    () => normalizeBackendBase(process.env.NEXT_PUBLIC_BACKEND_URL),
    []
  );

  const sanitizer = useMemo(
    () => (typeof window === 'undefined' ? null : createDOMPurify(window)),
    []
  );

  const jobStatusLabel = useMemo(() => {
    if (activeJobStatus === JOB_STATUS.QUEUED) return "Message en file d'attente...";
    if (activeJobStatus === JOB_STATUS.PROCESSING) return 'Réflexion en cours...';
    return 'Réflexion en cours...';
  }, [activeJobStatus]);

  const suggestionChips = [
    'Quels sont les prochains événements associatifs ?',
    'Comment réserver une salle de travail au campus ?',
    'Qui contacter pour une question de scolarité ?',
  ];

  const formatTimestamp = (isoString: string) => {
    const date = new Date(isoString);
    return Number.isNaN(date.getTime())
      ? ''
      : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      if (chatContainerRef.current) {
        chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
      }
    });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation.length, isLoading]);

  useEffect(() => {
    if (isAuthenticated) {
      messageInputRef.current?.focus();
    }
  }, [isAuthenticated]);

  const validatePassword = () => {
    if (!passwordInput.trim()) {
      setPasswordError('Le mot de passe est requis.');
      return;
    }
    setPassword(passwordInput.trim());
    setPasswordInput('');
    setPasswordError('');
    setIsAuthenticated(true);
    messageInputRef.current?.focus();
  };

  const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  const buildJobCreationUrl = (messageContent: string) => {
    const search = new URLSearchParams({ message: messageContent, password });
    return `${backendBase}/message?${search.toString()}`;
  };

  const buildJobStatusUrl = (jobId: string) => {
    const search = new URLSearchParams({ password });
    return `${backendBase}/message/${jobId}?${search.toString()}`;
  };

  const requestJson = async (
    url: string,
    options: RequestInit = {},
    defaultErrorMessage = 'Une erreur est survenue.'
  ) => {
    let response: Response;

    try {
      response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {}),
        },
      });
    } catch (networkError) {
      console.error('[chat] network error:', networkError);
      throw new Error(defaultErrorMessage);
    }

    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error((payload as { detail?: string; error?: string })?.detail ?? defaultErrorMessage);
    }

    return payload;
  };

  const queueMessageJob = async (messageContent: string) => {
    const payload = (await requestJson(
      buildJobCreationUrl(messageContent),
      { method: 'POST' },
      "Impossible de mettre en file d'attente votre requête, merci de réessayer."
    )) as JobCreateResponse;

    const jobId = payload?.job_id;
    if (!jobId) throw new Error('Réponse invalide du serveur : identifiant de job manquant.');
    return jobId;
  };

  const pollJobUntilComplete = async (jobId: string, onStatusChange?: (status: JobStatus) => void) => {
    const deadline = Date.now() + MAX_POLL_DURATION_MS;
    let lastStatus: JobStatus = null;

    while (Date.now() < deadline) {
      const payload = (await requestJson(
        buildJobStatusUrl(jobId),
        {},
        "Impossible de récupérer l'état du traitement."
      )) as JobStatusResponse;

      const currentStatus = (payload?.status as JobStatus) ?? null;
      if (currentStatus && currentStatus !== lastStatus) {
        onStatusChange?.(currentStatus);
      }
      lastStatus = currentStatus;

      if (currentStatus === JOB_STATUS.COMPLETED) return payload;
      if (currentStatus === JOB_STATUS.ERROR) throw new Error(payload?.error ?? 'La génération a échoué.');
      if (currentStatus === JOB_STATUS.QUEUED || currentStatus === JOB_STATUS.PROCESSING) {
        await wait(JOB_POLL_INTERVAL_MS);
        continue;
      }

      throw new Error('Réponse inattendue du serveur, merci de réessayer.');
    }

    const timeoutMessage =
      lastStatus === JOB_STATUS.QUEUED
        ? "La file d'attente est temporairement saturée, merci de réessayer dans un instant."
        : "Le délai d'attente a été dépassé, merci de réessayer.";

    throw new Error(timeoutMessage);
  };

  const buildAssistantMeta = (payload: Partial<JobStatusResponse['message']> = {}): AssistantMeta => {
    const status = typeof payload?.status === 'string' ? payload.status : 'approved';
    const attempts = Number.isFinite(Number(payload?.attempts)) ? Number(payload?.attempts) : 1;
    const reformulatedQuery =
      typeof payload?.reformulated_query === 'string' && payload.reformulated_query.trim()
        ? payload.reformulated_query
        : null;
    const verifierFeedback =
      typeof payload?.verifier_feedback === 'string' && payload.verifier_feedback?.trim()
        ? payload.verifier_feedback
        : null;

    return {
      status: (status as AssistantMeta['status']) || 'approved',
      attempts,
      reformulatedQuery,
      verifierFeedback,
    };
  };

  const renderMarkdown = (rawText: string) => {
    const html = marked.parse(typeof rawText === 'string' ? rawText : '', { breaks: true });
    const safeHtml = typeof html === 'string' ? html : '';
    if (!sanitizer) return safeHtml;
    return sanitizer.sanitize(safeHtml);
  };

  const appendMessage = (payload: ChatMessage) => {
    setConversation((prev) => [...prev, payload]);
  };

  const resetConversation = () => {
    setNewMessage('');
    setErrorMessage('');
    setConversation([initialAssistantMessage()]);
    requestAnimationFrame(() => messageInputRef.current?.focus());
  };

  const applySuggestion = (prompt: string) => {
    setNewMessage(prompt);
    requestAnimationFrame(() => messageInputRef.current?.focus());
  };

  const sendMessage = async () => {
    const trimmedMessage = newMessage.trim();
    if (!trimmedMessage || isLoading) return;
    if (!isAuthenticated) {
      setErrorMessage('Veuillez entrer le mot de passe avant de discuter.');
      return;
    }

    const userMessage: ChatMessage = {
      id: createId('user'),
      role: 'user',
      content: trimmedMessage,
      createdAt: new Date().toISOString(),
    };

    appendMessage(userMessage);
    setNewMessage('');
    setErrorMessage('');
    setIsLoading(true);
    setActiveJobStatus(JOB_STATUS.QUEUED);

    try {
      const jobId = await queueMessageJob(trimmedMessage);
      const jobResult = await pollJobUntilComplete(jobId, (status) => setActiveJobStatus(status));

      let assistantMessage = jobResult?.message ?? null;
      if (assistantMessage && typeof assistantMessage === 'string') {
        assistantMessage = {
          message: assistantMessage,
          created_at: new Date().toISOString(),
          status: 'approved',
          attempts: 1,
        };
      }

      if (!assistantMessage || !assistantMessage.message) {
        throw new Error('Le serveur a terminé sans réponse valide.');
      }

      appendMessage({
        id: createId('assistant'),
        role: 'assistant',
        content: assistantMessage.message,
        createdAt: assistantMessage?.created_at ?? new Date().toISOString(),
        meta: buildAssistantMeta(assistantMessage),
      });
    } catch (error) {
      const message = (error as Error)?.message ?? 'Une erreur est survenue pendant la génération.';
      setErrorMessage(message);
      appendMessage({
        id: createId('assistant'),
        role: 'assistant',
        content: `⚠️ ${message}`,
        createdAt: new Date().toISOString(),
        meta: {
          status: 'error',
          attempts: 0,
          reformulatedQuery: null,
          verifierFeedback: message,
        },
      });
    } finally {
      setIsLoading(false);
      setActiveJobStatus(null);
      requestAnimationFrame(() => messageInputRef.current?.focus());
    }
  };

  const handleSubmitOnEnter = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      <Head>
        <title>Chat&apos;akon</title>
        <link rel="icon" type="image/vnd.microsoft.icon" href="/favicon.ico" />
      </Head>

      {!isAuthenticated && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm px-4">
          <div className="w-full max-w-sm space-y-4 rounded-3xl bg-white p-8 text-center shadow-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">Accès</p>
            <h2 className="text-lg font-semibold text-slate-800">Entrez le mot de passe</h2>
            <p className="text-sm text-slate-500">
              Le même mot de passe que celui attendu par le backend `/message`.
            </p>
            <input
              value={passwordInput}
              onChange={(e) => setPasswordInput(e.target.value)}
              type="password"
              placeholder="Mot de passe"
              className="w-full rounded-xl border border-slate-300 px-4 py-2 text-sm text-slate-800 outline-none focus:border-sky-400 focus:ring-1 focus:ring-sky-400"
              onKeyDown={(e) => e.key === 'Enter' && validatePassword()}
            />
            {passwordError && <p className="text-sm text-rose-500">{passwordError}</p>}
            <button
              onClick={validatePassword}
              className="w-full rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-sky-400"
            >
              Valider
            </button>
          </div>
        </div>
      )}

      <div className="flex min-h-screen flex-col bg-gradient-to-br from-slate-50 via-white to-sky-50">
        <header className="border-b border-white/70 bg-white/90 backdrop-blur">
          <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-4 px-6 py-6">
            <div className="flex items-center gap-3">
              <img
                src="/logo.png"
                alt="Chat'akon"
                className="h-11 w-11 rounded-2xl border border-slate-100 object-cover shadow-sm"
                loading="lazy"
              />
              <div>
                <p className="text-lg font-semibold tracking-tight text-slate-900">Chat&apos;akon</p>
                <p className="text-sm text-slate-500">
                  Pose tes questions sur la vie étudiante, les cours ou les services du Pôle.
                </p>
              </div>
            </div>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-sky-400/70 hover:text-sky-600"
              onClick={resetConversation}
            >
              <span className="text-xs">↺</span>
              Nouvelle discussion
            </button>
          </div>
        </header>

        <main className="flex flex-1 justify-center px-4 py-10 sm:px-6 lg:px-8">
          <section className="flex w-full max-w-5xl flex-col gap-6">
            <div className="rounded-3xl border border-white/60 bg-white p-6 shadow-2xl shadow-slate-200/60 backdrop-blur">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">
                    Assistant étudiant
                  </p>
                  <h2 className="text-xl font-semibold text-slate-900">Bonjour !</h2>
                  <p className="text-sm text-slate-500">
                    Laisse un message pour obtenir de l&apos;aide sur les emplois du temps, la vie associative
                    ou les services du campus à La Défense.
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {suggestionChips.map((chip) => (
                      <button
                        key={chip}
                        type="button"
                        className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-100/80 px-3 py-1 text-xs font-medium text-slate-600 transition hover:border-sky-300/70 hover:text-sky-600"
                        onClick={() => applySuggestion(chip)}
                      >
                        ✦ {chip}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-xs text-slate-600 shadow-sm">
                  <p className="font-semibold text-sky-700">Comment ça marche ?</p>
                  <ul className="mt-2 space-y-1 text-slate-600">
                    <li>• Les messages sont mis en file, puis traités par le backend agentique.</li>
                    <li>• Les réponses sont validées par un agent de vérification.</li>
                    <li>• Les métadonnées de validation sont affichées si besoin.</li>
                  </ul>
                </div>
              </div>
            </div>

            <section className="flex min-h-[28rem] flex-col overflow-hidden rounded-3xl border border-white/60 bg-white shadow-2xl shadow-slate-200/60 backdrop-blur">
              <div className="border-b border-slate-200 px-6 py-5">
                <p className="text-xs font-medium uppercase tracking-[0.25em] text-slate-500">Fil de discussion</p>
                <p className="mt-2 text-sm text-slate-500">
                  L&apos;assistant garde le contexte tant que la session reste ouverte.
                </p>
              </div>

              <div ref={chatContainerRef} className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
                {conversation.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-xl px-5 py-4 text-sm leading-relaxed shadow-lg backdrop-blur ${
                        message.role === 'user'
                          ? 'rounded-3xl rounded-br-sm bg-gradient-to-br from-sky-500 to-sky-400 text-white shadow-sky-200/80'
                          : 'rounded-3xl rounded-bl-sm bg-slate-100 text-slate-800 shadow-slate-200/80'
                      }`}
                    >
                      <div
                        className="space-y-3 whitespace-pre-wrap break-words text-sm leading-relaxed [&_a]:text-sky-600 [&_a]:underline [&_code]:rounded [&_code]:bg-slate-200/70 [&_code]:px-1 [&_code]:py-0.5 [&_strong]:text-slate-900 [&_ul]:ml-4 [&_ul]:list-disc [&_ol]:ml-4 [&_ol]:list-decimal"
                        dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
                      />
                      {message.role === 'assistant' && message.meta && (
                        <div className="mt-3 space-y-1 text-[11px] leading-relaxed text-slate-500">
                          {message.meta.status === 'fallback' && (
                            <p className="text-rose-500">
                              Cette réponse n&apos;a pas pu être validée automatiquement.
                              {message.meta.verifierFeedback && (
                                <span> Motif : {message.meta.verifierFeedback}</span>
                              )}
                            </p>
                          )}
                          {message.meta.status === 'approved' && message.meta.attempts > 1 && (
                            <p>Validée après {message.meta.attempts} tentatives.</p>
                          )}
                          {message.meta.reformulatedQuery && (
                            <p className="text-slate-400">Reformulation : {message.meta.reformulatedQuery}</p>
                          )}
                        </div>
                      )}
                      <span className="mt-3 block text-[11px] uppercase tracking-[0.25em] text-slate-400/90">
                        {formatTimestamp(message.createdAt)}
                      </span>
                    </div>
                  </div>
                ))}

                {isLoading && (
                  <div className="flex justify-start">
                    <div className="flex items-center gap-2 rounded-3xl rounded-bl-sm bg-slate-100 px-5 py-3 text-sm text-slate-500 shadow-lg shadow-slate-200/80 backdrop-blur">
                      <span className="relative flex h-2.5 w-2.5">
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-sky-400/70 opacity-75" />
                        <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-sky-400" />
                      </span>
                      {jobStatusLabel}
                    </div>
                  </div>
                )}
              </div>

              <form className="border-t border-slate-200 p-6" onSubmit={(e) => e.preventDefault()}>
                <div className="rounded-3xl border border-slate-200 bg-slate-50 transition focus-within:border-sky-400/60 focus-within:ring-2 focus-within:ring-sky-400/15">
                  <textarea
                    ref={messageInputRef}
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    className="h-28 w-full resize-none rounded-3xl border-0 bg-transparent px-5 py-4 text-sm leading-relaxed text-slate-800 outline-none placeholder:text-slate-400"
                    placeholder="Ex: Quels sont les horaires du Learning Center cette semaine ?"
                    rows={4}
                    onKeyDown={handleSubmitOnEnter}
                  />
                  <div className="flex flex-col gap-3 px-5 pb-4 sm:flex-row sm:items-center sm:justify-between">
                    {errorMessage ? (
                      <p className="text-sm text-rose-500">{errorMessage}</p>
                    ) : (
                      <p className="text-xs text-slate-400">
                        Astuce : Entrée pour envoyer, Shift + Entrée pour une nouvelle ligne.
                      </p>
                    )}
                    <button
                      type="button"
                      className="inline-flex items-center gap-2 rounded-full bg-sky-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-300/80"
                      disabled={isLoading || !newMessage.trim()}
                      onClick={sendMessage}
                    >
                      {!isLoading ? (
                        <>
                          <span>Envoyer</span>
                        </>
                      ) : (
                        <span className="flex items-center gap-2">
                          <span className="h-2.5 w-2.5 animate-spin rounded-full border-2 border-white/60 border-t-transparent" />
                          Envoi
                        </span>
                      )}
                    </button>
                  </div>
                </div>
              </form>
            </section>
          </section>
        </main>
      </div>
    </>
  );
};

export default Index;
