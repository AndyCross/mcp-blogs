+++
title = "Streaming LLM Responses: A Partial JSON Parser for Structured Output"
date = "2024-12-11"
draft = false
tags = ["llm", "ai", "typescript", "streaming"]
+++

I've been building conversational AI features recently, and I hit an annoying problem: I want *structured* responses from the LLM (JSON with specific fields), but I also want to *stream* the response text to the user as it generates. These two goals don't play nicely together.

When you ask an LLM to respond with structured JSON, you can't show anything to the user until the entire response arrives and parses successfully. That's a rubbish user experience. Users stare at a spinner for seconds while the model churns through tokens that could already be on screen.

So I wrote a partial JSON parser. It's scrappy, it's specific to my use case, and it works beautifully.

## The Problem

Here's the situation. I'm building a chat interface where the LLM returns structured data:

```json
{
  "response": "Here's what I found about your skin type...",
  "language": "en",
  "suggestedTents": [{"id": "1", "name": "Beach Tent", "number": "42"}],
  "suggestedMenus": [{"id": "a", "name": "Lunch Special", "price": "€12"}]
}
```

The model wraps this in markdown code fences (because of course it does), and I need to:

1. Show the `response` text immediately as it streams in
2. Eventually parse the complete JSON for the structured fields
3. Handle the fact that for most of the stream, the JSON is *incomplete*

Standard `JSON.parse()` throws on incomplete input. And waiting for completion defeats the purpose of streaming.

## The Insight

Here's the trick: for partial display, I don't need to parse the whole JSON. I just need to extract the `response` string value as it grows, character by character.

JSON string values have predictable structure:

- They start with `"`
- They end with an unescaped `"`  
- Everything in between is content (with escape sequences like `\n`, `\"`, `\uXXXX`)

If I can find `"response"` followed by `:` followed by `"`, I can walk the string character-by-character, handling escapes, and extract whatever's been received so far.

## The Parser

Here's the implementation. It's TypeScript, deliberately simple, and handles the specific format I need:

```typescript
/**
 * Extract the response text from a partial JSON string.
 * Handles the markdown code fence wrapper and incomplete JSON.
 */
export function extractResponseFromPartialJson(partialText: string): string | null {
  // Remove markdown code fences if present
  let json = partialText;
  
  // Strip ```json prefix
  const jsonStart = json.indexOf('```json');
  if (jsonStart !== -1) {
    json = json.substring(jsonStart + 7);
  }
  
  // Strip trailing ``` if present
  const jsonEnd = json.lastIndexOf('```');
  if (jsonEnd !== -1) {
    json = json.substring(0, jsonEnd);
  }
  
  json = json.trim();
  
  if (!json) return null;
  
  // Find the "response" field
  const responseKeyIndex = json.indexOf('"response"');
  if (responseKeyIndex === -1) return null;
  
  // Find the colon after "response"
  const colonIndex = json.indexOf(':', responseKeyIndex + 10);
  if (colonIndex === -1) return null;
  
  // Find the opening quote of the value
  const valueStart = json.indexOf('"', colonIndex);
  if (valueStart === -1) return null;
  
  // Extract the string value, handling escape sequences
  let result = '';
  let i = valueStart + 1;
  let escaped = false;
  
  while (i < json.length) {
    const char = json[i];
    
    if (escaped) {
      // Handle escape sequences
      switch (char) {
        case 'n': result += '\n'; break;
        case 'r': result += '\r'; break;
        case 't': result += '\t'; break;
        case '"': result += '"'; break;
        case '\\': result += '\\'; break;
        case '/': result += '/'; break;
        case 'b': result += '\b'; break;
        case 'f': result += '\f'; break;
        case 'u':
          // Unicode escape \uXXXX
          if (i + 4 < json.length) {
            const hex = json.substring(i + 1, i + 5);
            const code = parseInt(hex, 16);
            if (!isNaN(code)) {
              result += String.fromCharCode(code);
              i += 4;
            }
          }
          break;
        default:
          // Unknown escape, just add the char
          result += char;
      }
      escaped = false;
    } else if (char === '\\') {
      escaped = true;
    } else if (char === '"') {
      // End of string value - this is the complete response
      break;
    } else {
      result += char;
    }
    
    i++;
  }
  
  return result;
}
```

The key points:

| Aspect | How it's handled |
|--------|------------------|
| Code fences | Strip ```` ```json ```` prefix and ```` ``` ```` suffix |
| Field location | Simple `indexOf` for `"response"` |
| String parsing | Character-by-character with escape handling |
| Incomplete input | Returns whatever's been received so far |
| Complete input | Stops at the closing `"` |

