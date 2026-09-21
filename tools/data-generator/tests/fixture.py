"""A small synthetic bundle. Deliberately not anyone's real configuration -- the generator takes
the bundle path as a parameter, so no implementation's config belongs in this repository."""
import json
from pathlib import Path

CODED = "c0000000-0000-0000-0000-000000000001"
NUMERIC = "c0000000-0000-0000-0000-000000000002"
TEXT = "c0000000-0000-0000-0000-000000000003"
MEDIA = "c0000000-0000-0000-0000-000000000004"
MEDIA_AUDIO = "c0000000-0000-0000-0000-000000000008"
MEDIA_REPEATED = "c0000000-0000-0000-0000-000000000009"
MEDIA_DISPLAY = "c0000000-0000-0000-0000-00000000000a"
QGROUP_FE = "e-questiongroup"
EMPTY_CODED = "c0000000-0000-0000-0000-000000000005"
VOIDED = "c0000000-0000-0000-0000-000000000006"
QGROUP = "c0000000-0000-0000-0000-000000000007"
ANSWERS = [f"a0000000-0000-0000-0000-00000000000{i}" for i in range(1, 5)]
FORM = "f0000000-0000-0000-0000-000000000001"
VOIDED_FORM = "f0000000-0000-0000-0000-000000000002"
SUBJECT_TYPE = "s0000000-0000-0000-0000-000000000001"


def _el(uuid, concept_uuid, *, type_="SingleSelect", mandatory=False, voided=False):
    return {"uuid": uuid, "type": type_, "mandatory": mandatory, "voided": voided,
            "concept": {"uuid": concept_uuid}}


def write(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "forms").mkdir(exist_ok=True)

    concepts = [
        {"uuid": CODED, "name": "Coded One", "dataType": "Coded",
         "answers": [{"uuid": a} for a in ANSWERS[:3]] + [{"uuid": ANSWERS[3], "voided": True}]},
        {"uuid": NUMERIC, "name": "Weight", "dataType": "Numeric",
         "lowAbsolute": 2.0, "highAbsolute": 8.0},
        {"uuid": TEXT, "name": "Remark", "dataType": "Text"},
        {"uuid": MEDIA, "name": "Photo", "dataType": "Image",
         "keyValues": [{"key": "readOnly", "value": True}]},
        {"uuid": MEDIA_AUDIO, "name": "Recording", "dataType": "Audio"},
        {"uuid": MEDIA_REPEATED, "name": "Lesion Photo", "dataType": "Image"},
        {"uuid": MEDIA_DISPLAY, "name": "AI Copy", "dataType": "Image"},
        {"uuid": EMPTY_CODED, "name": "No Answers", "dataType": "Coded", "answers": []},
        {"uuid": VOIDED, "name": "Gone", "dataType": "Text", "voided": True},
        {"uuid": QGROUP, "name": "Group", "dataType": "QuestionGroup"},
    ]
    (root / "concepts.json").write_text(json.dumps(concepts))

    form = {"uuid": FORM, "name": "Test Form", "formType": "IndividualProfile", "formElementGroups": [
        {"uuid": "g1", "formElements": [
            _el("e1", CODED, mandatory=True),
            _el("e2", CODED, type_="MultiSelect"),
            _el("e3", NUMERIC),
            _el("e4", TEXT),
            _el("e5", MEDIA),
            _el("e5b", MEDIA_AUDIO, mandatory=True),
            # A repeatable question group, the image captured inside it, and the
            # app's own display-only copy of that same image.
            {"uuid": QGROUP_FE, "type": "SingleSelect", "mandatory": False,
             "concept": {"uuid": QGROUP},
             "keyValues": [{"key": "repeatable", "value": True}]},
            {"uuid": "e5c", "type": "SingleSelect", "mandatory": True,
             "concept": {"uuid": MEDIA_REPEATED},
             "parentFormElementUuid": QGROUP_FE},
            {"uuid": "e5d", "type": "SingleSelect", "mandatory": False,
             "concept": {"uuid": MEDIA_DISPLAY},
             "parentFormElementUuid": QGROUP_FE,
             "keyValues": [{"key": "editable", "value": False}]},
            _el("e6", EMPTY_CODED),
            _el("e7", VOIDED),
            _el("e8", QGROUP),
            _el("e9", TEXT, voided=True),
        ]},
        {"uuid": "g2", "voided": True, "formElements": [_el("e10", TEXT)]},
    ]}
    (root / "forms" / "form.json").write_text(json.dumps(form))
    (root / "forms" / "voided.json").write_text(json.dumps(
        {"uuid": VOIDED_FORM, "name": "Dead", "formType": "Encounter", "voided": True,
         "formElementGroups": [{"uuid": "g3", "formElements": [_el("e11", TEXT)]}]}))

    (root / "formMappings.json").write_text(json.dumps([
        {"uuid": "m1", "formUUID": FORM, "formType": "IndividualProfile",
         "subjectTypeUUID": SUBJECT_TYPE},
        {"uuid": "m2", "formUUID": VOIDED_FORM, "formType": "Encounter",
         "subjectTypeUUID": SUBJECT_TYPE, "voided": True},
    ]))
    return root
