import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/http'
import { getAttempt, isAbortError, waitForRecommendation } from '../api/quiz'
import BackLink from '../components/BackLink'
import type { AttemptOut } from '../api/types/quiz'

export default function AttemptPage() {
	const { attemptId } = useParams()
	const numericId = Number(attemptId)
	const [attempt, setAttempt] = useState<AttemptOut | null>(null)
	const [error, setError] = useState<string | null>(null)
	const [loading, setLoading] = useState(true)
	// Ожидание рекомендации не уложилось в дедлайн или упало с ошибкой —
	// показываем кнопку «Check again» вместо вечной плашки.
	const [recStalled, setRecStalled] = useState(false)
	const [recError, setRecError] = useState<string | null>(null)
	const pollRef = useRef<AbortController | null>(null)

	// Опрашивает рекомендацию фоном: счёт и ответы уже показаны.
	const pollRecommendation = useCallback((current: AttemptOut) => {
		pollRef.current?.abort()
		const controller = new AbortController()
		pollRef.current = controller
		setRecStalled(false)
		setRecError(null)

		void waitForRecommendation(current, { signal: controller.signal })
			.then(({ value, timedOut }) => {
				setAttempt(value)
				setRecStalled(timedOut)
			})
			.catch((err: unknown) => {
				if (isAbortError(err)) return
				const apiErr = err as ApiError
				setRecError(apiErr.detail ?? apiErr.message)
				setRecStalled(true)
			})
	}, [])

	useEffect(() => {
		if (!Number.isFinite(numericId) || numericId <= 0) {
			setError('Invalid attempt id.')
			setLoading(false)
			return
		}

		let cancelled = false
		void getAttempt(numericId)
			.then((loaded) => {
				if (cancelled) return
				setAttempt(loaded)
				if (loaded.recommendation_status === 'pending') pollRecommendation(loaded)
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
			pollRef.current?.abort()
		}
	}, [numericId, pollRecommendation])

	const title = useMemo(() => {
		if (!attempt) return 'Result'
		return attempt.is_perfect ? 'Perfect score' : 'Quiz result'
	}, [attempt])

	if (loading) {
		return (
			<main className="page">
				<BackLink />
				<p className="muted">Loading result...</p>
			</main>
		)
	}

	if (!attempt) {
		return (
			<main className="page">
				<BackLink />
				<h1>Result</h1>
				{error ? <div className="alert alert--error">{error}</div> : <p className="muted">Attempt not found.</p>}
				<Link to="/dashboard">Back to dashboard</Link>
			</main>
		)
	}

	return (
		<main className="page">
			<BackLink />
			<h1>{title}</h1>
			<section className="card card--wide">
				<div className="kv">
					<div className="kv__row">
						<span>Score</span>
						<strong>
							{attempt.score} / {attempt.total_questions}
						</strong>
					</div>
					<div className="kv__row">
						<span>Accuracy</span>
						<strong>{Math.round(attempt.percentage)}%</strong>
					</div>
				</div>

				{attempt.recommendation_status === 'pending' && !recStalled ? (
					<div className="alert alert--info">AI recommendation is still generating...</div>
				) : null}
				{attempt.recommendation_status === 'pending' && recStalled ? (
					<div className="alert alert--info">
						<p>{recError ?? 'AI recommendation is taking longer than usual.'}</p>
						<button
							type="button"
							className="btn btn--secondary"
							onClick={() => pollRecommendation(attempt)}
						>
							Check again
						</button>
					</div>
				) : null}
				{attempt.recommendation_status === 'failed' ? (
					<div className="alert alert--error">AI recommendation failed.</div>
				) : null}
				{attempt.ai_recommendation ? (
					<div className="alert alert--info">
						<strong>AI recommendation</strong>
						<p>{attempt.ai_recommendation}</p>
					</div>
				) : null}

				<ol className="result-list">
					{attempt.answers.map((answer, index) => (
						<li key={answer.question_id} className={answer.is_correct ? 'result-item result-item--ok' : 'result-item result-item--bad'}>
							<p>
								<strong>Q{index + 1}.</strong> Your answer: {answer.user_answer}
							</p>
							<p className="muted">Correct answer: {answer.correct_answer}</p>
						</li>
					))}
				</ol>

				<div className="actions">
					<Link className="btn" to="/topics">
						Take another quiz
					</Link>
					<Link className="btn btn--secondary" to="/dashboard">
						Back to dashboard
					</Link>
				</div>
			</section>
		</main>
	)
}
