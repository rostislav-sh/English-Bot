import type { FormEvent } from 'react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/http'
import { listTopics, requestTest, waitForTestReady } from '../api/quiz'
import type { TopicOut } from '../api/types/quiz'

export default function TopicsPage() {
	const navigate = useNavigate()
	const [topics, setTopics] = useState<TopicOut[]>([])
	const [customTopic, setCustomTopic] = useState('')
	const [error, setError] = useState<string | null>(null)
	const [loading, setLoading] = useState(true)
	const [pendingTopic, setPendingTopic] = useState<string | null>(null)

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

	async function startTest(topicName: string) {
		setError(null)
		setPendingTopic(topicName)
		try {
			const created = await requestTest({ topic_name: topicName })
			const ready = await waitForTestReady(created)
			if (ready.status === 'failed') {
				setError('Test generation failed. Please try another topic.')
				return
			}
			if (ready.status !== 'ready') {
				setError('Test is still generating. Please retry in a moment.')
				return
			}
			navigate(`/tests/${ready.id}`)
		} catch (err) {
			const apiErr = err as ApiError
			setError(apiErr.detail ?? apiErr.message)
		} finally {
			setPendingTopic(null)
		}
	}

	async function onCustomSubmit(e: FormEvent) {
		e.preventDefault()
		const topicName = customTopic.trim()
		if (!topicName) return
		await startTest(topicName)
	}

	return (
		<main className="page">
			<h1>Choose a topic</h1>
			<p className="muted page__lead">
				Pick a topic to generate a quiz. If the test is still generating, the page will wait until it is ready.
			</p>

			{error ? <div className="alert alert--error">{error}</div> : null}

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
