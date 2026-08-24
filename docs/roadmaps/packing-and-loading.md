# Packing & Loading Feature Roadmap

## Document Status

- **State:** in progress
- **Shipped baseline:** version 1 single-container orthogonal 3D packing,
  validation, desktop workflow, public service capability, and result artifacts
- **Remaining scope:** support-aware and multi-container workflows, interactive
  refinement, benchmark depth, and the later capacity-allocation workflow
- **Safety boundary:** output is not a physical load-safety certification

This document defines the horizontal expansion that introduces geometric
packing and container loading to Optees. The feature remains educational: each
workflow must expose its mathematical formulation, solver status, limitations,
and structured JSON contract. The same workflows may also support operational
experiments on small instances, but they are not a physical load-safety
certification system.

## Product Placement

Packing & Loading is exposed as a dedicated application card, similarly to
Knapsack. It is not hidden inside the generic MILP editor because geometric
models require dedicated formulation and solution views. Every exact workflow
must nevertheless explain that its first implementation is a mixed-integer
linear formulation and link the business concepts to the generated variables,
constraints, and objective.

The card name is **Packing & Loading**. The narrower name avoids suggesting
that Optees already covers the entire logistics domain, such as routing,
inventory, scheduling, or supply-chain planning.

The eventual user-facing order is:

1. Multi-container Capacity Allocation;
2. Single-container 3D Packing;
3. Multi-container 3D Packing;
4. Packing with Supports and Dunnage, with single-container and multi-container
   modes when both are implemented.

The implementation order is intentionally different because the first target
is the more useful geometric workflow:

1. Single-container 3D Packing;
2. support-aware single-container refinement;
3. Multi-container 3D Packing;
4. Packing with Supports and Dunnage;
5. Interactive refinement;
6. industrial constraints and heuristic solvers;
7. Multi-container Capacity Allocation.

## Mathematical Scope

### Initial Geometry

The first release supports rectangular cuboids inside rectangular containers.
All placements are orthogonal: object edges remain parallel to container axes.
Diagonal placements, cylinders, irregular shapes, and compound shapes are out
of scope.

An item starts with dimensions `(length, width, height)`. The initial model may
use all six orthogonal permutations of those dimensions. They represent the
three possible support faces and, for each support face, the two possible
90-degree rotations in its plane. The item never receives a diagonal placement.

Rotation permissions are configured per item. The UI provides clear presets:

- **Fixed:** canonical orientation only;
- **Keep upright:** preserve the original vertical dimension and allow a
  90-degree rotation around the container's vertical axis;
- **Single axis:** allow multiples of 90 degrees around only the selected X, Y,
  or Z axis; selecting the vertical axis is the geometric equivalent of the
  keep-upright preset;
- **Any orthogonal:** allow every orthogonal orientation;
- **Custom:** explicitly select the permitted resulting orientations.

The domain stores the resulting allowed-orientation set rather than relying on
ambiguous UI flags. When more than one axis is enabled, the generator computes
the orientations reachable by composing the permitted 90-degree rotations.

Before creating solver variables, Optees normalizes the orientation set by its
resulting `(length, width, height)` tuple. A cuboid with two equal dimensions
therefore has fewer than six distinct geometric orientations, and a cube has
exactly one. This avoids equivalent binaries and duplicate branches without
changing the feasible geometric set.

This dimensional deduplication assumes that equal faces have no distinct
semantic properties. A future model with labelled faces, mandatory labels-up,
fragile sides, or face-specific support rules must preserve physically distinct
orientations even when their dimension tuples are equal.

### Core Decisions

For each item, the exact model decides:

- whether the item is loaded;
- its container, when more than one is available;
- its X, Y, and Z coordinates;
- one allowed orthogonal orientation;
- pairwise spatial separation from every other loaded item in that container.

The initial model validates geometric containment and non-overlap. It does not
claim to model deformation, pressure, dynamic transport stability, or material
strength.

### Selection And Recovery

Two requirements must remain mathematically distinct:

- **Optional selection:** maximize the total value or priority loaded into the
  available container set. Unloaded items are a normal part of the solution.
- **All items required:** first test whether every item can be loaded. Failure
  means the requested model is infeasible.

When an all-items-required model is infeasible, Optees may additionally solve
an explicitly labelled **maximum feasible recovery plan**. It must never report
that partial plan as a solution to the original requirement. The result view
shows both facts: the complete request is infeasible, and the recovery plan is
the best partial load found under the selected value or priority objective.

### Additional Capacities

