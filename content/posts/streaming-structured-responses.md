+++
title = "Streaming AI Responses from Server to Screen"
date = "2026-03-24"
draft = true
tags = ["ai", "streaming", "sse", "typescript", "csharp", "react-native"]
+++

I wrote previously about [a partial JSON parser](/posts/streaming-json-partial-parser/) for extracting text from incomplete LLM responses as they stream in. That post covered one specific piece: pulling the `response` field out of a half-received JSON object so users see text immediately.

But that parser lives inside a larger system. There's a server emitting tokens over SSE, a chunk protocol that handles tool execution mid-response, a transport layer that works on React Native (barely), and a rendering pipeline that switches from plain text to rich content when the stream completes. The parser was the fun bit to write about. The pipeline around it is where the real engineering decisions live.

## Four Problems at Once

When you're building conversational AI backed by an LLM with tool-use, you hit four problems simultaneously:

**Users want immediate feedback.** Text should appear token-by-token as it generates. Nobody wants to stare at a spinner for four seconds.

**The UI needs structured data.** Suggested items, navigation targets, metadata. These should render as interactive cards, not inline text peppered with UUIDs.

**Tool execution is invisible.** The LLM might pause mid-response to run a server-side tool (a database query, a search index lookup). The user needs to know something is happening during that pause.

**JSON isn't streamable.** You can't `JSON.parse()` a half-received object. I covered the solution to this one [already](/posts/streaming-json-partial-parser/).

The pattern I've settled on combines an SSE chunk protocol with a fenced-JSON output format and the partial parser on the client. This post covers the parts I haven't written about yet.

---

## The SSE Chunk Protocol

The server streams responses as Server-Sent Events. Each event carries a JSON payload with a `type` discriminator. Six types cover everything:

| Type | Purpose | Key Fields |
|------|---------|------------|
| `started` | Session created | `conversationId` |
| `delta` | Text fragment from LLM | `text` |
| `tool_start` | LLM invoked a tool | `toolName`, `toolDescription` |
| `tool_complete` | Tool finished | `toolName`, `text` |
| `complete` | Final structured response | `text`, `suggestedItems`, `suggestedLocations` |
| `error` | Something broke | `error` |

A typical sequence for "Where can I find seafood?" looks like this:

```
1. { "type": "started", "conversationId": "abc-123" }
2. { "type": "delta", "text": "Let me look" }
3. { "type": "delta", "text": " that up for you..." }
4. { "type": "tool_start", "toolName": "search_catalog", "toolDescription": "Searching for 'seafood'..." }
   // Tool executes (database query)
5. { "type": "tool_complete", "toolName": "search_catalog", "text": "completed" }
6. { "type": "delta", "text": "I found several options!" }
7. { "type": "complete", "text": "I found several options! ...", "suggestedLocations": [...] }
```

`tool_start` fires the instant the LLM decides to call a tool. `tool_complete` fires when execution finishes. The UI gets an accurate loading state during data fetches without any polling or guesswork.

The chunk type as a discriminated union in TypeScript:

```typescript
interface StreamChunk {
  type: 'started' | 'delta' | 'tool_start' | 'tool_complete' | 'complete' | 'error';
  conversationId?: string;
  text?: string;
  toolName?: string;
  toolDescription?: string;
  suggestedItems?: SuggestedItem[];
  suggestedLocations?: SuggestedLocation[];
  error?: string;
}
```

---

## Why Fenced JSON

I covered the parser in the [previous post](/posts/streaming-json-partial-parser/), but I didn't explain why the LLM wraps everything in a markdown code fence in the first place. The system prompt tells the model to respond like this:

```
Reply in a JSON message with the following format:
{
  "response": "<your natural language response>",
  "language": "<response language code>",
  "suggestedLocations": [{ "id": "...", "name": "...", "label": "..." }],
  "suggestedItems": [{ "id": "...", "name": "...", "price": "..." }]
}
Surround the JSON with ```json and ```.
Never put IDs in the response text, only in the structured arrays.
```

