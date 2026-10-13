import { apiUrl } from './config'
import { ApiError, getJson, postJson } from './http'
import type {
	AttemptHistoryItemOut,
	AttemptOut,
	MonthlyStatOut,
	RequestTestIn,
	SubmitAnswersIn,
	TestOut,
	TopicOut,
} from './types/quiz'

// Дедлайн ожидания: с запасом покрывает soft-лимит LLM-таски (~52 с)
// плюс один ретрай Celery и ожидание в очереди воркера.
const POLL_TIMEOUT_MS = 120_000
const POLL_MAX_INTERVAL_MS = 3000
// Сколько сетевых ошибок / 5xx подряд терпим, прежде чем сдаться.
const POLL_MAX_TRANSIENT_ERRORS = 3

export type WaitOpts = { signal?: AbortSignal; timeoutMs?: number }
export type WaitResult<T> = { value: T; timedOut: boolean }

function abortError(): DOMException {
	return new DOMException('Polling aborted', 'AbortError')
}

export function isAbortError(err: unknown): boolean {
	return err instanceof DOMException && err.name === 'AbortError'
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
	return new Promise((resolve, reject) => {
		if (signal?.aborted) {
			reject(abortError())
			return
		}
		const onAbort = () => {
			window.clearTimeout(timer)
			reject(abortError())
		}
		const timer = window.setTimeout(() => {
			signal?.removeEventListener('abort', onAbort)
			resolve()
		}, ms)
		signal?.addEventListener('abort', onAbort, { once: true })
	})
}

function isTransientError(err: unknown): boolean {
	return err instanceof ApiError && (err.status === 0 || err.status >= 500)
}

/**
 * Опрашивает load(), пока isDone не вернёт true или не истечёт дедлайн.
 * Интервал растёт 1 → 2 → 3 с. По дедлайну не бросает ошибку, а возвращает
 * timedOut=true — страница сама решает, предложить ли подождать ещё.
 * При abort бросает AbortError (см. isAbortError).
 */
export async function pollUntil<T>(
	initial: T,
	load: () => Promise<T>,
	isDone: (value: T) => boolean,
	opts?: WaitOpts,
): Promise<WaitResult<T>> {
	const signal = opts?.signal
	const deadline = Date.now() + (opts?.timeoutMs ?? POLL_TIMEOUT_MS)
	let current = initial
	let intervalMs = 1000
	let failures = 0

	while (!isDone(current)) {
		const remaining = deadline - Date.now()
		if (remaining <= 0) return { value: current, timedOut: true }

		await sleep(Math.min(intervalMs, remaining), signal)
		intervalMs = Math.min(intervalMs + 1000, POLL_MAX_INTERVAL_MS)

		try {
			current = await load()
			failures = 0
		} catch (err) {
			// Единичный сбой сети не должен обрывать долгое ожидание.
			failures += 1
			if (!isTransientError(err) || failures >= POLL_MAX_TRANSIENT_ERRORS) throw err
		}
		// requestJson не принимает signal: уже начатый запрос доживает,
		// но его результат после abort отбрасываем.
		if (signal?.aborted) throw abortError()
	}

	return { value: current, timedOut: false }
}

type StatusEventOutcome = 'event' | 'error' | 'timeout'

/**
 * Открывает SSE-поток и ждёт одно событие `status` (бэкенд: src/api/sse.py).
 * Любая ошибка потока (401/404, обрыв, Redis недоступен, закрытие сервером)
 * → 'error': автопереподключение EventSource не используем, вызывающий
 * откатывается на polling.
 */
function listenForStatusEvent(
	path: string,
	timeoutMs: number,
	signal?: AbortSignal,
): Promise<StatusEventOutcome> {
	return new Promise((resolve, reject) => {
		if (signal?.aborted) {
			reject(abortError())
			return
		}
		// withCredentials — чтобы ушла access-cookie (API на другом origin).
		const source = new EventSource(apiUrl(path), { withCredentials: true })
		const finish = (done: () => void) => {
			source.close()
			window.clearTimeout(timer)
			signal?.removeEventListener('abort', onAbort)
			done()
		}
		const onAbort = () => finish(() => reject(abortError()))
		const timer = window.setTimeout(() => finish(() => resolve('timeout')), timeoutMs)
		// Событие именованное (`event: status`) — onmessage его не получит.
		source.addEventListener('status', () => finish(() => resolve('event')))
		source.onerror = () => finish(() => resolve('error'))
		signal?.addEventListener('abort', onAbort, { once: true })
	})
}

