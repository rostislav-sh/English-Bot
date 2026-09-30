import { useMemo, useState } from 'react'

export type StatsChartPoint = {
	id: string
	at: string
	accuracy: number
	score: number
	totalQuestions: number
}

type Props = {
	points: StatsChartPoint[]
}

function pointDate(value: string): Date | null {
	const date = new Date(value)
	return Number.isNaN(date.getTime()) ? null : date
}

function dayKey(value: string): string {
	const date = pointDate(value)
	if (!date) return value
	return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
}

function axisLabel(value: string, withTime: boolean): string {
	const date = pointDate(value)
	if (!date) return value
	const day = date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }).replace('.', '')
	if (!withTime) return day
	const time = date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
	return `${day} ${time}`
}

function pointTitle(value: string): string {
	const date = pointDate(value)
	if (!date) return value
	return date.toLocaleString()
}

export default function StatsChart({ points }: Props) {
	const ordered = useMemo(
		() => [...points].sort((a, b) => a.at.localeCompare(b.at)),
		[points],
	)
	const [active, setActive] = useState(Math.max(0, ordered.length - 1))
	const selectedIndex = ordered[active] ? active : ordered.length - 1
	const selected = ordered[selectedIndex]

	const totals = useMemo(() => {
		return ordered.reduce(
			(acc, item) => {
				acc.score += item.score
				acc.questions += item.totalQuestions
				return acc
			},
			{ score: 0, questions: 0 },
		)
	}, [ordered])

	const overallAccuracy = totals.questions === 0 ? 0 : (totals.score / totals.questions) * 100
	const dayCounts = useMemo(() => {
		const counts = new Map<string, number>()
		for (const item of ordered) {
			const key = dayKey(item.at)
			counts.set(key, (counts.get(key) ?? 0) + 1)
		}
		return counts
	}, [ordered])

	const width = 640
	const height = 236
	const pad = { left: 36, right: 18, top: 28, bottom: 36 }
	const innerW = width - pad.left - pad.right
	const innerH = height - pad.top - pad.bottom
	const baseline = pad.top + innerH
	const labelStep = Math.max(1, Math.ceil(ordered.length / 6))

	const coords = ordered.map((item, index) => {
		const accuracy = Math.min(100, Math.max(0, item.accuracy))
		const x = ordered.length === 1 ? pad.left + innerW * 0.08 : pad.left + (innerW * index) / (ordered.length - 1)
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
					<span>Tests</span>
					<strong>{ordered.length}</strong>
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
				<svg className="stats-line" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Accuracy by test">
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
							<line className="stats-line__price" x1={focus.x} x2={width - pad.right} y1={focus.y} y2={focus.y} />
							<text className="stats-line__badge" x={focus.x} y={Math.max(14, focus.y - 12)} textAnchor="middle">
								{Math.round(focus.accuracy)}%
							</text>
						</>
					) : null}

					{coords.map((point, index) => {
						const item = ordered[index]
						const showLabel = index === 0 || index === ordered.length - 1 || index % labelStep === 0
						const withTime = (dayCounts.get(dayKey(item.at)) ?? 0) > 1
						return (
							<g key={item.id}>
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
								{showLabel ? (
									<text className="stats-line__label" x={point.x} y={height - 12} textAnchor="middle">
										{axisLabel(item.at, withTime)}
									</text>
								) : null}
							</g>
						)
					})}

					{coords.map((point, index) => {
						const slot = ordered.length <= 1 ? 80 : innerW / ordered.length
						const item = ordered[index]
						return (
							<rect
								key={`${item.id}-hit`}
								className="stats-line__hit"
								x={point.x - slot / 2}
								y={pad.top}
								width={slot}
								height={innerH}
								onMouseEnter={() => setActive(index)}
								onClick={() => setActive(index)}
							>
								<title>
									{pointTitle(item.at)}: {item.score}/{item.totalQuestions} · {Math.round(point.accuracy)}%
								</title>
							</rect>
						)
					})}
				</svg>
			</div>

			{selected ? (
				<p className="stats__detail">
					<strong>{pointTitle(selected.at)}</strong>
					<span>
						{selected.score}/{selected.totalQuestions} · {Math.round(selected.accuracy)}%
					</span>
				</p>
			) : null}
		</div>
	)
}
