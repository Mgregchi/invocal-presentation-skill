# Continuous motion and data charts

Use `render_motion.py MANIFEST.json NEW_RENDER_DIRECTORY` after `pipeline.py prepare`. Feed its `render-states.json` to the normal encoder. This renderer samples at the manifest FPS, deduplicates identical holds, and disables the encoder's second dissolve for its frame states. Scene changes use `motion_transition_seconds` (default 0.24). Set it to zero for reduced motion.

## Current scope

Text slide entrances, focus outlines, short scene dissolves, positive vertical bars growing from zero, and a progressive line with a moving endpoint. This is an optional portable Pillow renderer, separate from the Work presentation renderer. It currently accepts text and outline elements plus charts, not image elements. Use the existing still adapter for image-heavy scenes until adapters are integrated. No 3D charts, negative bars, multiple series, camera moves, avatars or lip-sync are implemented here.

## Chart contract

Add `charts` to a scene. Each chart has `kind` (`bar` or `line`), `position` `[x,y,width,height]`, `unit`, `domain` `[min,max]`, `ticks`, `labels`, `values`, `anchors` and `source`. Anchors use the existing unique phrase/occurrence/word-index contract and resolve to global `reveals` during preparation. Choose chart geometry with room for axes, labels and source text. The renderer rejects unsafe chart positions, mismatched labels, non-finite/out-of-domain values, missing provenance, invalid ticks, and colliding line point cues. Bar domain must start at zero. Negative bars are unsupported.

Bar `duration` defaults to 0.65 seconds. A bar starts at its word cue, grows with bounded smooth easing, and shows the exact label after settling. For lines, the marker reaches each data point at its word cue, with linear travel between adjacent cues. Connecting segments are visual interpolation, not measured intermediate observations. Explain that when needed. Use explicit categorical step labels; this adapter does not infer numerical x-axis spacing from labels. Final chart values and scales stay fixed throughout.

Optional chart `focus` contains `anchor`, `until_anchor`, `value` and `label`. It draws an emphasized horizontal reference during that spoken interval. Text elements accept `motion: {kind: "slide", duration: 0.6, offset: [0,22], easing: "smooth"}`. Do not add motion unrelated to the concept being taught.

Configure `font_file` and `font_bold_file` for other hosts. Defaults are the installed Linux DejaVu Sans font files. Full-resolution PNG rendering uses more disk and CPU than still scenes.

## Editable presentation

The Work adapter exports the final data as native PowerPoint bar/line charts and records sources in notes and visible captions. Video motion does not become PowerPoint animation. Run the host presentation finalizer with required chart owner slides. For literal new data, explicitly enable its workbook snapshot packaging so the chart includes an editable embedded workbook. Preserve source workbook lineage when actual workbook inputs exist.

## Verification

Compare actual encoded frames to the scheduled source states at exact frame boundaries. Check before/on/after word cues, bar endpoints, fixed zero baseline, line endpoints, source/encoded audio correlation, subtitles, all scene frames and full decode. Visually inspect layout and data labels. Automated checks do not constitute a listening review or native PowerPoint application review.