/**
 * Ждёт окончания генерации: сначала через SSE, при любой проблеме — polling
 * на оставшееся до дедлайна время. Контракт тот же, что у pollUntil.
 */
async function waitWithEvents<T>(
	eventsPath: string,
	initial: T,
	load: () => Promise<T>,
	isDone: (value: T) => boolean,
	opts?: WaitOpts,
): Promise<WaitResult<T>> {
	if (isDone(initial)) return { value: initial, timedOut: false }
	if (typeof EventSource === 'undefined') return pollUntil(initial, load, isDone, opts)

	const signal = opts?.signal
	const deadline = Date.now() + (opts?.timeoutMs ?? POLL_TIMEOUT_MS)
	let current = initial

	const outcome = await listenForStatusEvent(eventsPath, deadline - Date.now(), signal)
	if (outcome === 'event') {
		// Событие — только сигнал «перечитай», данные берём обычным GET.
		try {
			current = await load()
			if (signal?.aborted) throw abortError()
			if (isDone(current)) return { value: current, timedOut: false }
		} catch (err) {
			if (isAbortError(err) || !isTransientError(err)) throw err
		}
	}

	// 'error' / 'timeout' / событие без финального статуса → polling на остаток.
	// На 'timeout' остаток ≈ 0, и pollUntil сразу вернёт timedOut=true.
	// Первый GET в pollUntil при истёкшем токене сделает refresh (requestJson).
	return pollUntil(current, load, isDone, {
		signal,
		timeoutMs: Math.max(0, deadline - Date.now()),
	})
}

export async function listTopics(): Promise<TopicOut[]> {
	return getJson<TopicOut[]>('/topics')
}

export async function requestTest(data: RequestTestIn): Promise<TestOut> {
	return postJson<TestOut, RequestTestIn>('/tests', data)
}

export async function getTest(testId: number): Promise<TestOut> {
	return getJson<TestOut>(`/tests/${testId}`)
}

export async function waitForTestReady(
	test: TestOut,
	opts?: WaitOpts,
): Promise<WaitResult<TestOut>> {
	return waitWithEvents(
		`/tests/${test.id}/events`,
		test,
		() => getTest(test.id),
		(t) => t.status !== 'generating',
		opts,
	)
}

export async function submitTest(
	testId: number,
	data: SubmitAnswersIn,
): Promise<AttemptOut> {
	return postJson<AttemptOut, SubmitAnswersIn>(`/tests/${testId}/submit`, data)
}

export async function getAttempt(attemptId: number): Promise<AttemptOut> {
	return getJson<AttemptOut>(`/attempts/${attemptId}`)
}

export async function waitForRecommendation(
	attempt: AttemptOut,
	opts?: WaitOpts,
): Promise<WaitResult<AttemptOut>> {
	return waitWithEvents(
		`/attempts/${attempt.id}/events`,
		attempt,
		() => getAttempt(attempt.id),
		(a) => a.recommendation_status !== 'pending',
		opts,
	)
}

export async function listAttempts(
	limit = 20,
	offset = 0,
): Promise<AttemptHistoryItemOut[]> {
	const params = new URLSearchParams({
		limit: String(limit),
		offset: String(offset),
	})
	return getJson<AttemptHistoryItemOut[]>(`/attempts?${params.toString()}`)
}

export async function listAllAttempts(pageSize = 100): Promise<AttemptHistoryItemOut[]> {
	const items: AttemptHistoryItemOut[] = []
	for (let offset = 0; offset < 1000; offset += pageSize) {
		const page = await listAttempts(pageSize, offset)
		items.push(...page)
		if (page.length < pageSize) break
	}
	return items
}

export async function getMonthlyStats(months = 12): Promise<MonthlyStatOut[]> {
	const params = new URLSearchParams({ months: String(months) })
	return getJson<MonthlyStatOut[]>(`/attempts/stats/monthly?${params.toString()}`)
}
