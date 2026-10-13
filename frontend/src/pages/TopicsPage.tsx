import type { FormEvent } from 'react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/http'
import { isAbortError, listTopics, requestTest, waitForTestReady } from '../api/quiz'
import BackLink from '../components/BackLink'
import type { TestOut, TopicOut } from '../api/types/quiz'

export default function TopicsPage() {
	const navigate = useNavigate()
	const [topics, setTopics] = useState<TopicOut[]>([])
	const [customTopic, setCustomTopic] = useState('')
	const [error, setError] = useState<string | null>(null)
	const [loading, setLoading] = useState(true)
	// Тема, по которой идёт запрос/ожидание, и уже созданный тест (если POST /tests прошёл).
	// Пока waiting не null — старт новых тестов заблокирован, в том числе после
	// таймаута опроса: повторный requestTest запустил бы вторую платную генерацию.
	const [waiting, setWaiting] = useState<{ topic: string; test: TestOut | null } | null>(null)
	const [stalled, setStalled] = useState(false)
	const pollRef = useRef<AbortController | null>(null)
	const pendingTopic = waiting?.topic ?? null

	useEffect(() => () => pollRef.current?.abort(), [])

	useEffect(() => {
		let cancelled = false
		void listTopics()
			.then((items) => {
				if (!cancelled) setTopics(items)
			})
			.catch((err: unknown) => {
				if (cancelled) return
				const apiErr = err as ApiError
				setError(apiErr.detail ?? apiErr.message)
			})
			.finally(() => {
				if (!cancelled) setLoading(false)
			})
		return () => {
			cancelled = true
		}
	}, [])

	async function waitForTest(topicName: string, test: TestOut) {
		pollRef.current?.abort()
		const controller = new AbortController()
		pollRef.current = controller
		setWaiting({ topic: topicName, test })
		setStalled(false)
		setError(null)

		try {
			const { value, timedOut } = await waitForTestReady(test, { signal: controller.signal })
			if (timedOut) {
				// Не сбрасываем waiting: «Keep waiting» продолжит опрос того же теста.
				setWaiting({ topic: topicName, test: value })
				setStalled(true)
				return
			}
			setWaiting(null)
			if (value.status === 'failed') {
				setError('Test generation failed. Please try another topic.')
				return
			}
			navigate(`/tests/${value.id}`)
		} catch (err) {
			if (isAbortError(err)) return
			const apiErr = err as ApiError
			// Тест уже создан и, возможно, ещё генерируется — даём продолжить ожидание.
			setError(apiErr.detail ?? apiErr.message)
			setStalled(true)
		}
	}

	async function startTest(topicName: string) {
		setError(null)
		setWaiting({ topic: topicName, test: null })
		try {
			const created = await requestTest({ topic_name: topicName })
			await waitForTest(topicName, created)
		} catch (err) {
			const apiErr = err as ApiError
			setError(apiErr.detail ?? apiErr.message)
			setWaiting(null)
		}
	}

	function stopWaiting() {
		pollRef.current?.abort()
		setWaiting(null)
		setStalled(false)
		setError(null)
	}

	async function onCustomSubmit(e: FormEvent) {
		e.preventDefault()
		const topicName = customTopic.trim()
		if (!topicName) return
		await startTest(topicName)
	}

	return (
		<main className="page">
			<BackLink />
			<h1>Choose a topic</h1>
			<p className="muted page__lead">
				Pick a topic to generate a quiz. If the test is still generating, the page will wait until it is ready.
			</p>

			{stalled && waiting?.test ? (
				<div className="alert alert--info">
					<p>
						{error ?? `"${waiting.topic}" is taking longer than usual to generate.`}
					</p>
					<button
						type="button"
						className="btn btn--secondary"
						onClick={() => waiting.test && void waitForTest(waiting.topic, waiting.test)}
					>
						Keep waiting
					</button>
					<button type="button" className="btn btn--secondary" onClick={stopWaiting}>
						Choose another topic
					</button>
				</div>
			) : error ? (
				<div className="alert alert--error">{error}</div>
			) : null}

			{loading ? <p className="muted">Loading topics...</p> : null}

			{!loading && topics.length === 0 ? (
				<p className="muted">No system topics yet. You can still start a custom topic below.</p>
			) : null}

			<div className="topic-grid">
				{topics.map((topic) => (
					<button
						key={topic.id}
						type="button"
						className="topic-card"
						disabled={pendingTopic !== null}
						onClick={() => void startTest(topic.name)}
					>
						<strong>{topic.name}</strong>
						<span className="muted">
							{pendingTopic === topic.name ? 'Generating...' : topic.is_custom ? 'Custom' : 'Start quiz'}
						</span>
					</button>
				))}
			</div>

			<form className="card card--wide" onSubmit={(e) => void onCustomSubmit(e)}>
				<h2 className="card__title">Custom topic</h2>
				<label className="field">
					<span>Topic name</span>
					<input
						value={customTopic}
						onChange={(e) => setCustomTopic(e.target.value)}
						type="text"
						minLength={1}
						maxLength={150}
						placeholder="Present Perfect"
						disabled={pendingTopic !== null}
					/>
				</label>
				<button className="btn" type="submit" disabled={pendingTopic !== null || !customTopic.trim()}>
					{pendingTopic === customTopic.trim() ? 'Generating...' : 'Start custom quiz'}
				</button>
			</form>
		</main>
	)
}
