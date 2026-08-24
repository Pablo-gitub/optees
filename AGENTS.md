# Repository Agent Instructions

These instructions apply to every automated coding agent working in this
repository. Keep this file concise; detailed and frequently changing project
information belongs in the canonical documents linked below.

## Sources of truth

Read the relevant source before making changes:

- Architecture and dependency boundaries: `docs/architecture/overview.md`
- Test strategy, markers, and commands: `docs/guides/testing.md`
- Versioning, packaging, and release procedure: `docs/guides/releasing.md`
- Current implementation priorities: `docs/roadmaps/project.md` and any
  feature-specific roadmap referenced from it

Do not copy large sections of these documents into agent instruction files.
When implementation changes behavior, contracts, commands, architecture,
supported platforms, or roadmap status, update the corresponding documentation
in the same work unit. Documentation must describe shipped behavior honestly;
planned functionality must remain clearly marked as planned.

## Engineering workflow

- Inspect the surrounding code and existing patterns before designing a change.
- Preserve the dependency direction documented in `docs/architecture/overview.md`.
  Presentation and transport code must not become the owner of domain or solver
  logic. Register public solver capabilities through the existing composition
  and versioned-contract mechanisms.
- Keep changes scoped. Do not revert, rewrite, or include unrelated user work.
- Prefer existing helpers, codecs, adapters, UI components, and i18n mechanisms
  over parallel implementations.
- Keep user-visible English and Italian resources synchronized. Do not hardcode
  translatable UI text.
- Add or update focused tests for changed behavior. Run targeted tests while
  iterating, then choose broader gates according to blast radius and
  `docs/guides/testing.md`. Do not claim that tests passed when dependencies, GUI
  support, sockets, datasets, or platform access prevented execution.
- Treat solver correctness, public JSON contracts, independent validation,
  update behavior, and packaging as high-risk surfaces requiring explicit
  regression coverage.

## Local commits

- Agents may create local commits autonomously when a coherent, reviewed, and
  appropriately tested work unit is complete.
- Keep commits atomic and use concise imperative messages describing the
  repository change.
- Before committing, inspect the staged diff and exclude unrelated files,
  generated artifacts, secrets, credentials, and local configuration.
- Do not add AI attribution such as `Co-authored-by`, `Generated-by`, agent
  names, vendor names, or similar trailers to commit messages.
- Use the repository's existing Git identity and signing configuration. Do not
  modify author information, signing keys, hooks, or credential settings.

## Remote publication and releases

- Never push `main` or publish commits, branches, or tags to a remote repository.
- Never create a GitHub release or trigger a release/deployment workflow.
- Do not change the configured remote or bypass SSH by switching to HTTPS.
- When the local state is ready to publish, recommend that explicitly and give
  the user the exact ordered `git push`, tag, and tag-push commands to run in
  their own terminal.
- Before recommending a release, verify the working tree, required tests,
  internal version, intended tag, release notes/documentation, and the
  invariants in `docs/guides/releasing.md`.
- Treat application and website releases as separate publication flows and
  provide commands only for the flow that is actually ready.

## Completion standard

A task is complete only when implementation, focused verification, relevant
documentation, and local Git state agree. Report what changed, which checks
ran, any checks that could not run, local commits created, and the next manual
or publication step when one exists.