Three reasons for the fence.

**Clean separation.** LLMs sometimes emit thinking text before the JSON. The fence boundary tells the parser exactly where structured data begins and preamble ends.

**Partial extraction.** The `response` field always comes first. The [partial parser](/posts/streaming-json-partial-parser/) can extract readable text from an incomplete JSON string while the rest of the object is still streaming.

**LLM grounding.** Forcing the model to output structured JSON with entity IDs in specific arrays reduces hallucination of entity references in the prose. Telling it "never put IDs in the response text" keeps the conversation clean of UUID noise.

You might ask: why not just carry all the structured data in the `complete` chunk and skip the fenced JSON entirely? Redundancy. If the SSE connection drops after the last delta but before the complete chunk, the client can still attempt to parse whatever it received. The fenced JSON in the delta stream acts as a fallback. It costs almost nothing and makes the system more resilient to dropped connections.

---

## Server-Side Streaming in C#

The server uses `IAsyncEnumerable<StreamChunk>` to yield chunks as the LLM generates them. Most of the plumbing is straightforward, but the tool-use loop is where it gets gnarly.

An LLM with tool-use doesn't just generate text and stop. It might generate some text, decide it needs data, request a tool call, wait for the result, then continue generating. This can happen multiple times in a single response. The server needs to handle that loop while streaming everything to the client in real-time.

```csharp
public async IAsyncEnumerable<StreamChunk> StreamConversationAsync(
    string conversationId,
    string prompt,
    string contextId,
    string language = "en",
    [EnumeratorCancellation] CancellationToken ct = default)
{
    yield return StreamChunk.Started(conversationId);

    var responseBuilder = new StringBuilder();
    int iteration = 0;
    const int maxIterations = 5;

    while (iteration++ < maxIterations)
    {
        await foreach (var sseEvent in llmClient.StreamAsync(messages, tools, ct))
        {
            if (sseEvent.IsTextDelta)
            {
                responseBuilder.Append(sseEvent.Text);
                yield return StreamChunk.Delta(sseEvent.Text);
            }

            if (sseEvent.IsToolUse)
            {
                TrackToolBlock(sseEvent);
            }
        }

        var pendingTools = GetPendingToolCalls();
        if (pendingTools.Count == 0) break;

        foreach (var tool in pendingTools)
        {
            var description = GetToolDescription(tool.Name, tool.Input, language);
            yield return StreamChunk.ToolStart(tool.Name, description);

            var (result, success) = await ExecuteToolAsync(
                tool.Name, tool.Input, contextId, language);

            AddToolResultToMessages(tool.Id, result, success);
            yield return StreamChunk.ToolComplete(tool.Name, success);
        }
    }

    var finalText = responseBuilder.ToString();
    var parsed = ParseStructuredResponse(finalText);
    yield return StreamChunk.Complete(
        parsed.Response, parsed.SuggestedLocations, parsed.SuggestedItems);
}
```

The `maxIterations` cap matters. Without it, a model that keeps requesting tools without converging could loop forever. Five iterations has been plenty in practice.

Each iteration works the same way: stream tokens from the LLM, yield delta chunks for text, track any tool requests. When the LLM's turn ends, check if it requested tools. If not, we're done. If so, execute each tool, yield the start/complete notifications, feed the results back into the conversation, and let the LLM continue.

The ASP.NET controller writes each chunk as an SSE event:

```csharp
[HttpPost("stream")]
public async Task StreamConversation([FromBody] StartRequest request)
{
    Response.ContentType = "text/event-stream";
    Response.Headers["Cache-Control"] = "no-cache";
    Response.Headers["Connection"] = "keep-alive";

    await foreach (var chunk in service.StreamConversationAsync(
        request.ConversationId, request.Prompt,
        request.ContextId, request.Language))
    {
        var json = JsonSerializer.Serialize(chunk);
        await Response.WriteAsync($"event: chunk\ndata: {json}\n\n");
        await Response.Body.FlushAsync();
    }
}
```

