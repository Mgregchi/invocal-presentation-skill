# Invocal narration acquisition

Discover the actual Invocal MCP tools in the connected host. Expected service operations include creating narration, reading job state, creating an artifact URL and reading a word timeline. Namespaces vary. Inspect schemas rather than assuming undocumented REST endpoints or authentication headers.

1. Submit the exact researched script through `create_narration_job`, preserving the requested voice/rate and `text` or validated `ssml` mode.
2. Store the actual returned job ID. Poll `get_narration_job` until completed, honoring errors/retry guidance. Do not immediately resubmit a slow job or assume a failed tool call created nothing.
3. Save job metadata, exact script and selected voice/rate. Never invent durations.
4. Call `get_narration_timeline` with supported pagination (the tested service allowed limits 1–200). Continue until `hasMore` is false. Preserve pages unchanged as JSON; verify contiguous offsets and the total word count.
5. Request `get_narration_artifact_url(job_id, kind="audio")` immediately before download. Keep its private signed URL out of reports and manifests.
6. Invoke curl with an argument array, `--fail --silent --show-error --location --max-time 45`, and a local output filename. Check the result, local size, actual RIFF/WAVE header, complete PCM decode and exact duration against metadata.

If Python's HTTP client receives an error, test curl and inspect the actual error/status. A previous Work run received Python HTTP 403 while curl succeeded. This observation does not grant a bypass for host restrictions or authentication. Do not change Invocal infrastructure or transfer narration through another external storage service without a separate authorized reason.

If signed-URL download fails, inspect `get_narration_audio_chunk` if available. Use actual documented fields for bytes/offset/length/total/EOF; never assume a response shape. Decode valid Base64, enforce contiguous non-overlapping offsets, track total bytes and reject incomplete coverage. Validate the reconstructed WAV and duration. The original production did not exercise this fallback; disclose that it is untested until verified on the current run.

A new user needs their own authorized Invocal connection and service access. Installing or sharing this skill grants neither credentials nor another user's jobs. Do not hard-code an owner's URL, PAT, job IDs or artifact contents into the skill. Do not silently synthesize speech with another provider.
