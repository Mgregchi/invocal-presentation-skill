# Motion validation example

This uses synthetic chart data, not empirical observations. Generate the exact script in `motion-project.json` through your own authorized Invocal connection. Save its WAV, metadata and complete timeline under `examples/audio/`, and replace the placeholder job ID. The example contains no private recording or service credentials.

Run the skill's `pipeline.py prepare`, `render_motion.py`, `pipeline.py encode` and `pipeline.py verify` commands as described in `references/motion.md` and the main skill. Use a new directory per build. Use the Work adapter separately for editable chart slides and complete host presentation finalization. Do not claim PowerPoint animation: the deck contains editable final states.

The test script exercises three bar growth intervals, a baseline highlight, four line point cues, two scene transitions and text entrances.
