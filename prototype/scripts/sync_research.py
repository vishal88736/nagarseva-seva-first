"""Copy public research deliverables and derive a small, cited evidence-card index."""
import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DEST = BASE / "prototype" / "dist"
RESEARCH = BASE / "research"
DATE = "2026-10-17"


def card(id, title, text, url, publisher, observation, location, keywords, kind="documented"):
    return dict(id=id, title=title, text=text, source_url=url, publisher=publisher,
                observation_period=observation, locator=location, access_date=DATE,
                keywords=keywords, kind=kind)


cards = [
    card("pmay-infrastructure", "PMAY-U 2.0 includes project infrastructure",
         "The September 2024 guidelines distinguish a completed dwelling from a completed project with infrastructure. Unified MIS, geotagging and monitoring are specified. These are documented requirements, not a test of local implementation.",
         "https://pmaymis.gov.in/PMAYMIS2_2024/Operational-Guidelines-of-PMAY-U-2.pdf", "MoHUA", "September 2024 guidelines", "Definitions; sections 5.1.15, 13 and 15", ["PMAY", "completion", "completed", "infrastructure", "houses", "MIS", "geotagging"]),
    card("pmay-verticals", "Four PMAY-U 2.0 verticals",
         "The four verticals are Beneficiary Led Construction (BLC), Affordable Housing in Partnership (AHP), Affordable Rental Housing (ARH) and Interest Subsidy Scheme (ISS). Legacy ISSR is not an additional fifth 2.0 vertical. Individual entitlement requires applicable current rules and competent authority review.",
         "https://pmaymis.gov.in/PMAYMIS2_2024/PmayFAQ.aspx", "MoHUA", "2.0 scheme; FAQ revision unknown", "Scheme FAQ and operational guidelines", ["verticals", "BLC", "AHP", "ARH", "ISS", "ISSR", "rental"]),
    card("sbm-functional", "SBM already specifies functional-asset monitoring",
         "The October 2021 SBM-U 2.0 guidelines specify functional-asset monitoring, ICT/GIS evaluation and an integrated platform for city/ward profiles, infrastructure and sanitation/waste progress. Indexed Chapter 10 was read; the full PDF was not acquired. Local effectiveness is untested.",
         "https://mahadma.maharashtra.gov.in/wp-content/uploads/2025/07/swachh-bharat-2.pdf", "MoHUA; Maharashtra DMA copy", "October 2021; mirror posted July 2025", "Chapter 10, printed p.81, sections 10.1–10.3.1", ["SBM", "functional", "assets", "monitoring", "GIS", "integration", "ward", "sanitation"]),
    card("swachhata-reopen", "Citizen confirmation and reopening already exist",
         "An official PIB description of Swachhata documents photo/location reports, ward assignment, notifications and a seven-day citizen confirmation/reopening window. A new geo-photo complaint app cannot claim this capability as new. No local resolution rate was measured.",
         "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2162194&lang=2&reg=48", "MoHUA / PIB", "30 August 2025 publication", "Swachhata complaint workflow", ["Swachhata", "complaint", "grievance", "reopen", "reopening", "confirmation", "seven", "7"]),
    card("sra-existing-gis", "SRA GIS has existing multi-layer mapping",
         "NIC describes existing SRA GIS and AASRA with more than ten layers, including wards, villages, slum clusters and rehabilitation schemes. Documentation does not establish a successful current export or complete household-service data.",
         "https://maharashtra.nic.in/news/gis-sra/", "NIC Maharashtra", "System account 2016–2020; page accessed 2026", "GIS for SRA Mumbai", ["SRA", "AASRA", "GIS", "layers", "spatial", "existing"]),
    card("sra-records", "SRA public rows identify locality leads",
         "The public SRA table includes Bharti CHS, Universal CHS and AHAD CHS & ITEHAD CHS in M-E/Govandi/Deonar with CTS 1-A. A shared CTS is not a unique scheme join. Listing presence and blank proposal fields establish neither delay nor completion status.",
         "https://dms.sra.gov.in/SRAPUBLIC/", "Slum Rehabilitation Authority Mumbai", "Record update date unknown; accessed 17 October 2026", "Visible public rows 3–5", ["SRA", "Bharti", "Universal", "Govandi", "Deonar", "CTS", "scheme", "proposal"]),
    card("me-historical-wash", "M/E water and toilet context is historical",
         "Census 2011 ward-wide household measures reproduced in the 2022 climate plan are: treated tap water 82.8%, tap within premises 53.6%, latrine within premises 35.8%. These are not slum-only or current figures. No private latrine is not the same as no toilet; these figures do not measure uptime or water quality.",
         "https://www.mcgm.gov.in/irj/go/km/docs/documents/Environment/Climate/Mumbai%20Climate%20Action%20Plan.pdf", "BMC; original Census 2011", "2011 observations; 2022 report", "Table 5, printed p.68", ["M/E", "2011", "water", "toilet", "latrine", "tap", "82.8", "53.6", "35.8", "premises", "historical"]),
    card("water-for-all", "BMC reports Water for All from May 2022",
         "BMC's 2025 year book reports an inclusive Water for All policy from May 2022 covering slums and unauthorised non-slum areas, among others. This qualifies older accounts of exclusion. A policy announcement does not establish universal reliable supply.",
         "https://portal.mcgm.gov.in/irj/go/km/docs/documents/HomePage%20Data/Whats%20New/English%20Year%20Book%202025%20Portal.pdf", "BMC", "Policy from May 2022; year book 2025", "Water for All policy section", ["water", "policy", "2022", "inclusive", "unauthorised"]),
    card("housing-shortage", "Housing shortage is a dated estimate",
         "The 2012 TG-12 estimate was 18.78 million nationally and 1.94 million for Maharashtra. It includes congestion and obsolescence as well as homelessness; it is not a current ward shortage or simply a count of absent buildings.",
         "https://mohua.gov.in/upload/uploadfiles/files/5Annual_Reprot_English_2012-13.pdf", "MoHUPA / NBO", "March 2012 estimate", "Annual report Tables 13–14, printed pp.75–76", ["housing", "shortage", "Maharashtra", "2012", "1.94", "18.78", "congestion"]),
    card("slum-population", "Slum population anchors are Census 2011",
         "The official historical table records 65,494,604 slum residents nationally and 11,848,423 in Maharashtra in Census 2011. The figures are not a 2026 enumeration or an M/E population estimate.",
         "https://mohua.gov.in/pdf/6253c2f3cea11Handbook-of-Urban-Statistics-2016.pdf", "Government of India; original Census 2011", "Census 2011", "Handbook Table 1.6", ["population", "2011", "Maharashtra", "11848423", "65494604", "census"]),
    card("census-rooms", "Census HL-04 covers historical ownership and rooms",
         "Catalogue 11441 is SLUM HL-04: Slum households by ownership status of the census houses, size of the household and number of dwelling rooms — 2011, reference PC11_SLUM_HL04. India/State aggregates and SHH1604-crc.pdf are advertised. Metadata was verified; the PDF was not downloaded. Ownership categories do not decide legal tenure or eligibility.",
         "https://censusindia.gov.in/nada/index.php/catalog/11441", "Registrar General & Census Commissioner India", "2011; metadata 21 January 2021", "Official indexed catalogue 11441", ["11441", "HL04", "HL-04", "ownership", "rooms", "dwelling", "household", "2011"]),
    card("osm-licence", "OSM data and service performance are different evidence",
         "OpenStreetMap data are available under ODbL with attribution and applicable database obligations. Crowdsourced mapped presence does not establish facility hours, capacity, accessibility or reliable service. Tile and API use policies are separate.",
         "https://www.openstreetmap.org/copyright", "OpenStreetMap Foundation / contributors", "Licence page accessed 17 October 2026", "Copyright and licence", ["OSM", "licence", "ODbL", "attribution", "OpenStreetMap", "copyright"]),
    card("transport-references", "Three transport points are secondary references",
         "Mapcarta's OSM-derived records locate Govandi railway station, Bainganwadi bus stop and Shivaji Nagar Bus Depot. Observation dates and passenger entrances were not verified; the depot point represents a way. No road network, timetable or service coverage was obtained.",
         "https://mapcarta.com/N3205733664", "OpenStreetMap contributors via Mapcarta (secondary)", "Observation unknown; accessed 17 October 2026", "OSM node 3205733664; see per-marker links", ["transport", "Govandi", "Bainganwadi", "depot", "station", "reference", "Mapcarta"], "secondary_reference"),
    card("stalled-policy", "Policy recognises stalled redevelopment",
         "Maharashtra Housing Policy 2025 recognises developer financial stress, stalled redevelopment and delayed transit rent. Its account records 228 MMR projects selected for a joint-venture route. This is a policy snapshot, not today's total stalled count or an M/E project status.",
         "https://cdnbbsr.s3waas.gov.in/s30bf727e907c5fc9d5356f11e4c45d613/uploads/2025/02/202507311134926775.pdf", "Government of Maharashtra", "Housing Policy 2025 snapshot", "Section 3.15.14", ["stalled", "228", "MMR", "transit", "rent", "finance", "developer", "joint", "venture"])
]


