"""Read an Avni implementation bundle and work out what a valid observation may contain.

A bundle is the directory the admin app exports: concepts.json, forms/, formMappings.json,
subjectTypes.json, programs.json, encounterTypes.json and friends. It is the same artefact an
implementation keeps in version control, so a run can name exactly which configuration it used.

Nothing here touches a database. The bundle is the only input.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Datatypes whose values are a reference to an S3 object. Generating them implies uploading
# media, which section D5 puts out of scope, so form elements carrying them are skipped.
MEDIA_DATATYPES = frozenset({"Image", "ImageV2", "Video", "Audio", "File"})

# QuestionGroup nests a further set of elements inside one observation value. Supported shape,
# but a different one, and skipped until the flat case is proven.
UNSUPPORTED_DATATYPES = frozenset({"QuestionGroup"})


@dataclass(frozen=True)
class Concept:
    uuid: str
    name: str
    data_type: str | None
    answer_uuids: tuple[str, ...] = ()
    low_absolute: float | None = None
    high_absolute: float | None = None

    @property
    def generatable(self) -> bool:
        if not self.data_type:
            return False
        if self.data_type in MEDIA_DATATYPES or self.data_type in UNSUPPORTED_DATATYPES:
            return False
        # A Coded concept with no answers has nothing valid to emit.
        return not (self.data_type == "Coded" and not self.answer_uuids)


@dataclass(frozen=True)
class Element:
    """A form element that can carry a generated observation."""
    uuid: str
    concept: Concept
    multi_select: bool
    mandatory: bool


@dataclass(frozen=True)
class FormMapping:
    form_uuid: str
    form_type: str
    subject_type_uuid: str | None
    program_uuid: str | None
    encounter_type_uuid: str | None

    @property
    def key(self) -> tuple[str | None, str | None, str | None, str]:
        return (self.subject_type_uuid, self.program_uuid, self.encounter_type_uuid, self.form_type)


@dataclass
class Bundle:
    path: Path
    concepts: dict[str, Concept] = field(default_factory=dict)
    forms: dict[str, list[Element]] = field(default_factory=dict)
    mappings: list[FormMapping] = field(default_factory=list)

    def elements_for(self, mapping: FormMapping) -> list[Element]:
        """The elements a valid observation for this mapping may be keyed on."""
        return self.forms.get(mapping.form_uuid, [])

    def concept_uuids(self) -> set[str]:
        """Every concept reachable through a live form element, across all mappings."""
        return {e.concept.uuid for m in self.mappings for e in self.elements_for(m)}


def _read(path: Path, name: str, default):
    f = path / name
    if not f.exists():
        return default
    with f.open() as fh:
        return json.load(fh)


def _concept(raw: dict) -> Concept:
    answers = tuple(
        a["uuid"] for a in raw.get("answers") or []
        if a.get("uuid") and not a.get("voided")
    )
    return Concept(
        uuid=raw["uuid"],
        name=raw.get("name", ""),
        data_type=raw.get("dataType"),
        answer_uuids=answers,
        low_absolute=raw.get("lowAbsolute"),
        high_absolute=raw.get("highAbsolute"),
    )


def load(path: str | Path) -> Bundle:
    """Load a bundle directory.

    Voided concepts, forms, elements and mappings are dropped. Roughly 40% of the elements in a
    real bundle are voided, and emitting observations against them produces data the client will
    not render.
    """
    p = Path(path)
    if not p.is_dir():
        raise NotADirectoryError(f"bundle path is not a directory: {p}")

    bundle = Bundle(path=p)

    for raw in _read(p, "concepts.json", []):
        if raw.get("voided") or not raw.get("uuid"):
            continue
        bundle.concepts[raw["uuid"]] = _concept(raw)

    forms_dir = p / "forms"
    if forms_dir.is_dir():
        for f in sorted(forms_dir.glob("*.json")):
            with f.open() as fh:
                form = json.load(fh)
            if form.get("voided") or not form.get("uuid"):
                continue
            elements: list[Element] = []
            for group in form.get("formElementGroups") or []:
                if group.get("voided"):
                    continue
                for el in group.get("formElements") or []:
                    if el.get("voided"):
                        continue
                    raw_concept = el.get("concept") or {}
                    if not raw_concept.get("uuid"):
                        continue
                    # The element embeds its concept, but concepts.json is the fuller record --
                    # it carries lowAbsolute/highAbsolute, which the embedded copy omits.
                    concept = bundle.concepts.get(raw_concept["uuid"]) or _concept(raw_concept)
                    if not concept.generatable:
                        continue
                    elements.append(Element(
                        uuid=el["uuid"],
                        concept=concept,
                        multi_select=el.get("type") == "MultiSelect",
                        mandatory=bool(el.get("mandatory")),
                    ))
            bundle.forms[form["uuid"]] = elements

    for raw in _read(p, "formMappings.json", []):
        if raw.get("voided") or not raw.get("formUUID"):
            continue
        bundle.mappings.append(FormMapping(
            form_uuid=raw["formUUID"],
            form_type=raw.get("formType", ""),
            subject_type_uuid=raw.get("subjectTypeUUID"),
            program_uuid=raw.get("programUUID"),
            encounter_type_uuid=raw.get("encounterTypeUUID"),
        ))

    return bundle
