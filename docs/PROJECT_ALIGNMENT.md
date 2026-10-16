# Implementation alignment with the project write-up

## Aim

Design and implement an intelligent Python chatbot that enhances student support, then evaluate its performance. The supplied Flask prototype is retained as the foundation and expanded into a working research demonstrator.

| Write-up requirement | Original implementation | Completed implementation |
| --- | --- | --- |
| Web-based student interaction | One small chat page | Responsive desktop/mobile interface, topic prompts, loading/error states, keyboard support |
| Python and natural language processing | Substring and fuzzy-keyword counting | Word/character TF-IDF, cosine similarity, vocabulary normalization, ambiguity and out-of-domain fallback |
| Academic and administrative support | Four answers | Twelve guidance topics with transparent sources and limitations |
| Database with user/query/response data | Empty database module | Anonymous users, queries, responses, feedback and editable knowledge tables |
| Administrator role | Missing | Protected staff workspace with aggregate metrics and knowledge/example editing |
| Interaction tracking and improvement | Missing | Session history, feedback, source review and staff-controlled matching-example updates |
| Error handling and reliability | Minimal | Structured validation, payload limits, CSRF protection, session isolation and browser error handling |
| Performance evaluation | Response duration only | Regression tests, per-case benchmark, timing report and browser workflow checks |
| Deployment | Missing | Vercel Flask configuration and persistent PostgreSQL integration |

## Correct the methodology and claims

Chapter 3 lists MySQL/MongoDB, while Chapter 4 specifies SQLite. Describe the actual implementation consistently: SQLite for local development and PostgreSQL for Vercel persistence, accessed through SQLAlchemy. Explain why serverless deployment needs an external database.

Describe the engine as a retrieval-based NLP chatbot with TF-IDF and cosine similarity. It does not use a large language model or generate unrestricted answers. Character n-grams help with spelling variation but do not guarantee semantic understanding. It has no multilingual or personal-record integration. Similarity scores are not probabilities.

Do not claim automatic learning from conversations. Staff review feedback and update examples and guidance; those reviewed changes refresh the matching index. No private message is automatically added to training data.

The original fixed 30 March deadline is example content, not a verified institutional fact. Demonstrations should use the current clearly labelled general guidance or a verified institutional handbook with its source and date.

## Evaluation evidence

`evaluation-results.json` records 44 development cases and their actual outcomes. The dataset was inspected during tuning, and must not be described as a blind test set. The remaining recorded error maps a bursary/tuition-assistance question to fee guidance. Automated tests also exercise malformed requests, unauthorized staff access, isolated sessions, feedback ownership, deletion and guidance updates. Browser checks exercise the actual interface, not just HTTP status codes.

For the final dissertation:

1. Freeze the code and knowledge-base version, record the Git commit, and collect a separate representative dataset of real or independently authored student questions, with consent where required.
2. Have a knowledgeable reviewer label expected intent and answer correctness before running evaluation. Keep these questions separate from training examples and development cases.
3. Report the actual number of cases, correct/incorrect/fallback outcomes, per-topic results and confusion matrix. A relevant topic match is not sufficient evidence that a policy answer is correct.
4. Measure end-to-end response times on the live deployment, separating cold and warm requests, and report median/p95 and the testing conditions.
5. Conduct an actual usability study. Record participant count, questionnaire, anonymized responses and the calculation of satisfaction percentages. Button feedback is not a representative survey.
6. Replace the existing claims of 170/200 correct, 85% accuracy, 2–5 seconds and 90% satisfaction unless original auditable evidence is available. Do not substitute development-benchmark results as if they came from those 200 participants/questions.

## Deployment and privacy scope

This release is a final-year project demonstrator with general guidance. It provides no live institutional student-record access, payment handling, ticketing, staff email routing or verified emergency service. It is not a substitute for institutional support. Institutional deployment additionally requires approved content, retention and privacy policies, provider backup configuration, monitoring, and distributed abuse protection.

Chat messages are stored under anonymous session identifiers. Cookies are HTTP-only and SameSite=Lax, with Secure enabled on Vercel. The clear-chat action deletes the session's stored queries and responses. Staff can see aggregate counts but cannot browse raw conversations through the staff API. Server/database administrators still control the underlying storage; anonymous identifiers do not guarantee that message text contains no personal information.