def main():
    target = DEST / "research"
    target.mkdir(parents=True, exist_ok=True)
    files = []
    for path in sorted(RESEARCH.iterdir()):
        if path.is_file() and path.suffix in {".md", ".csv", ".bib", ".json"}:
            shutil.copyfile(path, target / path.name)
            files.append(dict(name=path.name, url="./research/"+path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size))
    text = (RESEARCH / "literature_review.md").read_text()
    papers = []
    chunks = re.split(r"(?m)^## (L\d\d) — (.+)\n", text)
    for i in range(1, len(chunks), 3):
        id, title, body = chunks[i:i+3]
        doi = re.search(r"\[([^\]]+)\]\((https://doi\.org/[^)]+)\)", body)
        fields = {}
        for line in body.splitlines():
            match = re.match(r"\| (Area / question|Data / sample|Method|Findings|Limitations|Relevance) \| (.+) \|$", line)
            if match: fields[match[1]] = match[2]
        metadata = next((x for x in body.splitlines() if x.startswith("**")), "")
        papers.append(dict(id=id, title=title, metadata=metadata, doi=doi.group(1) if doi else None, url=doi.group(2) if doi else None, fields=fields))
    # The historical evidence workbench uses its original candidate schema.
    # The current acquisition inventory is also copied above as a separate document.
    inventory_path = RESEARCH / "dataset_inventory_legacy.csv"
    if not inventory_path.exists():
        inventory_path = RESEARCH / "dataset_inventory.csv"
    with inventory_path.open(newline="") as f:
        datasets = list(csv.DictReader(f))
    with (RESEARCH / "problem_evidence_matrix.csv").open(newline="") as f:
        problems = list(csv.DictReader(f))
    data = dict(reviewed_at=DATE, cards=cards, papers=papers, datasets=datasets, problems=problems, files=files,
                counts=dict(publications=len(papers), government_impact_reports=1, dataset_candidates=len(datasets), problem_records=len(problems)),
                schemes=[dict(name=n, ward="M-E", locality="Govandi / Deonar", cts="1-A", proposal=None, record_date=None, source_url="https://dms.sra.gov.in/SRAPUBLIC/") for n in ["Bharti CHS", "Universal CHS", "AHAD CHS & ITEHAD CHS"]])
    case_path = DEST / "data/public-schemes.json"
    if case_path.is_file():
        data["publicCase"] = json.loads(case_path.read_text())
    data_dir = DEST / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "research.json").write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n")
    print(f"Synced {len(files)} public research files, {len(cards)} source cards and {len(papers)} publication records.")


if __name__ == "__main__":
    main()
