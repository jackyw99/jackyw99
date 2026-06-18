'use strict';

/**
 * English Reading Comprehension Test — server
 *
 * Dependency-free Node.js HTTP server (built-ins only) that:
 *   - serves the single-page frontend from ./public
 *   - exposes POST /api/generate, which asks Claude to *search and/or generate*
 *     a leveled reading passage plus 6 comprehension questions.
 *
 * Levels (target word counts):
 *   junior      -> ~400 words   (junior high,  CEFR A2-B1)
 *   high        -> ~600 words   (high school,  CEFR B1-B2)
 *   university  -> ~1000 words  (university,   CEFR B2-C1)
 *
 * Configuration (environment variables):
 *   ANTHROPIC_API_KEY        required — your Anthropic API key (sk-ant-...)
 *   READING_TEST_MODEL       optional — model id (default: claude-opus-4-8)
 *   READING_TEST_BASE_URL    optional — API base (default: https://api.anthropic.com)
 *   PORT                     optional — listen port (default: 3000)
 *
 * Note: we intentionally read a *dedicated* base-URL variable rather than the
 * ambient ANTHROPIC_BASE_URL so this app always talks to the public API with an
 * x-api-key, regardless of any proxy configured in the surrounding environment.
 */

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

const PORT = parseInt(process.env.PORT || '3000', 10);
const MODEL = process.env.READING_TEST_MODEL || 'claude-opus-4-8';
const API_BASE = process.env.READING_TEST_BASE_URL || 'https://api.anthropic.com';
const API_KEY = process.env.ANTHROPIC_API_KEY || '';

const PUBLIC_DIR = path.join(__dirname, 'public');

const LEVELS = {
  junior: {
    label: 'Junior High',
    words: 400,
    guidance:
      'Audience: junior-high students (CEFR A2-B1). Use common, concrete vocabulary, mostly short to medium sentences, and a clear, friendly narrative or expository style. Avoid idioms and rare words.',
  },
  high: {
    label: 'High School',
    words: 600,
    guidance:
      'Audience: high-school students (CEFR B1-B2). Use a mix of sentence lengths, some figurative language, and moderately sophisticated vocabulary. The passage may present an argument or a nuanced topic.',
  },
  university: {
    label: 'University',
    words: 1000,
    guidance:
      'Audience: university students (CEFR B2-C1). Use academic register, varied and complex sentence structures, abstract concepts, discipline-appropriate terminology, and develop ideas across multiple well-organized paragraphs.',
  },
};

// The six question "topics" — every test covers these distinct comprehension skills.
const QUESTION_TOPICS = [
  'main idea',
  'supporting detail',
  'vocabulary in context',
  'inference',
  "author's tone or attitude",
  "author's purpose or text structure",
];

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
};

// --------------------------------------------------------------------------
// Anthropic API call (raw HTTPS, no SDK)
// --------------------------------------------------------------------------

function callAnthropic(body) {
  return new Promise((resolve, reject) => {
    const url = new URL('/v1/messages', API_BASE);
    const payload = Buffer.from(JSON.stringify(body));
    const transport = url.protocol === 'http:' ? http : https;

    const req = transport.request(
      {
        hostname: url.hostname,
        port: url.port || (url.protocol === 'http:' ? 80 : 443),
        path: url.pathname,
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'content-length': payload.length,
          'x-api-key': API_KEY,
          'anthropic-version': '2023-06-01',
        },
      },
      (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => {
          const text = Buffer.concat(chunks).toString('utf8');
          let json;
          try {
            json = JSON.parse(text);
          } catch (e) {
            return reject(new Error(`Non-JSON response (HTTP ${res.statusCode}): ${text.slice(0, 500)}`));
          }
          if (res.statusCode < 200 || res.statusCode >= 300) {
            const msg = json && json.error && json.error.message ? json.error.message : text;
            return reject(new Error(`Anthropic API error (HTTP ${res.statusCode}): ${msg}`));
          }
          resolve(json);
        });
      }
    );

    req.on('error', reject);
    req.setTimeout(180000, () => req.destroy(new Error('Anthropic API request timed out')));
    req.write(payload);
    req.end();
  });
}

