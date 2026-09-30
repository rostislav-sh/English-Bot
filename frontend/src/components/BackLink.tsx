import { useNavigate } from 'react-router-dom'

type Props = {
	fallback?: string
}

export default function BackLink({ fallback = '/dashboard' }: Props) {
	const navigate = useNavigate()

	function goBack() {
		const idx = window.history.state?.idx
		if (typeof idx === 'number' && idx > 0) {
			navigate(-1)
			return
		}
		navigate(fallback)
	}

	return (
		<div className="page-back">
			<button className="back-link" type="button" onClick={goBack}>
				<span aria-hidden="true">←</span>
				Back
			</button>
		</div>
	)
}
