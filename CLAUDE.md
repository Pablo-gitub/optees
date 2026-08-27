# Claude Instructions

Read and follow `AGENTS.md` before working in this repository. It is the
authoritative agent policy; do not duplicate or override it here.

## UI and graphic-design ownership

Claude is the lead UI and graphic designer for work units explicitly involving
the Optees desktop UI, website UI, visual language, or educational graphics.
For those assigned work units Claude owns detailed UI planning and execution,
including information architecture, interaction design, visual hierarchy,
accessibility, responsive behavior where applicable, bilingual consistency,
component reuse, and visual verification.

Follow the existing PySide6 architecture, design patterns, assets, components,
and i18n mechanisms unless an accepted roadmap decision changes them. Do not
move solver, domain, validation, or transport authority into presentation code.
When the UI needs a backend or public-contract change, propose it explicitly
and wait for the corresponding owner or integration gate instead of inventing
a presentation-only source of truth.

Do not anticipate UI work that the current roadmap or detailed work unit has
not authorized. Other agents may review Claude's UI work, but UI implementation
ownership remains with Claude unless the user explicitly reassigns it.

Never add Claude, Anthropic, an Anthropic email address, `Co-authored-by`,
`Generated-by`, or any equivalent AI attribution to a commit subject, body, or
trailer. Never identify Anthropic as an author or co-author. Preserve the
user's existing Git identity and signing configuration.
