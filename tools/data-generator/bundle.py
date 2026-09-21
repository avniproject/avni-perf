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

# Datatypes whose values are a reference to an S3 object. The generator does not emit them - it
# would have to produce the objects too - but it counts them, because how many media files an
# encounter queues is what sets the media load on a sync (D5.1) and it is a property of the
# configuration rather than something to guess at.
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
    read_only: bool = False

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
class MediaElement:
    """A form element whose value is a file the device uploads before it pushes any data.

    Counted rather than generated. One of these on a form means every filled instance of that form
    queues at least one `GET /media/uploadUrl` and one direct-to-S3 PUT, ahead of the data push -
    so the count per encounter type, not a platform-wide average, is what sizes media load.

    Two attributes decide whether it is one file or sixteen, and missing either understates the
    load by an order of magnitude:

    `editable` separates capture from display. An element the app fills in - an AI verdict's copy
    of an image, a gallery of the suspicious ones - carries a reference to a file that was already
    uploaded by the element that captured it. Counting those again double-counts every image.

    `repeatable` comes from the parent question group. An Image inside a repeatable group is filled
    once per repeat, so a screening protocol that says "photograph every lesion" produces as many
    files as there are lesions from a single form element.
    """
    uuid: str
    concept_name: str
    data_type: str
    multi_select: bool
    mandatory: bool
    read_only: bool
    editable: bool = True
    parent_uuid: str | None = None
    parent_name: str | None = None
    repeatable: bool = False

    @property
    def captured(self) -> bool:
        """Whether the device produces a file here, as opposed to displaying one it already has."""
        return self.editable

    def files(self, repeats: int = 1) -> float:
        """Files one filled instance of this element queues, given how often its group repeats.

        `repeats` is the caller's input because no bundle records it: "take photos of all lesions"
        produces as many files as the patient has lesions. A multi-select holds an unknown number
        and still counts as one, so the result remains a floor.
        """
        if not self.captured:
            return 0.0
        return float(repeats) if self.repeatable else 1.0


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
    media: dict[str, list[MediaElement]] = field(default_factory=dict)
    mappings: list[FormMapping] = field(default_factory=list)

    def elements_for(self, mapping: FormMapping) -> list[Element]:
        """The elements a valid observation for this mapping may be keyed on."""
        return self.forms.get(mapping.form_uuid, [])

    def media_for(self, mapping: FormMapping) -> list[MediaElement]:
        """The media elements a filled instance of this mapping's form would queue."""
        return self.media.get(mapping.form_uuid, [])

    def media_per_form_type(self, repeats: int = 1) -> dict[str, tuple[float, float]]:
        """Files queued per filled form, by form type, as (mandatory only, every element).

        Two numbers rather than one because the gap between them is a question about field
        behaviour - how often an optional photo is actually taken - that the bundle cannot answer.

        Averaged across the distinct mappings of each type, which assumes encounter types are
        equally frequent. They are not: a screening programme's screening encounter dominates its
        own mix, and weighting by real frequency moves this figure a long way. It is a starting
        point to be overridden per deployment, not a measurement.

        `repeats` multiplies every element inside a repeatable question group. It is the single
        largest term for an image-heavy form and nothing in the bundle sets it.
        """
        by_type: dict[str, list[tuple[float, float]]] = {}
        seen: set[tuple[str, str]] = set()
        for m in self.mappings:
            if (m.form_type, m.form_uuid) in seen:
                continue
            seen.add((m.form_type, m.form_uuid))
            elements = self.media_for(m)
            mandatory = sum(e.files(repeats) for e in elements if e.mandatory)
            every = sum(e.files(repeats) for e in elements)
            by_type.setdefault(m.form_type, []).append((mandatory, every))
        return {
            t: (sum(a for a, _ in v) / len(v), sum(b for _, b in v) / len(v))
            for t, v in by_type.items() if v
        }

    def concept_uuids(self) -> set[str]:
        """Every concept reachable through a live form element, across all mappings."""
        return {e.concept.uuid for m in self.mappings for e in self.elements_for(m)}


def _read(path: Path, name: str, default):
    f = path / name
    if not f.exists():
        return default
    with f.open() as fh:
        return json.load(fh)


def _key_value(raw: dict, key: str):
    """One of a concept's or form element's keyValues, or None. Used for readOnly, which decides
    whether a media element is captured on the device at all."""
    for kv in raw.get("keyValues") or []:
        if kv.get("key") == key:
            return kv.get("value")
    return None


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
        read_only=_key_value(raw, "readOnly") is True,
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
            media: list[MediaElement] = []
            # Question-group membership is a reference to another element in the same form
            # (parentFormElementUuid), which may be declared either side of the child. So the
            # live elements are indexed first and resolved second.
            live = {
                el["uuid"]: el
                for group in form.get("formElementGroups") or []
                if not group.get("voided")
                for el in group.get("formElements") or []
                if not el.get("voided") and el.get("uuid")
            }
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
                    if concept.data_type in MEDIA_DATATYPES:
                        parent = live.get(el.get("parentFormElementUuid") or "")
                        media.append(MediaElement(
                            uuid=el["uuid"],
                            concept_name=concept.name,
                            data_type=concept.data_type or "",
                            multi_select=el.get("type") == "MultiSelect",
                            mandatory=bool(el.get("mandatory")),
                            # Either level can set it, and the element wins: it is the more
                            # specific of the two. Read off concepts.json rather than the copy
                            # embedded in the element, which is the fuller record - the same
                            # reason lowAbsolute is taken from there.
                            read_only=(_key_value(el, "readOnly") is True
                                       or concept.read_only),
                            # Absent means editable. Only an explicit false marks an element the
                            # app fills in rather than the user.
                            editable=_key_value(el, "editable") is not False,
                            parent_uuid=(parent or {}).get("uuid"),
                            parent_name=(parent or {}).get("name"),
                            repeatable=_key_value(parent or {}, "repeatable") is True,
                        ))
                        continue
                    if not concept.generatable:
                        continue
                    elements.append(Element(
                        uuid=el["uuid"],
                        concept=concept,
                        multi_select=el.get("type") == "MultiSelect",
                        mandatory=bool(el.get("mandatory")),
                    ))
            bundle.forms[form["uuid"]] = elements
            bundle.media[form["uuid"]] = media

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
