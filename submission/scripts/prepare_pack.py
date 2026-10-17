"""Validate public submission materials and build a credential-free delivery archive."""
import hashlib
import json
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SUB = ROOT / "submission"


def words(text):
    return len(re.findall(r"\S+", text))


def main():
    bank = json.loads((SUB / "answer_bank.json").read_text())
    answer_lines = ["# Draft application answers", "", "Prepared 18 October 2026. These sections map the public FAQ's requested content, not a verified authenticated form. **Draft budgets below are authoring constraints, not official word limits.** Counts include answer text only and use whitespace-separated words. Personal fields are deliberately omitted. No invention of identity, qualifications, IP, users or revenue is permitted.", "", "Verify the actual word/character and file limits in the portal before transferring answers. [Requirements and source/access record](competition_requirements.md).", ""]
    counts = []
    for i, item in enumerate(bank["answers"], 1):
        count = words(item["answer"])
        assert count <= item["draft_limit_words"], (item["field"], count, item["draft_limit_words"])
        counts.append({"field": item["field"], "words": count, "draft_budget": item["draft_limit_words"], "official_limit_verified": False})
        answer_lines += [f"## {i}. {item['field']}", "", f"**{count} words / {item['draft_limit_words']}-word draft budget.**", "", item["answer"], ""]
        if item["sources"]:
            answer_lines += ["Supporting sources; access dates recorded in the research and pilot notes: " + ", ".join(f"[source {n}]({url})" for n, url in enumerate(item["sources"], 1)) + ".", ""]
    answer_lines += ["## Applicant-only fields", "", "Complete legal name, age/category, domicile, background/skills, contact details, identity authentication, declarations, actual IP/registration details and final submission privately in the actual portal. These were skipped at the applicant's request. No profile fact should be inferred from a workspace username. Do not invent a hosted demo URL; the repository and local five-screen application are the demonstration deliverables.", ""]
    (SUB / "application_answers.md").write_text("\n".join(answer_lines))
    (SUB / "answer_validation.json").write_text(json.dumps({"status":"within_draft_budgets", "official_limits_verified":False, "answers":counts}, indent=2)+"\n")
    required = ["README.md", "competition_requirements.md", "application_answers.md", "pitch_scripts.md", "judge_questions.md", "deck_outline.md", "pilot_and_adoption.md", "validation_kit.md", "financial_model.md", "impact_metrics.md", "winning_edge_and_audit.md", "phase_checklists.md", "browser_acceptance.md", "delivery_validation.md", "outputs/urbansaarthi-pitch.pptx", "outputs/urbansaarthi-pitch.pdf", "outputs/pilot-budget.xlsx"]
    assert all((SUB / name).is_file() for name in required), [n for n in required if not (SUB/n).is_file()]
    broken = []
    for md in [ROOT/"README.md", ROOT/"prototype/README.md", *ROOT.glob("research/*.md"), *SUB.glob("*.md")]:
        for target in re.findall(r"\]\(([^)]+)\)", md.read_text()):
            if target.startswith(("https://", "http://", "#")):
                continue
            path = (md.parent / target.split("#")[0]).resolve()
            if not path.is_file(): broken.append((str(md.relative_to(ROOT)), target))
    assert not broken, broken
    # Check native package contents without implying PowerPoint/Excel execution.
    NS = {"a":"http://schemas.openxmlformats.org/drawingml/2006/main"}
    with zipfile.ZipFile(SUB/"outputs/urbansaarthi-pitch.pptx") as z:
        assert z.testzip() is None
        slides = sorted(n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml",n))
        assert len(slides)==6
        native_tables = [i+1 for i,n in enumerate(slides) if ET.fromstring(z.read(n)).findall('.//a:tbl',NS)]
        assert native_tables==[3], native_tables
        all_text=' '.join(' '.join(e.text or '' for e in ET.fromstring(z.read(n)).findall('.//a:t',NS)) for n in slides)
        for text in ['UrbanSaarthi','132,000','162,360','Working Prototype']:
            assert text in all_text, text
        assert len([n for n in z.namelist() if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml",n)])==6
    X={"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(SUB/"outputs/pilot-budget.xlsx") as z:
        assert z.testzip() is None
        sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        for address, expected in [('B5',132000),('B6',162360),('B8',6600)]:
            c=sheet.find(f'.//m:c[@r="{address}"]/m:v',X)
            assert c is not None and abs(float(c.text)-expected)<1e-7,(address,ET.tostring(sheet)[:100])
    forbidden={'.git','.aws','.codex','.agents','node_modules','__pycache__','test-artifacts','.build'}
    files=[ROOT/'README.md']
    for directory in ['research','prototype','submission','pilot']:
        files += [p for p in (ROOT/directory).rglob('*') if p.is_file() and not any(x in forbidden for x in p.relative_to(ROOT).parts) and p.suffix not in {'.pyc','.zip'} and p.name not in {'file_manifest.json', 'seva-evidence-pitch.pptx'} and '.inspect.' not in p.name and not p.name.startswith('.env')]
    unique=sorted(set(files))
    manifest={str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in unique}
    (SUB/'file_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=SUB/'outputs/seva-submission-kit.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in unique:z.write(p,str(p.relative_to(ROOT)))
        z.write(SUB/'file_manifest.json','submission/file_manifest.json')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(not any(x in forbidden for x in Path(n).parts) for n in z.namelist())
        for n,item in manifest.items():assert hashlib.sha256(z.read(n)).hexdigest()==item['sha256'],n
    summary={'draft_answers':len(counts),'all_within_draft_budgets':True,'official_limits_verified':False,'slides':6,'native_tables':1,'artifact_package_checks':'passed','archive_members':len(manifest)+1,'archive_bytes':archive.stat().st_size,'browser_passed': json.loads((ROOT/'integration/urban-validation.json').read_text()).get('status') == 'passed','field_validation':False}
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