Geometry is separate from user-defined scalar resources. Users may add named
capacity dimensions such as weight, pallet slots, or another measurable limit.
For each resource `r`, every container provides a capacity and every item
provides a consumption:

```text
sum(item_consumption[i, r] * assigned[i, c]) <= container_capacity[c, r]
```

These fields are called **additional capacities**, not arbitrary variables.
Categorical compatibility, destination, fragility, and stacking rules require
dedicated typed constraints rather than generic numeric columns.

Physical items remain indivisible in geometric packing. Fractional or bulk
quantities belong to Capacity Allocation because loading a fraction of a box
does not define a valid cuboid placement. Repeated identical boxes are modelled
as an integer quantity of indivisible units.

## Phase 1 - Single-Container 3D Packing

### Domain And JSON Contract

- [x] Define units, finite-value validation, numerical tolerances, and stable
  identifiers for containers and items.
- [x] Define `PackingItem`, rectangular `Container`, allowed orientations,
  value/priority, quantity, and additional resource consumption.
- [x] Add a deterministic orientation generator and dimension-based
  normalization step before constructing the solver model.
- [x] Define a versioned JSON schema and importer/exporter.
- [x] Reject zero or negative dimensions, invalid quantities, duplicate IDs,
  unsupported orientation combinations, and non-finite numbers.
- [x] Preserve input descriptions and names in every solution record.

### Exact MILP Formulation

- [x] Add load-selection binaries, continuous coordinates, orientation
  binaries, and oriented dimensions.
- [x] Add containment constraints for every loaded item.
- [x] Add pairwise disjunctive non-overlap constraints with documented Big-M
  values derived from container dimensions rather than arbitrary constants.
- [x] Add optional named scalar-capacity constraints, starting with weight.
- [x] Support optional-selection and all-items-required modes.
- [x] Support the separately labelled maximum-feasible recovery solve.
- [x] Preserve `Optimal`, `Feasible`, `Infeasible`, `NotSolved`, time-limit,
  objective bound, and MIP-gap semantics.
- [x] Apply deterministic downward compaction as an explicit optional
  post-processing criterion, without describing compactness as physical
  stability.

### Formulation View

- [x] Container dimensions and optional scalar capacities.
- [x] Item table with name, dimensions, quantity, value/priority, and a clear
  rotation-policy control.
- [x] Show only unique resulting orientations in the advanced/custom editor,
  including one orientation for a cube.
- [x] Controls for adding named scalar capacities to both container and item
  tables.
- [x] Selection policy and objective controls with educational explanations.
- [x] Solver time limit and MIP-gap controls.
- [x] JSON import and matching information dialog.
- [x] Localized example and problem-description pages.

### Solution View

- [x] Clearly separate requested-model status from any recovery-plan status.
- [x] Report loaded and excluded items, objective value, used/free volume,
  scalar-capacity usage, coordinates, and orientation.
- [x] Show proof status, elapsed time, objective bound, and MIP gap.
- [x] Render the container as a bounded 3D scene with a stable color per item.
- [x] Provide legend, item selection, reset-view, and visibility controls.
- [x] State that the placement is geometrically feasible under the model but
  is not a physical or transport-safety certification.
- [x] Provide optional deterministic simple gravity: lower each box at fixed
  X/Y and orientation until it reaches the floor or the highest overlapping
  footprint below it.
- [x] Explicitly delimit simple gravity from support-area, load-bearing,
  balance, and stability constraints. Support-aware refinement starts in Phase
  2; physical and industrial constraints remain Phase 6 scope.

### Verification

- [x] Analytic tests for one item, exact fits, excluded high-volume items,
  rotations, weight limits, and impossible all-required requests.
- [x] Orientation tests for a cuboid with three distinct dimensions, two equal
  dimensions, and three equal dimensions; verify deterministic deduplication.
- [x] Rotation-policy tests for fixed, single-axis, keep-upright, unrestricted,
  and custom orientation sets.
- [x] Pairwise tests for overlap prevention on each axis.
- [x] JSON round-trip and invalid-input tests.
- [x] Use-case tests for every solver status and recovery-plan semantics.
- [x] Presentation tests for formulation, result tables, and non-empty 3D
  rendering.
- [x] Integrate the public OR-Library Bischoff/Ratcliff `thpack1` source,
  document its provenance and checksum, and run an explicitly labelled derived
  two-box CI subset with an analytic expected objective.

## Phase 2 - Support-Aware Single-Container Refinement

This phase improves the visual and geometric quality of the existing optimal
load before adding container assignment. It does not claim transport safety or
full static stability.

