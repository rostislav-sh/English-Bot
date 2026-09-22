import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/http'
import { getAttempt, waitForRecommendation } from '../api/quiz'
import type { AttemptOut } from '../api/types/quiz'

export default function AttemptPage() {
	const { attemptId } = useParams()
	const numericId = Number(attemptId)
	const [attempt, setAttempt] = useState<AttemptOut | null>(null)
	const [error, setError] = useState<string | null>(null)
	const [loading, setLoading] = useState(true)

	useEffect(() => {
		if (!Number.isFinite(numericId) || numericId <= 0) {
			setError('Invalid attempt id.')
			setLoading(false)
			return
		}

		let cancelled = false
		void getAttempt(numericId)
			.then((loaded) => waitForRecommendation(loaded))
			.then((ready) => {
				if (!cancelled) setAttempt(ready)
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
	}, [numericId])

	const title = useMemo(() => {
		if (!attempt) return 'Result'
		return attempt.is_perfect ? 'Perfect score' : 'Quiz result'
	}, [attempt])

	if (loading) {
		return (
			<main className="page">
				<p className="muted">Loading result...</p>
			</main>
		)
	}

	if (!attempt) {
		return (
			<main className="page">
				<h1>Result</h1>
				{error ? <div className="alert alert--error">{error}</div> : <p className="muted">Attempt not found.</p>}
				<Link to="/dashboard">Back to dashboard</Link>
			</main>
		)
	}

	return (
		<main className="page">
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

				{attempt.recommendation_status === 'pending' ? (
					<div className="alert alert--info">AI recommendation is still generating...</div>
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
