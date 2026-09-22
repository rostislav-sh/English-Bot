import { useMemo, useState } from 'react'
import type { MonthlyStatOut } from '../api/types/quiz'

type Props = {
	stats: MonthlyStatOut[]
}

function monthDate(value: string): Date | null {
	const date = new Date(value)
	return Number.isNaN(date.getTime()) ? null : date
}

function monthLabel(value: string, withYear: boolean): string {
	const date = monthDate(value)
	if (!date) return value
	const label = date
		.toLocaleDateString(undefined, withYear ? { month: 'short', year: '2-digit' } : { month: 'short' })
		.replace('.', '')
	return label.charAt(0).toLocaleUpperCase() + label.slice(1)
}

function monthTitle(value: string): string {
	const date = monthDate(value)
	if (!date) return value
	return date.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
}

function attemptsLabel(count: number): string {
	return count === 1 ? '1 attempt' : `${count} attempts`
}

export default function StatsChart({ stats }: Props) {
	const points = useMemo(
		() => [...stats].sort((a, b) => a.month.localeCompare(b.month)),
		[stats],
	)
	const [active, setActive] = useState(Math.max(0, points.length - 1))
	const selectedIndex = points[active] ? active : points.length - 1
	const selected = points[selectedIndex]

	const totals = useMemo(() => {
		return points.reduce(
			(acc, item) => {
				acc.attempts += item.attempts_count
				acc.score += item.total_score
				acc.questions += item.total_questions
				return acc
			},
			{ attempts: 0, score: 0, questions: 0 },
		)
	}, [points])

	const overallAccuracy = totals.questions === 0 ? 0 : (totals.score / totals.questions) * 100
	const years = new Set(points.map((item) => monthDate(item.month)?.getFullYear()).filter((year) => year !== undefined))
	const showYear = years.size > 1

	const width = 640
	const height = 236
	const pad = { left: 36, right: 18, top: 28, bottom: 36 }
	const innerW = width - pad.left - pad.right
	const innerH = height - pad.top - pad.bottom
	const baseline = pad.top + innerH

	const coords = points.map((item, index) => {
		const accuracy = Math.min(100, Math.max(0, item.accuracy))
		const x = points.length === 1 ? pad.left + innerW * 0.08 : pad.left + (innerW * index) / (points.length - 1)
		const y = baseline - (accuracy / 100) * innerH
		return { x, y, accuracy }
	})

	const line = coords.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')
	const area =
		coords.length > 0
			? `${line} L ${coords[coords.length - 1].x} ${baseline} L ${coords[0].x} ${baseline} Z`
			: ''
	const focus = coords[selectedIndex]

	return (
		<div className="stats">
			<div className="stats__summary">
				<div className="stats__metric">
					<span>Attempts</span>
					<strong>{totals.attempts}</strong>
				</div>
				<div className="stats__metric stats__metric--accent">
					<span>Accuracy</span>
					<strong>{Math.round(overallAccuracy)}%</strong>
				</div>
				<div className="stats__metric">
					<span>Score</span>
					<strong>
						{totals.score}
						<span className="stats__metric-sub"> / {totals.questions}</span>
					</strong>
				</div>
			</div>

			<div className="stats-plot">
				<svg className="stats-line" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Monthly accuracy">
					<defs>
						<linearGradient id="stats-area-fill" x1="0" y1="0" x2="0" y2="1">
							<stop offset="0%" stopColor="var(--accent)" stopOpacity="0.38" />
							<stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
						</linearGradient>
					</defs>

					{[0, 25, 50, 75, 100].map((tick) => {
						const y = baseline - (tick / 100) * innerH
						return (
							<g key={tick}>
								<line className="stats-line__grid" x1={pad.left} x2={width - pad.right} y1={y} y2={y} />
								<text className="stats-line__tick" x={pad.left - 8} y={y + 4} textAnchor="end">
									{tick}
								</text>
							</g>
						)
					})}

					{area ? <path d={area} fill="url(#stats-area-fill)" /> : null}
					{line ? <path className="stats-line__stroke" d={line} /> : null}

					{focus && coords.length > 1 ? (
						<line className="stats-line__cross" x1={focus.x} x2={focus.x} y1={pad.top} y2={baseline} />
					) : null}
					{focus ? (
						<>
							<line
								className="stats-line__price"
								x1={focus.x}
								x2={width - pad.right}
								y1={focus.y}
								y2={focus.y}
							/>
							<text className="stats-line__badge" x={focus.x} y={Math.max(14, focus.y - 12)} textAnchor="middle">
								{Math.round(focus.accuracy)}%
							</text>
						</>
					) : null}

					{coords.map((point, index) => (
						<g key={points[index].month}>
							<circle
								className={index === selectedIndex ? 'stats-line__halo' : 'stats-line__halo stats-line__halo--idle'}
								cx={point.x}
								cy={point.y}
								r={index === selectedIndex ? 9 : 0}
							/>
							<circle
								className={index === selectedIndex ? 'stats-line__dot stats-line__dot--active' : 'stats-line__dot'}
								cx={point.x}
								cy={point.y}
								r={index === selectedIndex ? 4.5 : 3.5}
							/>
							<text className="stats-line__label" x={point.x} y={height - 12} textAnchor="middle">
								{monthLabel(points[index].month, showYear)}
							</text>
						</g>
					))}

					{coords.map((point, index) => {
						const slot = points.length <= 1 ? 80 : innerW / points.length
						return (
							<rect
								key={`${points[index].month}-hit`}
								className="stats-line__hit"
								x={point.x - slot / 2}
								y={pad.top}
								width={slot}
								height={innerH}
								onMouseEnter={() => setActive(index)}
								onClick={() => setActive(index)}
							>
								<title>
									{monthTitle(points[index].month)}: {Math.round(point.accuracy)}%,{' '}
									{attemptsLabel(points[index].attempts_count)}
								</title>
							</rect>
						)
					})}
				</svg>
			</div>

			{selected ? (
				<p className="stats__detail">
					<strong>{monthTitle(selected.month)}</strong>
					<span>
						{attemptsLabel(selected.attempts_count)} · {Math.round(selected.accuracy)}% · {selected.total_score}/
						{selected.total_questions}
					</span>
				</p>
			) : null}
		</div>
	)
}
