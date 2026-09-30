import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children: ReactNode }
type State = { error: Error | null }

export default class ErrorBoundary extends Component<Props, State> {
	state: State = { error: null }

	static getDerivedStateFromError(error: Error): State {
		return { error }
	}

	componentDidCatch(error: Error, info: ErrorInfo): void {
		console.error(error, info)
	}

	render() {
		if (this.state.error) {
			return (
				<main className="page">
					<h1>Something went wrong</h1>
					<p className="muted">The page failed to render. Reload it and try again.</p>
					<button className="btn" type="button" onClick={() => window.location.reload()}>
						Reload
					</button>
				</main>
			)
		}
		return this.props.children
	}
}
