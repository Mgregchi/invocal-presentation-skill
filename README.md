# Invocal Presentation Skill

Narration-led video production for AI agents.

Turn a topic or brief into researched scripts, original Invocal narration, word-aligned visual reveals, an editable PowerPoint, captions and a verified MP4. The current workflow specializes in educational lessons and explainers. 

## Install

### ChatGPT workspace
A workspace administrator can import this repository through Admin Console → Plugins → Add → Import marketplace. Use the repository root; the catalogue is `.agents/plugins/marketplace.json`. Each member needs their own authorized Invocal connection. Account and workspace support varies; a GitHub URL does not automatically install a plugin into every personal ChatGPT account.

### Codex plugin marketplace
Add this repository using your Codex client's supported GitHub marketplace flow, then install `invocal-presentation-skill`. The plugin source is `plugins/invocal-presentation-skill`.

### Standalone skill
Ask a compatible agent's skill installer to install `plugins/invocal-presentation-skill/skills/invocal-presentation` from this repository. Installation methods differ between agents; follow the host's documented process.

## Requirements

- An authorized Invocal MCP connection for speech synthesis, artifact URLs and Azure word timestamps.
- A network-enabled execution environment able to retrieve Invocal artifacts.
- Python with Pillow and NumPy; FFmpeg and FFprobe; curl; suitable fonts.
- Research access and editable presentation authoring/rendering.
- The included optional Work renderer requires the host-supplied `@oai/artifact-tool`. It is not a portable public dependency. Other hosts must supply a renderer matching the documented frame/state contract.

## Use

> Use Invocal Presentation Skill to create a three-minute explainer about photosynthesis for secondary-school learners. Use Invocal narration and deliver the MP4, editable PPTX, scripts, captions, timing manifest and QA report.

Start with a setup check before commissioning a full production.

## Verified scope

Short photosynthesis and IP-address lessons were produced with Invocal narration, progressive reveals and encoded video verification. A longer breast-cancer lesson established the original workflow. The repository contains production helpers, not a hosted rendering service. Continuous chart animation, presenter avatars and lip-sync remain future validation work.

## Structure

- `plugins/invocal-presentation-skill/plugin.json`: portable plugin manifest.
- `plugins/invocal-presentation-skill/skills/invocal-presentation/`: instructions, scripts and references.
- `.agents/plugins/marketplace.json`: GitHub marketplace catalogue.

Invocal remains a separately authorized service. No credentials, signed artifact URLs, private job IDs or narration recordings are distributed here.

## Quality gates

Validate downloaded WAV format, metadata and duration; use actual word-boundary timings; inspect all slides and sampled cue frames; decode the final MP4; verify its audio stream and source correlation; deliver a QA report. A successful encoder exit alone is insufficient.

## Repository

Repository: `Mgregchi/invocal-presentation-skill`.

For Codex clients that support the marketplace CLI:

```sh
codex plugin marketplace add Mgregchi/invocal-presentation-skill
```

Then install `invocal-presentation-skill` through the client plugin interface.

For a standalone skill installer, supply repository `Mgregchi/invocal-presentation-skill` and path `plugins/invocal-presentation-skill/skills/invocal-presentation`.

