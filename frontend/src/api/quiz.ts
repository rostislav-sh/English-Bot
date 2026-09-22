import { getJson, postJson } from './http'
import type {
	AttemptHistoryItemOut,
	AttemptOut,
	MonthlyStatOut,
	RequestTestIn,
	SubmitAnswersIn,
	TestOut,
	TopicOut,
} from './types/quiz'

function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => {
		window.setTimeout(resolve, ms)
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
	opts?: { intervalMs?: number; maxAttempts?: number },
): Promise<TestOut> {
	const intervalMs = opts?.intervalMs ?? 1000
	const maxAttempts = opts?.maxAttempts ?? 20
	let current = test
	let attempt = 0

	while (current.status === 'generating' && attempt < maxAttempts) {
		await sleep(intervalMs)
		current = await getTest(current.id)
		attempt += 1
	}

	return current
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
	opts?: { intervalMs?: number; maxAttempts?: number },
): Promise<AttemptOut> {
	const intervalMs = opts?.intervalMs ?? 1000
	const maxAttempts = opts?.maxAttempts ?? 20
	let current = attempt
	let poll = 0

	while (current.recommendation_status === 'pending' && poll < maxAttempts) {
		await sleep(intervalMs)
		current = await getAttempt(current.id)
		poll += 1
	}

	return current
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

export async function getMonthlyStats(months = 12): Promise<MonthlyStatOut[]> {
	const params = new URLSearchParams({ months: String(months) })
	return getJson<MonthlyStatOut[]>(`/attempts/stats/monthly?${params.toString()}`)
}
