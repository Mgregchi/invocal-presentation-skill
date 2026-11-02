# Project contract

Use UTF-8 JSON. Paths in the project are relative to the project file. Build and render outputs are resolved absolute paths; final delivery may strip machine-specific paths. Author the topic and design afresh rather than copying an old lesson.

## Top-level fields

- `title`: lesson title.
- `audience`, `voice`, `rate`, `sources`: preserve the brief and evidence. Source entries are URL-bearing strings.
- `resolution`: defaults to `[1920,1080]`; use positive even dimensions.
- `slide_size`: defaults to `[1280,720]`; use the same aspect ratio as output.
- `fps`: integer, default 25.
- `font`: actual installed font, default DejaVu Sans in the optional Work adapter.
- `section_gap_seconds`: default 0.65, inserted after each narration section.
- `credits_hold_seconds`: default 8. Add an explicit non-narrated reference scene, or set this to zero.
- `transition_seconds`: default 0.24.

The preparer records `codec_tail_padding_seconds` and adds only enough final-frame/audio hold to leave at least 200 ms after the last spoken section when both the configured last gap and reference hold would otherwise be shorter. Word times do not shift. Default 650 ms section pauses already cover this guard; zero-gap/zero-credit lessons gain 200 ms at the end. This protects AAC/resampling EOF samples and is included in the manifest duration.
- `caption_language`: three-letter subtitle language code, default `eng`.
- `sections`: narration order.
- `scenes`: chronological visual order; first scene starts at zero.

## Section records

Require `id`, actual `job_id`, exact submitted `script`, `wav`, `job_metadata`, `timeline` and `sources`.

`job_metadata` points to a JSON file containing the actual get-job result, directly or wrapped as MCP JSON. `timeline` points to one JSON response or an ordered list of page files. Do not hand-author word timestamps. Required timeline fields include `words`, `wordCount`, `offset`, `hasMore` and `timingMethod: "azure-sdk-word-boundary"`. Each word needs `text`, `start` and `end`. Page offsets must be contiguous and the final page must have `hasMore: false`.

The helper only accepts completed jobs, matching job IDs, complete WAVs and 24 kHz mono 16-bit PCM. Preserve downloaded originals and metadata. Validate any explicit format conversion separately.

## Anchors

Use `"START"`, a unique phrase string, `{"phrase":"...","occurrence":2}` (one-based), or `{"word_index":12}` (zero-based).

Anchors are section-relative spoken word starts. A scene's `anchor` determines its global start. Element anchors use the same section timeline, not a relative offset from the scene. Repeated phrases without an occurrence are rejected. Indices remain valid only for the exact script/timeline revision.

## Scene records

Use alphanumeric IDs with optional hyphens/underscores, beginning with a letter or digit. Require a unique `id`, `section` ID, `anchor`, `title`, `elements`. Add `background` and `notes` as appropriate. Use `section: null` for the reference hold. Scene ends come from the next scene's start; do not overlap or reorder scenes silently.

An element has a unique `id` within its scene, `type`, and `position: [x,y,width,height]` in slide-canvas coordinates. Supported types in the optional adapter:

- `text`: `text`, `font_size`, `font`, `bold`, `color`; normal UTF-8 newline characters, not escaped display strings.
- `image`: `src`, `alt`, `fit` (`contain` or `cover`) and `attribution` including creator/source/license URL. File extension must reflect its content; normalize assets to PNG or JPEG when necessary.
- `outline`: `color`, `line_width`; use only for meaningful annotations over sourced visuals. Give it `until_anchor` to clear focus on time. The bundled adapter supports timed removal for outline annotations only.

Omit an element's `anchor` to show it when the scene starts. Otherwise show it at its anchored word. An element's `until_anchor`, when used, must occur after its start and no later than the scene end. Render the state after every co-timed change. Ensure invisible/removed objects do not leave an old pointer on a new concept.

## Illustrative minimal project

Replace placeholders with real Invocal outputs and independently researched teaching content. This is configuration guidance, not synthesized test data.

```json
{
  "title": "A short lesson",
  "audience": "General adults",
  "voice": "en-US-JennyNeural",
  "rate": "-5%",
  "sources": ["Organization: source title https://source.example"],
  "credits_hold_seconds": 0,
  "sections": [{
    "id": "opening",
    "job_id": "ACTUAL_JOB_ID",
    "script": "EXACT SUBMITTED SCRIPT",
    "wav": "audio/opening.wav",
    "job_metadata": "audio/opening-job.json",
    "timeline": ["audio/opening-words-000.json"],
    "sources": ["Source URL"]
  }],
  "scenes": [{
    "id": "scene-01",
    "section": "opening",
    "anchor": "START",
    "title": "A short lesson",
    "background": "#FAF9F6",
    "notes": "Explain the concept and credit its sources.",
    "elements": [{
      "id": "heading", "type": "text",
      "position": [64,80,1140,100],
      "text": "A short lesson", "font_size": 48, "bold": true
    }, {
      "id": "point", "type": "text",
      "position": [64,280,1140,150],
      "text": "A concise supporting point", "font_size": 32,
      "anchor": {"phrase": "ACTUAL UNIQUE SPOKEN PHRASE"}
    }]
  }]
}
```

## Renderer output contract

Provide a JSON array of cumulative state records:

```json
[
  {"scene":"scene-01","time":0,"path":"state-000.png"},
  {"scene":"scene-01","time":2.5,"path":"state-001.png"}
]
```

Times are global seconds from actual prepared word anchors, not estimates. Paths may be absolute or relative to this state-list file. All frames must have identical dimensions and opaque background. The encoder converts every still and transition to RGB. Preserve scene IDs for verification. The helper quantizes starts forward to the next frame, adding less than one frame of rounding delay.

## Final timing manifest

Preserve prepared sections, job metadata, original checksums, complete words, scene intervals, captions, sources and image attribution. Add scheduled/encoded events from `encoded-events.json`; strip local `path` fields from the public copy when unnecessary. Include actual output duration and QA summary. Do not save signed URLs or credentials. Keep an internal build copy with original source paths so verification remains reproducible.
