# Presentation and renderer adapters

Read the host's current presentation skill and API documentation. Its required destination, rendering and finalization rules take precedence over this optional adapter.

## Compatible Work runtime

Use `scripts/render_work.mjs MANIFEST.json NEW_RENDER_DIRECTORY` with the supplied primary Node runtime. It resolves `@oai/artifact-tool` from `CODEX_PRIMARY_RUNTIME_NODE_MODULES` or the active module search path. It does not install a package or copy private runtime helpers.

The adapter creates text, embedded images and instructional outline annotations from the manifest, then renders cumulative PNG states and a candidate editable PPTX with narration notes and sources. It uses the manifest's 1280×720 default canvas and exports at the requested output scale. It deliberately rejects an existing render directory.

Inspect all slides and meaningful states, complete the host's presentation validation/finalization procedure and use that final deck for verification. Candidate export is not an approved final deck. Keep validation receipts and outputs distinct for each revision. Do not modify system skills or bundled runtime code.

The baseline adapter is intentionally small. For a richer visual layout, use the host's supported authoring tools directly while preserving the render-state output contract. Do not lower instructional quality merely to fit the convenience adapter.

## Other compatible hosts

Use an available renderer that emits an editable PPTX with notes and the PNG states described in project-contract.md. Public alternatives may require a presentation authoring library plus a separate office/PDF renderer. Do not pretend that an unimplemented adapter has been tested. Confirm fonts, notes, layout fidelity and frame dimensions on a small sample before a full lesson. The Python timing/encoding/QA scripts are independent of the Work slide runtime.

If no renderer is available, state that specific blocker. Continue research/script preparation where useful, preserve progress and do not deliver a silent or incomplete prototype as the finished lesson.

## Image-callout coordinates

With image `contain`, calculate `scale=min(frame_width/source_width, frame_height/source_height)` and center offsets for unused width/height. Convert anatomical/diagram target coordinates through this transform. Position outlines in slide coordinates; the PNG exporter scales the whole slide. Check at full size. Avoid leaving outlines on labels or empty space when the target is elsewhere.

Timed removal in the baseline adapter is for outline annotations. Use `until_anchor` on the old outline. Do not rely on removing arbitrary image/text objects through this adapter without adding and testing that support.
