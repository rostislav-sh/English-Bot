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
	return pollUntil(test, () => getTest(test.id), (t) => t.status !== 'generating', opts)
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
	return pollUntil(
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
