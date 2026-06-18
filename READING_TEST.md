# English Reading Comprehension Test

A small web app that generates leveled English reading-comprehension tests. Pick a
level, optionally give a topic, and the server asks Claude to **search and/or
generate** an original passage plus **six** multiple-choice questions — each
testing a different comprehension skill. Answer them in the browser and get an
instant score with explanations.

## Levels

| Level         | Target length | Audience / difficulty            |
| ------------- | ------------- | -------------------------------- |
| Junior High   | ~400 words    | CEFR A2–B1, common vocabulary    |
| High School   | ~600 words    | CEFR B1–B2, mixed complexity     |
| University    | ~1000 words   | CEFR B2–C1, academic register    |

## The six questions

Every test covers six distinct skills, in order:

1. Main idea
2. Supporting detail
3. Vocabulary in context
4. Inference
5. Author's tone / attitude
6. Author's purpose / text structure

## Running it

The server uses only Node.js built-ins — **no `npm install` required**.

```bash
export ANTHROPIC_API_KEY=sk-ant-...      # required
node server.js                            # or: npm start
# open http://localhost:3000
```

Optional environment variables:

| Variable                | Default                     | Purpose                          |
| ----------------------- | --------------------------- | -------------------------------- |
| `ANTHROPIC_API_KEY`     | —                           | **Required** Anthropic API key   |
| `PORT`                  | `3000`                      | Port to listen on                |
| `READING_TEST_MODEL`    | `claude-opus-4-8`           | Model used to generate tests     |
| `READING_TEST_BASE_URL` | `https://api.anthropic.com` | API base URL                     |

> A dedicated `READING_TEST_BASE_URL` is used (rather than `ANTHROPIC_BASE_URL`)
> so the app always reaches the public API with `x-api-key`, regardless of any
> proxy in the surrounding environment.

## How it works

- **`server.js`** — dependency-free HTTP server. Serves the frontend and exposes:
  - `POST /api/generate` — body `{ level, topic?, useSearch? }` → JSON `{ title, article, wordCount, questions[] }`.
  - `GET /api/health` — reports the model and whether an API key is set.
- It calls the Anthropic Messages API directly (raw HTTPS). With the **web search**
  option enabled it includes the `web_search` server tool so Claude can ground the
  passage in current, real-world information; otherwise it generates from the
  model's own knowledge. If search is unavailable it transparently falls back to
  plain generation.
- **`public/index.html`** — single-page frontend (no build step). Correct answers
  are revealed and the score computed in the browser when you press *Check answers*.

## Notes

- Article generation can take ~20–60 seconds, especially for the 1000-word level
  or with web search enabled.
- Each request is independent — the app keeps no server-side state or database.
