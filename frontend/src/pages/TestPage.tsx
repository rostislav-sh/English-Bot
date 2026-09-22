import type { FormEvent } from 'react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api/http'
import { getTest, submitTest, waitForTestReady } from '../api/quiz'
import type { TestOut } from '../api/types/quiz'

function optionLabel(option: unknown): string {
	return typeof option === 'string' ? option : JSON.stringify(option)
}

export default function TestPage() {
	const { testId } = useParams()
	const navigate = useNavigate()
	const numericId = Number(testId)
	const [test, setTest] = useState<TestOut | null>(null)
	const [answers, setAnswers] = useState<Record<number, string>>({})
	const [error, setError] = useState<string | null>(null)
	const [loading, setLoading] = useState(true)
	const [pending, setPending] = useState(false)

	useEffect(() => {
		if (!Number.isFinite(numericId) || numericId <= 0) {
			setError('Invalid test id.')
			setLoading(false)
			return
		}

		let cancelled = false
		void getTest(numericId)
			.then((loaded) => waitForTestReady(loaded))
			.then((ready) => {
				if (cancelled) return
				setTest(ready)
				if (ready.status === 'failed') {
					setError('Test generation failed.')
				}
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

	const unanswered = useMemo(() => {
		if (!test) return []
		return test.questions.filter((question) => !answers[question.id])
	}, [answers, test])

	async function onSubmit(e: FormEvent) {
		e.preventDefault()
		if (!test) return
		setError(null)
		setPending(true)
		try {
			const attempt = await submitTest(test.id, {
				answers: test.questions.map((question) => ({
					question_id: question.id,
					answer: answers[question.id] ?? '',
				})),
			})
			navigate(`/attempts/${attempt.id}`)
		} catch (err) {
			const apiErr = err as ApiError
			setError(apiErr.detail ?? apiErr.message)
		} finally {
			setPending(false)
		}
	}

	if (loading) {
		return (
			<main className="page">
				<p className="muted">Loading test...</p>
			</main>
		)
	}

	if (!test || test.status !== 'ready') {
		return (
			<main className="page">
				<h1>Test</h1>
				{error ? <div className="alert alert--error">{error}</div> : <p className="muted">Test is not ready.</p>}
				<Link to="/topics">Back to topics</Link>
			</main>
		)
	}

	return (
		<main className="page">
			<h1>Quiz</h1>
			<p className="muted page__lead">Answer every question, then submit the whole test at once.</p>

			<form className="card card--wide" onSubmit={(e) => void onSubmit(e)}>
				{test.questions.map((question, index) => (
					<fieldset key={question.id} className="question">
						<legend>
							Question {index + 1}. {question.text}
						</legend>
						<div className="options">
							{question.options.map((option) => {
								const label = optionLabel(option)
								const selected = answers[question.id] === label
								return (
									<label key={label} className={`option${selected ? ' option--selected' : ''}`}>
										<input
											type="radio"
											name={`question-${question.id}`}
											value={label}
											checked={selected}
											onChange={() => {
												setAnswers((current) => ({ ...current, [question.id]: label }))
											}}
										/>
										<span>{label}</span>
									</label>
								)
							})}
						</div>
					</fieldset>
				))}

				{error ? <div className="alert alert--error">{error}</div> : null}
				{unanswered.length > 0 ? (
					<p className="muted">Answered {test.questions.length - unanswered.length} of {test.questions.length}.</p>
				) : (
					<p className="muted">All questions answered.</p>
				)}

				<button className="btn" type="submit" disabled={pending || unanswered.length > 0}>
					{pending ? 'Submitting...' : 'Submit answers'}
				</button>
			</form>
		</main>
	)
}
