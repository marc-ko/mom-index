# Chinese Semantic Prompt Design

## Goal

Rewrite the OpenRouter semantic-classification prompt in Simplified Chinese so
its instructions match the language and discourse patterns of the communities
being reviewed. Keep the existing machine-readable JSON contract unchanged.

## Scope

- Translate both the system message and user prompt into Simplified Chinese.
- Keep JSON field names in English.
- Keep `investment_intent` values as `buy`, `sell`, `hold`, and `unknown`.
- Add three short, contrasting few-shot examples.
- Do not change scoring, parsing, provider selection, fallback behavior, or the
  dashboard.

## Prompt Contract

The system message identifies the model as a classifier for Simplified Chinese
retail-investing community posts. It requires one valid JSON object only, with
no Markdown fences, commentary, or additional keys.

The user prompt defines the central distinction in Chinese:

- `author_is_beginner`: the post reveals that the author personally lacks basic
  knowledge, depends on others to decide, or reacts with beginner-level
  confusion.
- `targets_beginners`: the post is written for beginners, but its author may be
  an educator, experienced investor, or marketer.

Tutorials, summaries, reposts, quoted beginner questions, rhetorical questions,
memes, and marketing language must not by themselves establish that the author
is a beginner. Scores must be based on the author's own expressed stance and
the surrounding context.

The prompt describes every numeric range in Chinese while retaining the current
field names and ranges. `evidence` must contain short exact phrases copied from
the source post. When evidence is weak or the authorial voice is ambiguous, the
model must lower `confidence` rather than invent context.

## Few-Shot Examples

Use exactly three compact examples before the real input:

1. A genuine beginner asking how much a loss must recover, with high
   `author_is_beginner`, `decision_dependence`, and `basic_knowledge_gap`.
2. A beginner-oriented investment guide, with high `targets_beginners` but low
   `author_is_beginner`.
3. A beginner-oriented post asking readers to comment for materials, with high
   `targets_beginners` and `spam_or_marketing` but low `author_is_beginner`.

The examples use complete JSON objects but stay short. They illustrate the
classification boundary rather than attempting to cover every community style.
Their sample evidence must be copied exactly from their sample posts.

## Data Flow

`build_semantic_prompt()` inserts the three static examples, followed by the
real sector, title, and content. `build_openrouter_payload()` supplies the
Chinese system message and the generated user prompt. The existing response
parser receives the same JSON shape as before, so downstream scoring and
dashboard generation remain unchanged.

## Error Handling

Existing behavior remains intact: malformed responses, provider failures, or
missing credentials fall back to deterministic local classification. Prompt
language changes must not affect this path.

## Testing

Update the OpenRouter payload tests before changing production code. Tests must
verify that:

- the system message and user instructions are in Simplified Chinese;
- the old English instruction sentence is absent;
- all required English JSON keys and enum values remain present;
- all three contrasting examples are included;
- the real post's sector, title, and content are still interpolated;
- payload model selection, message roles, temperature, and response parsing are
  unchanged.

Run the semantic-classifier test group and the wider existing dashboard/history
regression tests after implementation.

## Acceptance Criteria

- OpenRouter receives Chinese classification instructions and three concise
  Chinese few-shot examples.
- The classifier still returns the existing JSON schema without parser changes.
- Educational and marketing posts remain distinguishable from genuine
  beginner-authored questions.
- Automated tests pass.
- No API key, chat content, generated dashboard data, or unrelated working-tree
  changes are committed.
- The change is committed locally and is not pushed.
