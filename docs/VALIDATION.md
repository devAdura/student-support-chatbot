# Validation record

Validation performed on 16 October 2026 in the cloud development environment.

| Check | Observed result |
| --- | --- |
| Python regression suite with SQLite | 20 passed |
| Same suite with PostgreSQL 17 | 20 passed, using certificate and hostname verification against a trusted local test certificate |
| PostgreSQL integration smoke check | Schema, chat, history, feedback, staff editing, metrics, deletion and TLS verified |
| Chromium workflow checks | Desktop/mobile chat, feedback, history reload, clear-chat deletion, HTML-injection safety, overflow and staff page passed; no JavaScript errors |
| Development question benchmark | 43/44 correctly classified; 97.73%; inspected during tuning, not a held-out estimate |
| Dependency consistency | `pip check` passed |
| Vercel production build | Python 3.12 build succeeded; Vercel reported READY and assigned the production domain |
| Live production HTTPS smoke check | Health, page, JavaScript/CSS assets, secure cookies, course-registration response, PostgreSQL history, feedback, CSRF enforcement, staff access control and test-session deletion passed |

The development screenshots in `screenshots/` show the tested local interface. They do not establish that a live server has been functionally verified.

Production domain: https://student-support-chatbot-one.vercel.app

The initial cloud egress restriction was resolved and live HTTPS functional checks subsequently passed. One warm end-to-end chat request took 0.439 seconds; this is a single observation, not a performance benchmark. Production browser automation was not completed because Chromium did not trust the workspace’s HTTPS proxy certificate; certificate verification was not disabled. Desktop and mobile browser workflows passed locally using the same application code. The administrator credential is configured as a sensitive Vercel variable and cannot be read back; successful password authentication was tested locally, while production checks verified that staff endpoints reject anonymous access. No student survey or independent held-out evaluation was performed.

GitHub publication also remained pending because the workspace's available integration denied Git and API writes, including after a GitHub CLI device authorization. The source ZIP is available separately. A secure repository-scoped write-token requirement was saved to cloud environment settings; no token or production connection URL is included in this package.