- [ ] Define bottom-face support area separately from irrelevant side contact.
- [ ] Treat floor contact as full support and item-on-item support as the union
  of intersections between an item's bottom face and the top faces in direct
  vertical contact below it.
- [ ] Report both absolute supported area and normalized support ratio per item:
  `support_ratio = supported_bottom_area / bottom_face_area`.
- [ ] Preserve the primary loaded-value optimum and every hard feasibility
  constraint while refining a placement.
- [ ] Keep simple gravity as an inexpensive standalone mode and candidate
  generator, never as an irreversible constraint that narrows the feasible
  placement space before support refinement.
- [ ] Add a deterministic support-aware improvement heuristic that may change
  X/Y coordinates and allowed orientations, then reapplies downward compaction
  after each candidate move.
- [ ] Compare the original solver placement, its simple-gravity projection,
  and support-aware candidates; retain the best measured candidate without
  reducing the primary loaded value.
- [ ] Start with total normalized support as the documented secondary quality
  measure. Record minimum per-item support ratio as a diagnostic so that a high
  total cannot hide one poorly supported item.
- [ ] Keep side-face contact out of the support objective. A future compactness
  metric may measure lateral contact separately, but it must not be described
  as weight support.
- [ ] Use an explicit seed and reproducible tie-breakers.
- [ ] Report supported base area and support ratio per loaded item without
  presenting either metric as a safety certification.
- [ ] Reject any candidate move that violates containment, allowed
  orientation, scalar capacities, or pairwise non-overlap.
- [ ] Add analytic tests for floor support, partial support, unchanged primary
  objective, deterministic output, gravity not restricting candidate moves,
  and geometrically blocked placements.
- [ ] Simplify rotation presets so common axis combinations are directly
  selectable while the domain continues to store explicit orientation sets.

An exact secondary solve that maximizes support lexicographically is deferred
to Phase 6. The Phase 2 heuristic must therefore be labelled as placement
improvement, not as a proof of maximum support.

## Phase 3 - Multi-Container 3D Packing

### Fixed Container Set

- [ ] Assign every loaded item to at most one container.
- [ ] Support identical and heterogeneous container dimensions.
- [ ] Support different scalar capacities per container.
- [ ] Maximize loaded value/priority across the fixed container set.
- [ ] Keep all-required feasibility and recovery-plan results distinct.

### Container Minimization And Cost

- [ ] Support an available container type catalogue.
- [ ] Support minimum and maximum quantities per type.
- [ ] Minimize used-container count when all items are required.
- [ ] Minimize total container cost as a separate objective.
- [ ] Define deterministic tie-breakers, such as cost first and count second,
  rather than hiding several goals inside undocumented weighted sums.

### Multi-Container Solution UI

- [ ] Show one 3D container at a time with previous/next controls and a
  container selector suitable for larger fleets.
- [ ] Display selected-container utilization and overall fleet utilization.
- [ ] Keep item colors stable while switching between containers.
- [ ] Show excluded items and their reason when a useful diagnostic is known.
- [ ] Provide a fleet summary table with value, volume, weight, cost, and proof
  status.

## Phase 4 - Packing With Supports And Dunnage

This is a separate packing variant introduced only after the geometric
multi-container model. It represents physical support elements explicitly; it
does not reinterpret unsupported cargo contact as if support material existed.

The first scope uses a finite catalogue of rectangular support elements with
known geometry. Arbitrarily shaped or continuously resized supports are out of
scope until a dedicated mathematical model and validator exist.

### Support Model

- [ ] Define typed support elements such as spacers, interlayers, pallets, and
  full-layer separators separately from cargo items.
- [ ] Give every support type fixed length, width, height, weight, optional
  cost, available quantity, and permitted orientations.
- [ ] Make support elements consume geometric space and every configured scalar
  capacity exactly like physical objects, while excluding them from loaded
  cargo value.
- [ ] Define whether a support may rest on the floor, cargo, another support,
  or only on explicitly permitted surfaces.
- [ ] Require cargo using a support to satisfy direct-contact and support-area
  rules against the support's top face.
- [ ] Keep full-container or full-layer interlayers as a simpler explicit
  subtype rather than silently deriving a variable support shape.
- [ ] Preserve the primary loaded-cargo value, then minimize support count,
  cost, or occupied volume using an explicit lexicographic order selected by
  the workflow.
- [ ] Report support placement and consumption separately from cargo placement.
- [ ] State that modelled geometric support is not a certification of material
  strength, compression resistance, or transport stability.

### Single And Multiple Containers

- [ ] Implement and validate the support model in one container first.
- [ ] Extend the same support catalogue and constraints to heterogeneous
  multi-container instances without changing single-container semantics.