## Completing the Picture

Once the stream finishes, you want the full structured data. That's straightforward:

```typescript
export interface ParsedResponse {
  response: string;
  language?: string;
  suggestedTents?: Array<{ id: string; name: string; number: string }>;
  suggestedMenus?: Array<{ id: string; name: string; price?: string; TentId?: string }>;
}

export function tryParseCompleteJson(text: string): ParsedResponse | null {
  // Remove markdown code fences
  let json = text;
  
  const jsonStart = json.indexOf('```json');
  if (jsonStart !== -1) {
    json = json.substring(jsonStart + 7);
  }
  
  const jsonEnd = json.lastIndexOf('```');
  if (jsonEnd !== -1) {
    json = json.substring(0, jsonEnd);
  }
  
  json = json.trim();
  
  if (!json) return null;
  
  try {
    const parsed = JSON.parse(json);
    if (typeof parsed.response === 'string') {
      return {
        response: parsed.response,
        language: parsed.language,
        suggestedTents: parsed.suggestedTents,
        suggestedMenus: parsed.suggestedMenus,
      };
    }
  } catch {
    // JSON not complete yet
  }
  
  return null;
}
```

## Using It in Practice

Here's the pattern I use in my streaming handler:

```typescript
let accumulated = '';

for await (const chunk of stream) {
  accumulated += chunk.text;
  
  // Try to show partial response immediately
  const partial = extractResponseFromPartialJson(accumulated);
  if (partial) {
    updateUI(partial);  // User sees text appearing in real-time
  }
}

// Stream complete - parse full structure
const complete = tryParseCompleteJson(accumulated);
if (complete) {
  // Now we have language, suggestions, etc.
  handleStructuredResponse(complete);
}
```

The user sees the response text appearing token-by-token, exactly like a normal chat. But at the end, I get the full structured data for rendering suggestions, detecting language, whatever else the schema includes.

## Why Not Use a Streaming JSON Library?

There are proper streaming JSON parsers out there. But they're solving a different problem: parsing arbitrarily nested JSON incrementally. That's complex. My needs are simpler:

1. I only care about one field (`response`)
2. The structure is known and flat
3. The value I need is always a string
4. I'm already handling the stream myself

A 90-line function that does exactly what I need beats a dependency that does everything I don't.

## The Tradeoffs

This approach is deliberately limited:

**Works for:**
- Known JSON structure with a string field you want to stream
- Markdown-wrapped JSON (common with LLMs)
- Real-time display of text content

**Doesn't handle:**
- Nested objects you need to stream
- Arrays as the streaming target
- Unknown or dynamic schemas
- Non-string values

If your needs are more complex, look at something like [partial-json-parser](https://www.npmjs.com/package/partial-json-parser) or build state-machine-based parsing. But for the "show the text while I wait for the full response" use case, this is plenty.

## The UX Win

Before this, users waited 3-4 seconds staring at nothing while the model generated a full response. Now they see text appearing immediately, exactly like ChatGPT or Claude's native interfaces.

The structured data still arrives at the end, but by then the user has already read most of the response. The suggestions and metadata feel like a bonus, not something they waited for.

Small change, significant improvement. That's the kind of optimisation I like.

---

*The full parser code is [available as a Gist](https://gist.github.com/AndyCross/86a29ad97f8f24fb37b61f8bff72f4a0). MIT licensed, copy-paste friendly. Adapt it to your schema and streaming setup.*
