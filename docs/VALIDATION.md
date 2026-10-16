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

## Typography and visual refresh

The refreshed student and staff interfaces use self-hosted Manrope, larger headings, 16px chat/input text, stronger contrast, larger controls, a deep-green sidebar and responsive topic navigation. The font’s license is included in `public/static/fonts/`. No external font request is needed.

The Chromium chat workflow passed again after the design update. Layout checks at 320, 390, 768, 1024 and 1440 pixels found no horizontal page overflow on student or staff pages; the chat and input retained 16px text, and the self-hosted font loaded at every checked width. SVG arrows replace unsupported text glyphs. The screenshots reflect this refreshed interface.

## Fluid layout and Tailwind motion update

Tailwind CSS 4.1.18 is compiled locally into a small, tracked stylesheet. A frozen npm install and CSS compilation passed. The production interface needs neither a Tailwind CDN script nor a Node server. Spacing, headline size and chat height scale with the viewport. New messages ease into view, action controls respond to hover/press/focus, and the waiting avatar has a restrained pulse. Restored conversation messages do not replay entrance animations.

The desktop/mobile chat browser workflow passed after this update. Checks at 320, 390, 768, 1024, 1440 and 1920 pixels confirmed readable text (at least 16px), no horizontal page overflow and active message-entrance animation. Emulating reduced motion disabled both message animation and card transitions at every tested width. A separate reload check confirmed restored user and assistant messages have no entrance animation.
