from __future__ import annotations
from typing import Dict, Any, Optional, List, Tuple

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.core import charts

# Optional 3D support (guarded import)
try:
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    _HAS_MPL_3D = True
except Exception:
    _HAS_MPL_3D = False


class FeasibleRegionWidget(QWidget):
    """
    Visualizes the feasible region for LP problems, didactically:

      • For 2 variables: 2D half-spaces, light-filled feasible set,
        constraint guide lines, and the optimal solution as a dot + label.
      • For 3 variables: a light 3D feasible-point cloud sampled on a coarse grid,
        plus the optimal solution point.
      • For other dimensions (or missing matplotlib): shows a friendly placeholder.

    Expected context via set_context(ctx):
      ctx = {
        "names": [x1_name, x2_name, ...],
        "coefs": [...],                 # objective coefficients (optional, used for arrows)
        "offset": float,                # objective offset (unused here, but harmless)
        "bounds": [(lb0, ub0), ...],
        "constraints": [([a1,a2,...], rel_str, rhs), ...],  # rel_str: "<=", "=", ">="
        "sense": "max" | "min"          # optional, default "max" (used for direction arrows in 2D)
      }

    Expected solution via set_solution(result):
      result = {"values": {name: value, ...}}  # or legacy "x" map
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._ctx: Dict[str, Any] = {}
        self._result: Dict[str, Any] = {}

        # ---- UI skeleton ----------------------------------------------------
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self._title = QLabel(S.t("lp.sol.feasible.title"))
        self._title.setStyleSheet("font-weight:700;")
        root.addWidget(self._title)

        # Placeholder by default; replaced by a Matplotlib canvas if available
        self._placeholder = QLabel(S.t("lp.sol.feasible.placeholder"))
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setMinimumHeight(220)
        self._placeholder.setObjectName("feasiblePlaceholder")
        root.addWidget(self._placeholder, 1)

        # ---- Matplotlib plumbing (guarded) ---------------------------------
        self._matplotlib_ok = False
        self._fig = None
        self._ax = None
        self._canvas = None

        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # type: ignore
            from matplotlib.figure import Figure  # type: ignore

            self._fig = Figure(figsize=(4.6, 2.7))
            # Start with a 2D axes; we may switch to 3D later if needed
            self._ax = self._fig.add_subplot(111)
            self._canvas = FigureCanvasQTAgg(self._fig)

            # Replace placeholder with the canvas
            root.replaceWidget(self._placeholder, self._canvas)
            self._placeholder.setParent(None)
            self._placeholder = None
            self._matplotlib_ok = True
        except Exception:
            # Keep the placeholder; no plotting available
            self._matplotlib_ok = False

        # Apply theme now to avoid first-paint flicker
        self.refresh_theme()

    # ----------------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------------
    def set_context(self, ctx: Dict[str, Any]) -> None:
        """Accept the problem context (names, bounds, constraints, etc.)."""
        self._ctx = ctx or {}
        self._repaint()

    def set_solution(self, result: Dict[str, Any]) -> None:
        """Accept the current solution (values map, possibly objective)."""
        self._result = result or {}
        self._repaint()

    def refresh_strings(self) -> None:
        """Update localized strings."""
        self._title.setText(S.t("lp.sol.feasible.title"))
        if not self._matplotlib_ok and self._placeholder:
            self._placeholder.setText(S.t("lp.sol.feasible.placeholder"))

    def refresh_theme(self) -> None:
        """Apply theme colors and repaint."""
        fg = "rgba(255,255,255,0.95)" if theme.is_dark() else "rgba(0,0,0,0.90)"
        self._title.setStyleSheet(f"font-weight:700; color:{fg};")
        self._repaint()

    # ----------------------------------------------------------------------
    # Internal rendering dispatcher
    # ----------------------------------------------------------------------

    def _current_axis_labels(self, want: int) -> List[str]:
        """Return labels to show on axes (human-facing, e.g. 'mele', 'pere').
        Priority: context.labels -> context.names -> values.keys() -> generic."""
        labels = list(self._ctx.get("labels", []) or [])
        if len(labels) >= want:
            return labels[:want]

        names = list(self._ctx.get("names", []) or [])
        if len(names) >= want:
            return names[:want]

        vals_map = (self._result or {}).get("values") or (self._result or {}).get("x") or {}
        if vals_map:
            vnames = list(vals_map.keys())
            if len(vnames) >= want:
                return vnames[:want]

        return [f"X{i+1}" for i in range(want)]

    def _current_names(self, want: int) -> List[str]:
        """Return internal variable identifiers (used to look up values).
        Priority: context.names -> values.keys() -> generic."""
        names = list(self._ctx.get("names", []) or [])
        if len(names) >= want:
            return names[:want]

        vals_map = (self._result or {}).get("values") or (self._result or {}).get("x") or {}
        if vals_map:
            vnames = list(vals_map.keys())
            if len(vnames) >= want:
                return vnames[:want]

        return [f"X{i+1}" for i in range(want)]
    
    def _repaint(self) -> None:
        """Render the widget according to the *actual* problem dimension."""
        if not self._matplotlib_ok or self._ax is None or self._fig is None:
            return

        # 1) Detect true dimension from context (preferred), else bounds, else values
        n = 0
        ctx_names = self._ctx.get("names", []) or []
        if ctx_names:
            n = len(ctx_names)
        if n == 0:
            bounds = self._ctx.get("bounds", []) or []
            if bounds:
                n = len(bounds)
        if n == 0:
            vals_map = (self._result or {}).get("values") or (self._result or {}).get("x") or {}
            if vals_map:
                n = len(vals_map)

        # Safety clamp (only 2D/3D supported didactically)
        if n < 2:
            n = 2
        elif n > 3:
            n = 4  # sentinel to go to the "not supported" message

        # 2) Resolve the labels for exactly n axes
        names: List[str] = self._current_names(2 if n == 2 else 3) if n in (2, 3) else []

        # 3) Clear and dispatch
        self._fig.clear()
        self._fig.patch.set_facecolor(charts.to_mpl(charts.current().window))
        if n == 2:
            self._ax = self._fig.add_subplot(111)  # 2D axes
            self._draw_2d()
        elif n == 3 and _HAS_MPL_3D:
            self._ax = self._fig.add_subplot(111, projection="3d")
            self._draw_3d()
        elif n == 3 and not _HAS_MPL_3D:
            ax = self._fig.add_subplot(111)
            ax.text(0.5, 0.5, "Matplotlib 3D backend not available.",
                    ha="center", va="center", transform=ax.transAxes,
                    color=charts.to_mpl(charts.current().text_muted))
            charts.style_axes(self._fig, ax, grid=False)
        else:
            ax = self._fig.add_subplot(111)
            ax.text(0.5, 0.5, S.t("lp.sol.feasible.only2d"),
                    ha="center", va="center", transform=ax.transAxes,
                    color=charts.to_mpl(charts.current().text_muted))
            charts.style_axes(self._fig, ax, grid=False)

        self._fig.tight_layout()
        if self._canvas is not None:
            self._canvas.draw()

    # ----------------------------------------------------------------------
    # 2D Rendering
    # ----------------------------------------------------------------------
    def _draw_2d(self) -> None:
        """Draw 2D feasible region, constraints, and the optimal point."""
        import numpy as np

        ax = self._ax
        t = charts.current()
        names:  List[str] = self._current_names(2)        # for value lookup
        labels: List[str] = self._current_axis_labels(2)  # for axis labels
        cons: List[Tuple[List[Optional[float]], str, Optional[float]]] = self._ctx.get("constraints", [])
        bounds: List[Tuple[Optional[float], Optional[float]]] = self._ctx.get("bounds", [(0.0, None), (0.0, None)])

        def _num(x, default=None):
            try:
                return float(x)
            except Exception:
                return default

        # Determine a reasonable plotting window from bounds/constraints
        lb0, ub0 = bounds[0] if len(bounds) > 0 else (0.0, None)
        lb1, ub1 = bounds[1] if len(bounds) > 1 else (0.0, None)
        rhs_max = max([_num(c[2], 1.0) or 1.0 for c in cons] + [1.0])

        x0_min = _num(lb0, 0.0)
        x1_min = _num(lb1, 0.0)
        x0_max = _num(ub0, rhs_max * 1.5 if ub0 is None else ub0 or rhs_max * 1.5)
        x1_max = _num(ub1, rhs_max * 1.5 if ub1 is None else ub1 or rhs_max * 1.5)

        x0 = np.linspace(x0_min, x0_max, 240)
        x1 = np.linspace(x1_min, x1_max, 240)
        X0, X1 = np.meshgrid(x0, x1)

        # Build feasibility mask of all half-spaces + bounds
        mask = np.ones_like(X0, dtype=bool)
        for a, rel, rhs in cons:
            a0 = _num(a[0], 0.0) if a and len(a) > 0 else 0.0
            a1 = _num(a[1], 0.0) if a and len(a) > 1 else 0.0
            rhsf = _num(rhs, 0.0)
            expr = a0 * X0 + a1 * X1
            if rel == "<=":
                mask &= (expr <= rhsf + 1e-9)
            elif rel == ">=":
                mask &= (expr >= rhsf - 1e-9)
            else:  # "="
                mask &= (np.abs(expr - rhsf) <= 1e-9)

        # Variable bounds
        mask &= (X0 >= _num(lb0, -np.inf)) & (X1 >= _num(lb1, -np.inf))
        if ub0 is not None:
            mask &= (X0 <= _num(ub0, np.inf))
        if ub1 is not None:
            mask &= (X1 <= _num(ub1, np.inf))

        # Feasible region (light fill)
        ax.contourf(X0, X1, mask.astype(int), levels=[0.5, 1.5],
                    colors=[charts.to_mpl(t.accent)], alpha=0.22)

        # Constraint guide lines
        for a, rel, rhs in cons:
            a0 = _num(a[0], 0.0) if a and len(a) > 0 else 0.0
            a1 = _num(a[1], 0.0) if a and len(a) > 1 else 0.0
            rhsf = _num(rhs, 0.0)
            if abs(a1) > 1e-12:
                y = (rhsf - a0 * x0) / a1
                ax.plot(x0, y, linewidth=1.2, color=charts.to_mpl(t.cyan))
            elif abs(a0) > 1e-12:
                x = rhsf / a0
                ax.axvline(x, linewidth=1.2, color=charts.to_mpl(t.cyan))

        # Optimal point (if present)
        values = (self._result or {}).get("values") or (self._result or {}).get("x") or {}
        p0 = _num(values.get(names[0]), None)
        p1 = _num(values.get(names[1]), None)
        if p0 is not None and p1 is not None:
            ax.scatter([p0], [p1], s=48, color=charts.to_mpl(t.accent), zorder=5,
                       edgecolors=charts.to_mpl(t.on_accent), linewidths=1.2)
            ax.annotate(f"({p0:.3g}, {p1:.3g})",
                        xy=(p0, p1), xytext=(6, 6), textcoords="offset points",
                        color=charts.to_mpl(t.text))

        # Axes styling
        ax.set_xlabel(labels[0])
        ax.set_ylabel(labels[1])
        ax.set_title(S.t("lp.sol.feasible.subtitle"))
        ax.set_xlim([x0_min, x0_max])
        ax.set_ylim([x1_min, x1_max])
        for spine in ax.spines.values():
            spine.set_linewidth(1.0)
        charts.style_axes(self._fig, ax)

    # ----------------------------------------------------------------------
    # 3D Rendering
    # ----------------------------------------------------------------------
    def _draw_3d(self) -> None:
        """Draw translucent constraint planes and mark the optimal point (didactic 3D view)."""
        import numpy as np

        ax = self._ax
        t = charts.current()
        names:  List[str] = self._current_names(3)         # for value lookup
        labels: List[str] = self._current_axis_labels(3)   # for axis labels
        cons: List[Tuple[List[Optional[float]], str, Optional[float]]] = self._ctx.get("constraints", [])
        bounds: List[Tuple[Optional[float], Optional[float]]] = self._ctx.get(
            "bounds", [(0.0, None), (0.0, None), (0.0, None)]
        )

        def _num(x, default=None):
            try:
                return float(x)
            except Exception:
                return default

        # --- Build a tight plotting box from bounds + constraints ----------------
        # Start from (lb, ub) if provided (default lb=0, ub=None)
        lbs = [bounds[i][0] if i < len(bounds) else 0.0 for i in range(3)]
        ubs = [bounds[i][1] if i < len(bounds) else None for i in range(3)]

        # If ub is None for an axis, try to infer a finite cap from constraints:
        # For each axis i, consider all constraints a0*x + a1*y + a2*z <= rhs with a_i > 0.
        # Setting the other variables = 0 gives x_i <= rhs / a_i.
        # Take the minimum of those as an upper bound candidate.
        for i in range(3):
            if ubs[i] is None:
                candidates = []
                for a, rel, rhs in cons:
                    if rel not in ("<=", "="):    # ">=" does not bound from above
                        continue
                    ai = _num(a[i] if (a and len(a) > i) else 0.0, 0.0)
                    rhsf = _num(rhs, None)
                    if rhsf is None:
                        continue
                    if ai > 1e-12:
                        candidates.append(rhsf / ai)
                if candidates:
                    ubs[i] = min(candidates)

        # Fallback if still None: use a mild heuristic from RHS scale
        rhs_max = max([_num(c[2], 1.0) or 1.0 for c in cons] + [1.0])
        mins = [_num(lbs[i], 0.0) for i in range(3)]
        maxs = [ _num(ubs[i], rhs_max * 0.05) for i in range(3) ]  # much smaller than 1.2*RHS

        # Ensure strictly increasing limits
        for i in range(3):
            if maxs[i] <= mins[i]:
                maxs[i] = mins[i] + max(1.0, rhs_max * 0.01)

        # Coarse mesh inside the box
        grid_n = 24
        X = np.linspace(mins[0], maxs[0], grid_n)
        Y = np.linspace(mins[1], maxs[1], grid_n)
        Z = np.linspace(mins[2], maxs[2], grid_n)

        def _clip_to_box(A, B, C):
            """NaN-out-of-range points so the surface is clipped to box."""
            A = A.copy(); B = B.copy(); C = C.copy()
            mask = (
                (A < mins[0]) | (A > maxs[0]) |
                (B < mins[1]) | (B > maxs[1]) |
                (C < mins[2]) | (C > maxs[2])
            )
            A[mask] = np.nan; B[mask] = np.nan; C[mask] = np.nan
            return A, B, C

        # --- Draw a translucent plane for each constraint ------------------------
        for a, rel, rhs in cons:
            a0 = _num(a[0], 0.0) if a and len(a) > 0 else 0.0
            a1 = _num(a[1], 0.0) if a and len(a) > 1 else 0.0
            a2 = _num(a[2], 0.0) if a and len(a) > 2 else 0.0
            rhsf = _num(rhs, 0.0)

            # skip degenerate
            if abs(a0) < 1e-12 and abs(a1) < 1e-12 and abs(a2) < 1e-12:
                continue

            try:
                if abs(a2) > 1e-12:
                    XX, YY = np.meshgrid(X, Y, indexing="xy")
                    ZZ = (rhsf - a0 * XX - a1 * YY) / a2
                    XX, YY, ZZ = _clip_to_box(XX, YY, ZZ)
                    ax.plot_surface(XX, YY, ZZ, rstride=1, cstride=1,
                                    linewidth=0.3, color=charts.to_mpl(t.accent),
                                    edgecolor=charts.to_mpl(t.border_strong),
                                    alpha=0.28, antialiased=True)
                elif abs(a1) > 1e-12:
                    XX, ZZ = np.meshgrid(X, Z, indexing="xy")
                    YY = (rhsf - a0 * XX - a2 * ZZ) / a1
                    XX, YY, ZZ = _clip_to_box(XX, YY, ZZ)
                    ax.plot_surface(XX, YY, ZZ, rstride=1, cstride=1,
                                    linewidth=0.3, color=charts.to_mpl(t.accent),
                                    edgecolor=charts.to_mpl(t.border_strong),
                                    alpha=0.28, antialiased=True)
                else:
                    YY, ZZ = np.meshgrid(Y, Z, indexing="xy")
                    XX = (rhsf - a1 * YY - a2 * ZZ) / a0
                    XX, YY, ZZ = _clip_to_box(XX, YY, ZZ)
                    ax.plot_surface(XX, YY, ZZ, rstride=1, cstride=1,
                                    linewidth=0.3, color=charts.to_mpl(t.accent),
                                    edgecolor=charts.to_mpl(t.border_strong),
                                    alpha=0.28, antialiased=True)
            except Exception:
                # skip numerical issues
                pass

        # --- Optimal point -------------------------------------------------------
        values = (self._result or {}).get("values") or (self._result or {}).get("x") or {}
        def _v(i): return _num(values.get(names[i]), None)
        pt = (_v(0), _v(1), _v(2))
        if all(v is not None for v in pt):
            ax.scatter([pt[0]], [pt[1]], [pt[2]], s=55, color=charts.to_mpl(t.accent))
            ax.text(pt[0], pt[1], pt[2], f"({pt[0]:.3g}, {pt[1]:.3g}, {pt[2]:.3g})",
                    color=charts.to_mpl(t.text))

        # Axes labels/limits: now tight around the interesting range
        ax.set_xlabel(labels[0]); ax.set_ylabel(labels[1]); ax.set_zlabel(labels[2])
        ax.set_xlim(mins[0], maxs[0]); ax.set_ylim(mins[1], maxs[1]); ax.set_zlim(mins[2], maxs[2])
        try:
            ax.ticklabel_format(style="plain", axis="x")
            ax.ticklabel_format(style="plain", axis="y")
            ax.zaxis.set_major_formatter('{x:.0f}')
        except Exception:
            pass
        ax.set_title(S.t("lp.sol.feasible.subtitle"))
        charts.style_axes(self._fig, ax)