// Concatenate all text blocks from a response message's content array.
function collectText(content) {
  if (!Array.isArray(content)) return '';
  return content
    .filter((b) => b && b.type === 'text' && typeof b.text === 'string')
    .map((b) => b.text)
    .join('\n');
}

// Pull the first balanced JSON object out of arbitrary model text.
function extractJSON(text) {
  if (!text) throw new Error('Model returned no text to parse.');
  let cleaned = text.trim();
  // strip ```json ... ``` fences if present
  const fence = cleaned.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fence) cleaned = fence[1].trim();

  const start = cleaned.indexOf('{');
  const end = cleaned.lastIndexOf('}');
  if (start === -1 || end === -1 || end <= start) {
    throw new Error('Could not locate a JSON object in the model response.');
  }
  const slice = cleaned.slice(start, end + 1);
  return JSON.parse(slice);
}

function buildPrompt(levelKey, topic, useSearch) {
  const level = LEVELS[levelKey];
  const topicLine = topic
    ? `The passage MUST be about this topic: "${topic}".`
    : 'Choose an engaging, age-appropriate topic yourself (science, history, culture, technology, nature, society, etc.). Vary the subject.';

  const searchLine = useSearch
    ? 'Use the web_search tool to find accurate, current, real-world information, then write an ORIGINAL passage in your own words based on what you learn. Do not copy text verbatim from sources.'
    : 'Write an original, factually plausible passage from your own knowledge.';

  return [
    `You are an expert English-language assessment writer creating a reading comprehension test for ${level.label} students.`,
    '',
    `${searchLine}`,
    '',
    'PASSAGE REQUIREMENTS:',
    `- Length: approximately ${level.words} words (stay within ±10%).`,
    `- ${level.guidance}`,
    `- ${topicLine}`,
    '- Coherent, well-structured, and self-contained (a reader needs no outside knowledge to answer the questions).',
    '- Give it a short, descriptive title.',
    '',
    'QUESTION REQUIREMENTS:',
    '- Write EXACTLY 6 multiple-choice questions, each testing a DIFFERENT comprehension skill, in this order:',
    QUESTION_TOPICS.map((t, i) => `    ${i + 1}. ${t}`).join('\n'),
    '- Each question has EXACTLY 4 options.',
    '- Exactly one option is correct; the other three are plausible but clearly wrong on careful reading.',
    '- Vary the position of the correct answer across questions (do not always make it the same letter).',
    '- For each question include a one- or two-sentence explanation of why the correct answer is right.',
    '',
    'OUTPUT FORMAT:',
    'Respond with ONLY a single minified or pretty JSON object and NOTHING else (no markdown, no commentary). Use this exact shape:',
    '{',
    '  "title": "string",',
    '  "topic": "the subject of the passage",',
    '  "article": "the full passage text as a single string (use \\n\\n between paragraphs)",',
    '  "questions": [',
    '    {',
    '      "skill": "one of the six skills above",',
    '      "question": "string",',
    '      "options": ["string", "string", "string", "string"],',
    '      "correct_index": 0,',
    '      "explanation": "string"',
    '    }',
    '  ]',
    '}',
  ].join('\n');
}

