from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from datetime import datetime

from optees.application.contracts.forecasting import (
    ForecastingAdapterOutput,
    ForecastingEvaluationOutput,
)
from optees.application.ports.forecasting_solver_port import ForecastingSolverPort
from optees.domain.entities.forecasting import (
    ForecastDiagnostic,
    ForecastEvaluationFold,
    ForecastMetricSet,
    ForecastObservation,
    ForecastPoint,
    ForecastSegment,
    ForecastingSolution,
)
from optees.domain.models.forecasting import ForecastingModel
from optees.domain.value_objects.forecasting import (
    EvaluationStrategy,
    ForecastEvaluationStatus,
    ForecastingMethod,
    ForecastingStatus,
)

CancelCheck = Callable[[], bool]


class ForecastTimeSeriesUseCase:
    """Coordinates leakage-free evaluation and the final full-history forecast."""

    def __init__(
        self,
        solvers: Mapping[ForecastingMethod, ForecastingSolverPort],
    ) -> None:
        self._solvers = dict(solvers)

    def fit_training_window(
        self,
        model: ForecastingModel,
        training_observations: tuple[ForecastObservation, ...],
        prediction_timestamps: tuple[datetime, ...],
    ) -> ForecastingAdapterOutput:
        """Fit one explicit historical prefix and predict its immediate successors."""
        return self._solver_for(model.method).fit_and_predict(
            model,
            training_observations,
            prediction_timestamps,
        )

    def evaluate(
        self,
        model: ForecastingModel,
        *,
        cancel_requested: CancelCheck | None = None,
    ) -> ForecastingEvaluationOutput:
        """Evaluate only on observations strictly later than each training origin."""
        if model.evaluation.strategy is EvaluationStrategy.NONE:
            return ForecastingEvaluationOutput(
                status=ForecastEvaluationStatus.NOT_REQUESTED
            )

        folds: list[ForecastEvaluationFold] = []
        diagnostics: list[ForecastDiagnostic] = []
        scales: list[float | None] = []
        incomplete = False

        for training_size, target_size in self._evaluation_windows(model):
            if cancel_requested is not None and cancel_requested():
                diagnostics.append(
                    ForecastDiagnostic(
                        code="forecast_evaluation_cancelled",
                        message="Chronological forecast evaluation was cancelled.",
                    )
                )
                incomplete = True
                break

            training = model.observations[:training_size]
            targets = model.observations[training_size : training_size + target_size]
            output = self.fit_training_window(
                model,
                training,
                tuple(target.timestamp for target in targets),
            )
            diagnostics.extend(output.diagnostics)
            if (
                output.status in {ForecastingStatus.FAILED, ForecastingStatus.CANCELLED}
                or len(output.predicted_values) != len(targets)
            ):
                incomplete = True
                diagnostics.append(
                    ForecastDiagnostic(
                        code="forecast_evaluation_fold_failed",
                        message="A chronological forecast evaluation fold was unavailable.",
                        severity="error",
                    )
                )
                continue

            points = tuple(
                ForecastPoint(
                    timestamp=target.timestamp,
                    predicted=prediction,
                    actual=target.value,
                    residual=target.value - prediction,
                    segment=ForecastSegment.HOLDOUT,
                )
                for target, prediction in zip(targets, output.predicted_values, strict=True)
            )
            scale = self._mase_scale(model, training)
            folds.append(
                ForecastEvaluationFold(
                    origin=training[-1].timestamp,
                    training_size=training_size,
                    points=points,
                    metrics=self._metrics(points, scales=(scale,) * len(points)),
                )
            )
            scales.extend((scale,) * len(points))
            if output.status is ForecastingStatus.PARTIAL:
                incomplete = True

        all_points = tuple(point for fold in folds for point in fold.points)
        if not folds:
            status = ForecastEvaluationStatus.FAILED
        elif incomplete:
            status = ForecastEvaluationStatus.PARTIAL
        else:
            status = ForecastEvaluationStatus.EVALUATED
        return ForecastingEvaluationOutput(
            status=status,
            folds=tuple(folds),
            metrics=self._metrics(all_points, scales=tuple(scales)),
            diagnostics=tuple(diagnostics),
        )

    def forecast_future(
        self,
        model: ForecastingModel,
    ) -> ForecastingAdapterOutput:
        """Fit all available history and forecast exactly the declared horizon."""
        return self.fit_training_window(
            model,
            model.observations,
            model.future_timestamps(),
        )

    def execute(
        self,
        model: ForecastingModel,
        *,
        cancel_requested: CancelCheck | None = None,
    ) -> ForecastingSolution:
        """Evaluate chronologically, then fit all history for the production forecast."""
        evaluation = self.evaluate(model, cancel_requested=cancel_requested)
        if cancel_requested is not None and cancel_requested():
            return self._cancelled_solution(model, evaluation)

        future = self.forecast_future(model)
        diagnostics = evaluation.diagnostics + future.diagnostics
        if (
            future.status in {ForecastingStatus.FAILED, ForecastingStatus.CANCELLED}
            or len(future.predicted_values) != model.horizon
            or len(future.fitted_values) != len(model.observations)
        ):
            return ForecastingSolution(
                status=future.status,
                method=model.method,
                origin=model.forecast_origin,
                metrics=evaluation.metrics,
                evaluation_status=evaluation.status,
                evaluation_folds=evaluation.folds,
                diagnostics=diagnostics,
            )

        historical_points = tuple(
            ForecastPoint(
                timestamp=observation.timestamp,
                predicted=fitted,
                actual=observation.value,
                residual=observation.value - fitted,
                segment=ForecastSegment.FITTED,
            )
            for observation, fitted in zip(
                model.observations,
                future.fitted_values,
                strict=True,
            )
            if fitted is not None
        )
        future_points = tuple(
            ForecastPoint(
                timestamp=timestamp,
                predicted=prediction,
                segment=ForecastSegment.FUTURE,
            )
            for timestamp, prediction in zip(
                model.future_timestamps(),
                future.predicted_values,
                strict=True,
            )
        )
        status = future.status
        if (
            status is ForecastingStatus.FORECASTED
            and evaluation.status
            in {ForecastEvaluationStatus.PARTIAL, ForecastEvaluationStatus.FAILED}
        ):
            status = ForecastingStatus.PARTIAL
        return ForecastingSolution(
            status=status,
            method=model.method,
            origin=model.forecast_origin,
            points=historical_points + future_points,
            metrics=evaluation.metrics,
            evaluation_status=evaluation.status,
            evaluation_folds=evaluation.folds,
            parameters=future.parameters,
            diagnostics=diagnostics,
        )

    def _solver_for(self, method: ForecastingMethod) -> ForecastingSolverPort:
        try:
            return self._solvers[method]
        except KeyError as exc:
            raise ValueError(f"No forecasting solver is registered for {method.value}") from exc

    @staticmethod
    def _evaluation_windows(model: ForecastingModel) -> tuple[tuple[int, int], ...]:
        options = model.evaluation
        if options.strategy is EvaluationStrategy.HOLDOUT:
            return ((len(model.observations) - options.holdout_size, options.holdout_size),)
        last_training_size = len(model.observations) - options.evaluation_horizon
        first_training_size = last_training_size - (options.origin_count - 1) * options.step
        return tuple(
            (
                first_training_size + origin_index * options.step,
                options.evaluation_horizon,
            )
            for origin_index in range(options.origin_count)
        )

    @staticmethod
    def _mase_scale(
        model: ForecastingModel,
        training: tuple[ForecastObservation, ...],
    ) -> float | None:
        lag = model.season_length or 1
        if len(training) <= lag:
            return None
        differences = tuple(
            abs(training[index].value - training[index - lag].value)
            for index in range(lag, len(training))
        )
        scale = sum(differences) / len(differences)
        return scale if scale > 0 else None

    @staticmethod
    def _metrics(
        points: tuple[ForecastPoint, ...],
        *,
        scales: tuple[float | None, ...],
    ) -> ForecastMetricSet:
        if not points:
            return ForecastMetricSet()
        errors = tuple(point.actual - point.predicted for point in points)
        absolute_errors = tuple(abs(error) for error in errors)
        mae = sum(absolute_errors) / len(points)
        rmse = math.sqrt(sum(error * error for error in errors) / len(points))
        actuals = tuple(point.actual for point in points)
        mape = (
            None
            if any(actual == 0 for actual in actuals)
            else 100
            * sum(
                abs(error / actual)
                for error, actual in zip(errors, actuals, strict=True)
            )
            / len(points)
        )
        mase = (
            None
            if len(scales) != len(points) or any(scale is None for scale in scales)
            else sum(
                error / scale
                for error, scale in zip(absolute_errors, scales, strict=True)
                if scale is not None
            )
            / len(points)
        )
        return ForecastMetricSet(mae=mae, rmse=rmse, mape=mape, mase=mase)

    @staticmethod
    def _cancelled_solution(
        model: ForecastingModel,
        evaluation: ForecastingEvaluationOutput,
    ) -> ForecastingSolution:
        return ForecastingSolution(
            status=ForecastingStatus.CANCELLED,
            method=model.method,
            origin=model.forecast_origin,
            metrics=evaluation.metrics,
            evaluation_status=evaluation.status,
            evaluation_folds=evaluation.folds,
            diagnostics=evaluation.diagnostics
            + (
                ForecastDiagnostic(
                    code="forecast_cancelled",
                    message="Forecast execution was cancelled before final fitting.",
                ),
            ),
        )
