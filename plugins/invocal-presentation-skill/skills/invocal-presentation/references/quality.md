# Production acceptance

## Before rendering

Verify authoritative evidence, audience suitability, exact submitted narration scripts, complete Invocal job metadata/timelines and source-image permissions. Decode every WAV fully, inspect its RIFF/WAVE header, check PCM parameters and compare sample-derived duration with metadata. Track source checksums. Do not use mocked word timestamps in a real deliverable.

## Before encoding

Inspect every slide individually, not only a montage. Check factual accuracy, meaningful image choice, label/callout alignment, fonts, margins, clipping, text collisions, escaped newline strings and reference coverage. Inspect intermediate reveal states and removal of old focus markers. Complete the host's presentation structural/layout/font checks.

Validate all PNGs and make them consistent in dimensions/pixel format. The encoder normalizes all image inputs, including settled states, to RGB. It encodes narration independently to AAC, then copies that audio during video muxing. Preserve the preparer’s explicitly recorded minimum 200 ms final hold when there is no other trailing pause; removing it can truncate the decoded AAC tail after muxing. Mixing RGB transition images with RGBA presentation images previously caused lingering blends in the tested concat pipeline. Keep each build immutable and isolated. Finish writing images before starting FFmpeg; use fresh output names and atomic writes if adding concurrency.

## Encoded-file acceptance

Run the bundled verifier, then review the extracted evidence. It must confirm:

- Actual H.264 video, intended dimensions/duration, AAC audio, optional subtitle stream and complete error-free decoding.
- Source WAV duration/format checks and full-length AAC-to-original waveform comparisons at the scheduled offsets. Correlation must exceed 0.97 and encoded narration must have a substantial signal. Missing/truncated audio must fail.
- Every scene appears and matches a settled expected state. Compare actual encoded frames, not only render inputs.
- Visual states appear at actual word-aligned event times. Quantization adds less than a frame of onset delay; the short dissolve finishes later. Do not confuse onset with fully visible text.
- Captions use actual word times and preserve timestamps after muxing. Inspect line length/readability and absence of slide obstruction in the chosen playback mode.
- Beginning/middle/end frames exist for every narration section. Inspect those, the opening, the ending, transitions and exact structural callouts. Check long unchanged intervals contextually.
- Editable deck has one slide and narration notes per scene. Confirm any promised native chart/table editability separately. Record any host/application review that was not performed.

The automated verifier intentionally reports `automated_checks_passed_visual_review_required`. A numerical pass is not instructional, clinical, aesthetic or independent listening approval. Pixel error can miss a small wrong label, and waveform correlation cannot assess pronunciation. Listen where available; otherwise state the systematic audio review method without inventing a listening pass. Inspect source/encoded cue meaning, not only timestamp arithmetic.

If a requirement fails, repair and rerun that stage plus relevant downstream checks. Preserve test evidence and ship only the accepted revision.

## QA report and delivery

Record output properties; active job IDs/voice/rate; original and encoded durations; wave/stream checks; source correlation; slides and events checked; maximum cue-onset rounding; caption checks; visual-review checkpoints; factual/image-attribution review; corrections; material limitations; and delivery checksums. State which checks were automated and which involved visual/listening/application review.

Deliver the MP4, editable PPTX, scripts with sources, complete timing manifest, SRT and QA report. Save persistently using the host's artifact integration, inspect every save result and ensure user download links point to actual finalized files. For explicit byte-verification requests, retrieve saved copies and compare checksums through the host's supported transfer route. Never include private signed URLs or credentials.

Reviewers must be able to distinguish a complete film from a silent or single-frame prototype. A successful encoding command, an existing MP4 file or a large frame count alone is insufficient evidence.