function wordCount(str) {
  return (String(str).trim().match(/\b[\w'-]+\b/g) || []).length;
}

// Validate / normalize the model's JSON into the shape the frontend expects.
function normalize(data, levelKey) {
  if (!data || typeof data !== 'object') throw new Error('Model JSON was not an object.');
  const title = String(data.title || 'Reading Passage').trim();
  const topic = String(data.topic || '').trim();
  const article = String(data.article || '').trim();
  if (!article) throw new Error('Model JSON had no article text.');

  if (!Array.isArray(data.questions) || data.questions.length === 0) {
    throw new Error('Model JSON had no questions.');
  }

  const questions = data.questions.slice(0, 6).map((q, i) => {
    const options = Array.isArray(q.options) ? q.options.map((o) => String(o)) : [];
    if (options.length !== 4) {
      throw new Error(`Question ${i + 1} did not have exactly 4 options.`);
    }
    let idx = Number(q.correct_index);
    if (!Number.isInteger(idx) || idx < 0 || idx > 3) idx = 0;
    return {
      skill: String(q.skill || QUESTION_TOPICS[i] || 'comprehension'),
      question: String(q.question || '').trim(),
      options,
      correct_index: idx,
      explanation: String(q.explanation || '').trim(),
    };
  });

  return {
    level: levelKey,
    levelLabel: LEVELS[levelKey].label,
    targetWords: LEVELS[levelKey].words,
    title,
    topic,
    article,
    wordCount: wordCount(article),
    questions,
  };
}

async function generateTest(levelKey, topic, useSearch) {
  const prompt = buildPrompt(levelKey, topic, useSearch);

  const baseBody = {
    model: MODEL,
    max_tokens: 16000,
    output_config: { effort: 'medium' },
    messages: [{ role: 'user', content: prompt }],
  };
  if (useSearch) {
    baseBody.tools = [{ type: 'web_search_20260209', name: 'web_search' }];
  }

  // Agentic loop: server-side tools may return stop_reason "pause_turn" when the
  // built-in iteration cap is hit; re-send the conversation to let it continue.
  const messages = [{ role: 'user', content: prompt }];
  let resp;
  for (let i = 0; i < 6; i++) {
    const body = Object.assign({}, baseBody, { messages });
    resp = await callAnthropic(body);
    if (resp.stop_reason === 'pause_turn') {
      messages.push({ role: 'assistant', content: resp.content });
      continue;
    }
    break;
  }

  const text = collectText(resp && resp.content);
  const parsed = extractJSON(text);
  return normalize(parsed, levelKey);
}

// --------------------------------------------------------------------------
// HTTP handling
// --------------------------------------------------------------------------

function sendJSON(res, status, obj) {
  const payload = Buffer.from(JSON.stringify(obj));
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  res.end(payload);
}

function serveStatic(req, res) {
  let urlPath = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  if (urlPath === '/') urlPath = '/index.html';

  const filePath = path.normalize(path.join(PUBLIC_DIR, urlPath));
  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
      res.end('Not found');
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { 'content-type': MIME[ext] || 'application/octet-stream' });
    res.end(data);
  });
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (c) => {
      size += c.length;
      if (size > 1e6) {
        reject(new Error('Request body too large'));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  const { pathname } = new URL(req.url, 'http://localhost');

  if (req.method === 'POST' && pathname === '/api/generate') {
    try {
      if (!API_KEY) {
        return sendJSON(res, 500, {
          error:
            'Server is missing ANTHROPIC_API_KEY. Set it in the environment and restart the server.',
        });
      }
      const raw = await readBody(req);
      const params = raw ? JSON.parse(raw) : {};
      const levelKey = LEVELS[params.level] ? params.level : 'junior';
      const topic = typeof params.topic === 'string' ? params.topic.trim().slice(0, 200) : '';
      const useSearch = Boolean(params.useSearch);

      let result;
      try {
        result = await generateTest(levelKey, topic, useSearch);
      } catch (e) {
        // If search-grounded generation fails (e.g. tool unavailable), fall back
        // to plain generation so the user still gets a test.
        if (useSearch) {
          result = await generateTest(levelKey, topic, false);
          result.note = 'Web search was unavailable; generated from the model knowledge instead.';
        } else {
          throw e;
        }
      }
      return sendJSON(res, 200, result);
    } catch (e) {
      return sendJSON(res, 500, { error: e.message || String(e) });
    }
  }

  if (req.method === 'GET' && pathname === '/api/health') {
    return sendJSON(res, 200, { ok: true, model: MODEL, hasApiKey: Boolean(API_KEY) });
  }

  if (req.method === 'GET') {
    return serveStatic(req, res);
  }

  res.writeHead(405, { 'content-type': 'text/plain; charset=utf-8' });
  res.end('Method not allowed');
});

server.listen(PORT, () => {
  console.log(`Reading comprehension server listening on http://localhost:${PORT}`);
  console.log(`Model: ${MODEL}  |  API base: ${API_BASE}  |  API key: ${API_KEY ? 'set' : 'MISSING'}`);
});