- [ ] Support per-container availability or cost only through explicit fields.
- [ ] Preserve stable support and cargo identifiers when switching container
  views or exporting structured results.

### UI, Contracts, And Verification

- [ ] Add a dedicated variant selector rather than overloading the ordinary 3D
  packing form with hidden support behavior.
- [ ] Define a versioned JSON contract for support catalogues, availability,
  placement rules, and secondary objectives.
- [ ] Render supports with a visual category distinct from cargo while keeping
  individual elements selectable in the 3D scene and tables.
- [ ] Explain how support height reduces usable space and how support weight or
  cost affects the selected plan.
- [ ] Add analytic tests for interlayer height, capacity consumption, support
  availability, objective preservation, cost/count tie-breakers, and infeasible
  support requirements.
- [ ] Add single-container cases before shared multi-container benchmark cases.

## Phase 5 - Interactive Refinement

Interactive refinement is a human-in-the-loop re-optimization workflow, not a
claim that Optees inferred physical properties that were absent from the data.

- [ ] Select an item from the 3D scene or result table.
- [ ] Add soft preferences: prefer high, prefer low, prefer another container.
- [ ] Add hard rules: no item above, fixed container, fixed orientation, and
  locked placement where mathematically supported.
- [ ] Display every added preference and constraint before re-solving.
- [ ] Require confirmation before replacing the current formulation or result.
- [ ] Keep previous solutions available for comparison.
- [ ] Implement **Propose another solution** as a constrained re-solve after
  user feedback. It does not initially mean enumerating arbitrary coordinate
  variants of the same packing.
- [ ] Explain which requirements are hard and which are penalty-based.

## Phase 6 - Industrial Constraints And Heuristics

- [ ] Centre-of-mass projection diagnostics for each item and container.
- [ ] Configurable minimum support-ratio constraints with explicit modelling
  assumptions.
- [ ] Stackability, fragility, incompatibility, forbidden orientations, and
  load-bearing limits.
- [ ] Unloading order and destination grouping.
- [ ] Weight distribution and container-balance objectives.
- [ ] Optional exact lexicographic re-solve that preserves the proven primary
  loaded-value optimum before optimizing support or balance.
- [ ] Optional priority heuristic using available weight, volume, and density
  only as an explicitly labelled proxy when structural data is unavailable.
- [ ] Fast constructive heuristic for larger instances.
- [ ] Improvement heuristic with seed, time budget, incumbent trace, and
  reproducibility metadata.
- [ ] Exact-versus-heuristic comparison on small shared instances.

## Phase 7 - Multi-Container Capacity Allocation

This workflow deliberately ignores physical geometry. A scalar volume limit is
therefore a capacity approximation, not proof that the objects physically fit.

- [ ] Identical or heterogeneous containers.
- [ ] Any number of named scalar capacities.
- [ ] Indivisible item assignment and optional bulk/fractional quantities.
- [ ] Fixed-fleet value maximization.
- [ ] All-items-required feasibility with a separately labelled recovery plan.
- [ ] Container-count and container-cost minimization.
- [ ] Assignment table and per-capacity utilization charts.
- [ ] Educational comparison with Multiple Knapsack, multi-dimensional Bin
  Packing, Generalized Assignment, and geometric packing.

## Performance And Responsiveness Contract

The number of non-overlap decisions grows with item pairs and, for multiple
containers, with assignment alternatives. Item count alone is not a reliable
runtime estimate.

- [x] Run every solve outside the GUI thread.
- [x] Provide elapsed time, a solver time limit, and cooperative cancellation
  through the OR-Tools interruption API.
- [ ] Provide live incumbent progress when a future backend exposes a stable
  callback contract.
- [x] Add pre-solve complexity warnings based on generated variables,
  constraints, item pairs, orientation alternatives, and containers.
- [ ] Calibrate warning tiers empirically on the development M1 Max and record
  the model size, solver, machine, and observed time.
- [x] Show a non-blocking runtime notice after approximately one minute.
- [x] Strengthen the notice after approximately two minutes while still
  allowing the user to continue or cancel.
- [x] Never present those thresholds as portable runtime predictions: faster
  and slower machines, solver versions, and instance geometry can change the
  result substantially.

## Completion Standard

A phase is complete only when its domain model, exact mathematical contract,
JSON schema, solver adapter, localized formulation and solution views,
educational documentation, deterministic tests, and benchmark evidence are
consistent. A visually plausible arrangement is not sufficient evidence of
geometric feasibility, and a feasible incumbent is never presented as a proven
optimum.
