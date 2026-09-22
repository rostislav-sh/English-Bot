export type TopicOut = {
	id: number
	name: string
	is_custom: boolean
}

export type RequestTestIn = {
	topic_name: string
}

export type QuestionType = 'multiple_choice'

export type TestStatus = 'generating' | 'ready' | 'failed'

export type RecommendationStatus = 'not_needed' | 'pending' | 'ready' | 'failed'

export type QuestionOut = {
	id: number
	text: string
	options: unknown[]
	question_type: QuestionType
}

export type TestOut = {
	id: number
	topic_id: number
	status: TestStatus
	questions: QuestionOut[]
}

export type AnswerIn = {
	question_id: number
	answer: string
}

export type SubmitAnswersIn = {
	answers: AnswerIn[]
}

export type AnswerResultOut = {
	question_id: number
	user_answer: string
	correct_answer: string
	is_correct: boolean
}

export type AttemptOut = {
	id: number
	test_id: number
	score: number
	total_questions: number
	percentage: number
	is_perfect: boolean
	recommendation_status: RecommendationStatus
	ai_recommendation: string | null
	answers: AnswerResultOut[]
}

export type AttemptHistoryItemOut = {
	id: number
	test_id: number
	score: number
	total_questions: number
	percentage: number
	created_at: string | null
}

export type MonthlyStatOut = {
	month: string
	attempts_count: number
	total_score: number
	total_questions: number
	accuracy: number
}
