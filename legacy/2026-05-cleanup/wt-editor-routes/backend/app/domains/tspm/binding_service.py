"""Scenario data binding helpers for TSPM."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.tspm.models import (
    TspmScenario,
    TspmScenarioDataBinding,
    TspmTestDataSet,
)
from app.domains.tspm.schemas import (
    DataBindingCreate,
    ExpandedScenarioOut,
    ExpandedScenarioRow,
    ExpandedStep,
)


def bind_data_to_scenario_for_project(
    db: Session,
    project_id: str,
    scenario_id: str,
    body: DataBindingCreate,
) -> TspmScenarioDataBinding:
    scenario = get_scenario_or_404(db, project_id, scenario_id)
    dataset = get_test_data_or_404(db, project_id, body.data_set_id)
    binding = TspmScenarioDataBinding(
        scenario_id=scenario.id,
        data_set_id=dataset.id,
        parameter_mapping=body.parameter_mapping,
    )
    db.add(binding)
    db.commit()
    db.refresh(binding)
    return binding


def get_expanded_scenario_for_project(
    db: Session,
    project_id: str,
    scenario_id: str,
) -> ExpandedScenarioOut:
    scenario = get_scenario_or_404(db, project_id, scenario_id)
    bindings = list(
        db.scalars(
            select(TspmScenarioDataBinding).where(
                TspmScenarioDataBinding.scenario_id == scenario_id
            )
        )
    )

    expanded_rows: list[ExpandedScenarioRow] = []
    if bindings:
        binding = bindings[0]
        dataset = db.get(TspmTestDataSet, binding.data_set_id)
        if dataset and dataset.rows:
            mapping = binding.parameter_mapping or {}
            for row_idx, row in enumerate(dataset.rows):
                row_steps: list[ExpandedStep] = []
                for step in scenario.steps or []:
                    text = step.get("text", "")
                    for param_name, col_name in mapping.items():
                        if isinstance(row, dict):
                            value = row.get(col_name, "")
                        else:
                            value = ""
                        text = text.replace(f"{{{{{param_name}}}}}", str(value))
                    row_steps.append(
                        ExpandedStep(
                            order=step.get("order", 0),
                            keyword=step.get("keyword", ""),
                            text=text,
                        )
                    )
                expanded_rows.append(ExpandedScenarioRow(row_index=row_idx, steps=row_steps))

    return ExpandedScenarioOut(
        scenario_id=scenario.id,
        title=scenario.title,
        expanded_rows=expanded_rows,
    )


def get_scenario_or_404(db: Session, project_id: str, scenario_id: str) -> TspmScenario:
    scenario = db.get(TspmScenario, scenario_id)
    if scenario is None or scenario.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Senaryo bulunamadı")
    return scenario


def get_test_data_or_404(db: Session, project_id: str, data_set_id: str) -> TspmTestDataSet:
    dataset = db.get(TspmTestDataSet, data_set_id)
    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Veri seti bulunamadı")
    return dataset
