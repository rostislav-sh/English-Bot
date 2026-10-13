import type { FormEvent } from 'react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api/http'
import { getTest, isAbortError, submitTest, waitForTestReady } from '../api/quiz'
import BackLink from '../components/BackLink'
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
	// Тест всё ещё генерируется после дедлайна опроса — предлагаем подождать ещё.
	const [stalled, setStalled] = useState(false)
	const pollRef = useRef<AbortController | null>(null)

	const applyTest = useCallback((loaded: TestOut) => {
		setTest(loaded)
		if (loaded.status === 'failed') {
			setError('Test generation failed.')
		}
	}, [])

	const pollTest = useCallback((current: TestOut) => {
		pollRef.current?.abort()
		const controller = new AbortController()
		pollRef.current = controller
		setStalled(false)
		setError(null)

		void waitForTestReady(current, { signal: controller.signal })
			.then(({ value, timedOut }) => {
				applyTest(value)
				setStalled(timedOut)
			})
			.catch((err: unknown) => {
				if (isAbortError(err)) return
				const apiErr = err as ApiError
				setError(apiErr.detail ?? apiErr.message)
				setStalled(true)
			})
	}, [applyTest])

	useEffect(() => {
		if (!Number.isFinite(numericId) || numericId <= 0) {
			setError('Invalid test id.')
			setLoading(false)
			return
		}

		let cancelled = false
		void getTest(numericId)
			.then((loaded) => {
				if (cancelled) return
				applyTest(loaded)
				if (loaded.status === 'generating') pollTest(loaded)
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
	}, [numericId, applyTest, pollTest])

	const answeredCount = useMemo(() => {
		if (!test) return 0
		return test.questions.filter((question) => Boolean(answers[question.id])).length
	}, [answers, test])
	const unansweredCount = test ? test.questions.length - answeredCount : 0

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
				<BackLink fallback="/topics" />
				<p className="muted">Loading test...</p>
			</main>
		)
	}

	if (test?.status === 'generating') {
		return (
			<main className="page">
				<BackLink fallback="/topics" />
				<h1>Test</h1>
				{stalled ? (
					<div className="alert alert--info">
						<p>{error ?? 'Test generation is taking longer than usual.'}</p>
						<button type="button" className="btn btn--secondary" onClick={() => pollTest(test)}>
							Keep waiting
						</button>
					</div>
				) : (
					<p className="muted">Generating test...</p>
				)}
				<Link to="/topics">Back to topics</Link>
			</main>
		)
	}

	if (!test || test.status !== 'ready') {
		return (
			<main className="page">
				<BackLink fallback="/topics" />
				<h1>Test</h1>
				{error ? <div className="alert alert--error">{error}</div> : <p className="muted">Test is not ready.</p>}
				<Link to="/topics">Back to topics</Link>
			</main>
		)
	}

	return (
		<main className="page">
			<BackLink fallback="/topics" />
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
				<p className="quiz-progress" translate="no">
					{unansweredCount > 0 ? (
						<>
							Answered <strong key={answeredCount}>{answeredCount}</strong> of {test.questions.length}.
						</>
					) : (
						'All questions answered.'
					)}
				</p>

				<button className="btn" type="submit" disabled={pending || unansweredCount > 0}>
					{pending ? 'Submitting...' : 'Submit answers'}
				</button>
			</form>
		</main>
	)
}
