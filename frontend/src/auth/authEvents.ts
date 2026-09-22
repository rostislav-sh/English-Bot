type Listener = () => void

const listeners = new Set<Listener>()

export function onSessionExpired(cb: Listener) {
	listeners.add(cb)
	return () => {
		listeners.delete(cb)
	}
}

export function notifySessionExpired() {
	listeners.forEach((cb) => cb())
}