Nothing revolutionary there. The `FlushAsync()` after each chunk is the only bit that matters. Without it, ASP.NET buffers the response and your "streaming" endpoint sends everything in one go at the end.

---

## Client Transport on React Native

This is where things get slightly annoying. React Native's `fetch` doesn't reliably support `ReadableStream`. The `EventSource` API only supports GET requests, and this endpoint uses POST with an auth header. So the client falls back to `XMLHttpRequest` with `onprogress` parsing:

```typescript
function streamWithXHR(
  url: string,
  body: object,
  onChunk: (chunk: StreamChunk) => void,
  onError: (error: string) => void,
  token: string | null,
  onComplete: () => void
): void {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', url, true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);

  let lastProcessedIndex = 0;
  let buffer = '';

  xhr.onprogress = () => {
    const newData = xhr.responseText.substring(lastProcessedIndex);
    lastProcessedIndex = xhr.responseText.length;
    buffer += newData;

    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    let currentEvent = '';
    let currentData = '';

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        currentData = line.slice(6);
      } else if (line === '' && currentEvent && currentData) {
        try {
          onChunk(JSON.parse(currentData));
        } catch (e) {
          console.error('Failed to parse SSE data:', currentData);
        }
        currentEvent = '';
        currentData = '';
      }
    }
  };

  xhr.onload = () => onComplete();
  xhr.onerror = () => onError('Network error');
  xhr.ontimeout = () => onError('Request timed out');
  xhr.send(JSON.stringify(body));
}
```

It's a hand-rolled SSE parser inside `onprogress`. We track how much of `responseText` we've already processed, buffer incomplete lines, and parse complete SSE events as they arrive. Not elegant. Works everywhere.

For web clients, `fetch` with `ReadableStream` is the better choice. The XHR approach is specifically for React Native's limitations.

---

## Chunk Routing and Two-Phase Rendering

On the client, each chunk type routes to the appropriate state update:

```typescript
const rawResponse = useRef('');

function handleChunk(chunk: StreamChunk) {
  switch (chunk.type) {
    case 'started':
      setConversationId(chunk.conversationId);
      break;

    case 'delta':
      rawResponse.current += chunk.text;
      const partial = extractResponseFromPartialJson(rawResponse.current);
      updateAssistantMessage(partial || '');
      break;

    case 'tool_start':
      setToolStatus({ name: chunk.toolName, description: chunk.toolDescription });
      break;

    case 'tool_complete':
      setToolStatus(null);
      break;

    case 'complete':
      const parsed = tryParseCompleteJson(rawResponse.current);
      finalizeMessage(parsed, chunk);
      break;

    case 'error':
      handleError(chunk.error);
      break;
  }
}
```

The `delta` handler is where the partial parser from the [previous post](/posts/streaming-json-partial-parser/) plugs in. Every time a new text fragment arrives, it gets appended to the raw response, and the partial parser extracts whatever `response` text is available so far. That extracted text goes straight into the message bubble.

The rendering switches between two modes. During streaming, show plain text. On completion, switch to rich rendering with markdown and interactive cards:

```tsx
function MessageBubble({ message }: { message: Message }) {
  if (!message.isComplete) {
    return <Text>{message.content || '...'}</Text>;
  }

  return (
    <>
      <Markdown>{message.content}</Markdown>
      {message.suggestedLocations?.map(loc => (
        <SuggestionCard key={loc.id} item={loc} />
      ))}
    </>
  );
}
```

This avoids re-parsing markdown on every delta (expensive on mobile) and prevents layout thrash from partially-rendered structured data. During streaming the user sees text appearing character by character, like any chat interface. When the stream completes, the text reformats into markdown and suggestion cards appear below it. The transition is fast enough that users don't notice the switch.

---

## Tool Status UX

Tools that complete in under 100ms create a distracting flash of loading state. A spinner appears and vanishes before the user can read what it says. The fix is a minimum display time with a fade-out:

```typescript
const TOOL_MIN_DISPLAY_MS = 2000;
const TOOL_FADE_MS = 300;

useEffect(() => {
  if (toolStatus) {
    setVisibleToolStatus(toolStatus);
    shownAt.current = Date.now();
    fadeIn();
  } else if (visibleToolStatus) {
    const elapsed = Date.now() - shownAt.current;
    const remaining = Math.max(0, TOOL_MIN_DISPLAY_MS - elapsed);
    setTimeout(() => fadeOut(() => setVisibleToolStatus(null)), remaining);
  }
}, [toolStatus]);
```

Two seconds feels right. Long enough to read "Searching for seafood...", short enough not to feel like the app is stalling. If the tool takes longer than two seconds, the spinner stays until it finishes naturally.

---

## Delta Buffering

Rendering on every single delta causes jank, particularly on lower-end phones. Buffer the deltas and flush on a timer:

```typescript
const buffer = useRef<string[]>([]);

// In chunk handler:
case 'delta':
  buffer.current.push(chunk.text);
  break;

// Flush every 50ms:
useEffect(() => {
  const timer = setInterval(() => {
    if (buffer.current.length > 0) {
      rawResponse.current += buffer.current.join('');
      buffer.current = [];
      const partial = extractResponseFromPartialJson(rawResponse.current);
      updateAssistantMessage(partial || '');
    }
  }, 50);
  return () => clearInterval(timer);
}, []);
```

50ms is fast enough that text still appears to stream smoothly. Nobody can perceive a 50ms delay between tokens. But it reduces the number of re-renders significantly, especially when the LLM is generating quickly and deltas arrive in rapid bursts.

---

## Trade-offs Worth Knowing About

**Fenced JSON vs. separate complete payload.** The complete chunk is redundant with the fenced JSON. That's intentional. Connection resilience costs almost nothing here. The alternative (relying solely on the `complete` chunk for structured data) means a dropped connection at the wrong moment loses everything.

**Hand-rolled parser vs. streaming JSON library.** I only need one field during streaming. Everything else can wait for `JSON.parse()` when the stream finishes. A 90-line function that does exactly what I need beats a dependency that handles cases I don't have. I wrote about this in more detail in the [parser post](/posts/streaming-json-partial-parser/).

**XHR vs. fetch vs. EventSource.** `EventSource` only supports GET. React Native's `fetch` doesn't guarantee `ReadableStream`. `XHR.onprogress` works reliably across platforms for incremental access to response text. It's the least elegant option and the most pragmatic.

**maxIterations on tool-use.** Five might seem arbitrary. In practice, most responses need zero or one tool call. Complex queries occasionally need two or three. I've never seen a well-prompted model need more than four. Five gives headroom without risking runaway loops.

---

## Extending It

Adding a new suggestion type (say, `suggestedArticles`) is straightforward:

1. Add the array field to the JSON schema in the system prompt
2. Add it to `StreamChunk.Complete()` on the server
3. Add a card renderer on the client
4. Update the `ParsedResponse` interface

The partial parser doesn't need changes. It only extracts `response`. New fields are handled by `tryParseCompleteJson` on completion.

The protocol itself is LLM-provider-agnostic. The server's `IAsyncEnumerable<StreamChunk>` is a facade. Swap the LLM provider by changing the inner streaming call. The chunk protocol and client code stay identical. I've tested this with both Anthropic and OpenAI backends, and the client had no idea anything changed.

| Platform | Transport | Notes |
|----------|-----------|-------|
| React Native | `XMLHttpRequest.onprogress` | Most reliable cross-platform |
| Web (modern) | `fetch` + `ReadableStream` | Native streaming support |
| Web (legacy) | `EventSource` polyfill | Requires GET-to-POST adapter |

The chunk protocol over the wire is identical in all three cases. Only the transport layer differs.

---

*This is the companion piece to [Streaming LLM Responses: A Partial JSON Parser for Structured Output](/posts/streaming-json-partial-parser/), which covers the partial parser in detail. Together they describe the full pipeline for streaming structured AI responses in a React Native app backed by a .NET API.*
