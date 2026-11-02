# Invocal Presentation Skill setup

1. Install this plugin using your host’s supported plugin-import flow.
2. Connect Invocal in the recipient’s own account. The package reuses an existing authorized Invocal connection; it contains no credentials and does not create or modify Invocal infrastructure.
3. Ask the plugin to check setup. Its preflight checks FFmpeg, FFprobe, Pillow and NumPy; the agent must also confirm research access, fonts and editable presentation rendering. The supplied Work presentation adapter requires the host-provided @oai/artifact-tool runtime. Another host needs a compatible renderer producing the same frame/state contract.
4. Request a topic, audience, approximate duration and language. The skill completes research, narration, visuals, MP4 encoding and verification, and delivers editable slides, scripts, timing JSON, SRT and a QA report.

This package contains instructions and production helpers, not a separately hosted rendering API. Plugin installation alone cannot grant missing execution capabilities. There is no bundled MCP server configuration that restricts the package to desktop; Invocal is a separately connected dependency.

The baseline has been tested with short photosynthesis and IP-address lessons using Invocal. Existing breast-cancer production established the longer lesson workflow. Discrete reveals, focus markers and short dissolves are supported. Version 1.1 adds an optional continuous renderer for positive bars, progressive lines, moving endpoints and text entrances. See references/motion.md for host requirements and limitations. Avatars, lip-sync and independent clinical sign-off remain outside the validated scope.

## Distribution

The generated ChatGPT plugin starts private. Public directory publication and workspace sharing are separate permissions/workflows. A private plugin URL does not grant access to another user. Distribute this archive through an authorized channel for recipients whose host supports package upload, or complete the platform’s public-submission process. Recipients must use their own Invocal authorization and a compatible host.

No account-specific job IDs, narration recordings, signed URLs or secrets are included. The original standalone personal skill remains installed; this plugin is a separate packaged release.
