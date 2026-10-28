"""Build Go.Data location files for Brazil (IBGE UF/municipality tree and DSEI tree).

Inputs (data/raw): IBGE localidades API dumps, kelvins/municipios-brasileiros coordinates,
OpenDataSUS CNES establishments dump. Outputs (dist/): Go.Data hierarchical JSON + flat CSV.
"""
import csv
import io
import json
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DIST = ROOT / "dist"

LEVEL = "LNG_REFERENCE_DATA_CATEGORY_LOCATION_GEOGRAPHICAL_LEVEL_ADMIN_LEVEL_{}"

# The 34 Distritos Sanitarios Especiais Indigenas (SESAI/MS)
DSEIS = [
    ("alagoas-sergipe", "Alagoas e Sergipe", r"ALAGOAS|AL SE"),
    ("altamira", "Altamira", r"ALTAMIRA"),
    ("alto-rio-jurua", "Alto Rio Juruá", r"JURUA"),
    ("alto-rio-negro", "Alto Rio Negro", r"RIO NEGRO"),
    ("alto-rio-purus", "Alto Rio Purus", r"ALTO (RIO )?PURUS"),
    ("alto-rio-solimoes", "Alto Rio Solimões", r"ALTO (RIO )?SOLIM"),
    ("amapa-norte-para", "Amapá e Norte do Pará", r"AMAPA"),
    ("araguaia", "Araguaia", r"ARAGUAIA"),
    ("bahia", "Bahia", r"BAHIA"),
    ("ceara", "Ceará", r"CEARA"),
    ("cuiaba", "Cuiabá", r"CUIABA"),
    ("guama-tocantins", "Guamá-Tocantins", r"GUAMA"),
    ("interior-sul", "Interior Sul", r"INTERIOR SUL"),
    ("kaiapo-mato-grosso", "Kaiapó do Mato Grosso", r"KAIAPO DO MATO GROSSO|KAYAPO DO MATO GROSSO|KAIAPO MT"),
    ("kaiapo-para", "Kaiapó do Pará", r"KAIAPO DO PARA|KAYAPO DO PARA"),
    ("leste-roraima", "Leste de Roraima", r"LESTE DE RORAIMA|LESTE RORAIMA"),
    ("litoral-sul", "Litoral Sul", r"LITORAL SUL"),
    ("manaus", "Manaus", r"\bMANAUS\b"),
    ("maranhao", "Maranhão", r"MARANHAO"),
    ("mato-grosso-sul", "Mato Grosso do Sul", r"MATO GROSSO DO SUL"),
    ("medio-rio-purus", "Médio Rio Purus", r"MEDIO (RIO )?PURUS"),
    ("medio-rio-solimoes", "Médio Rio Solimões e Afluentes", r"MEDIO (RIO )?SOLIM"),
    ("minas-gerais-espirito-santo", "Minas Gerais e Espírito Santo", r"MINAS GERAIS|\bMG ES\b|MG E ES"),
    ("parintins", "Parintins", r"PARINTINS"),
    ("pernambuco", "Pernambuco", r"PERNAMBUCO|DSEI PE\b"),
    ("porto-velho", "Porto Velho", r"PORTO VELHO"),
    ("potiguara", "Potiguara", r"POTIGUARA"),
    ("rio-tapajos", "Rio Tapajós", r"TAPAJOS"),
    ("tocantins", "Tocantins", r"(?<!GUAMA )TOCANTINS"),
    ("vale-javari", "Vale do Javari", r"JAVARI"),
    ("vilhena", "Vilhena", r"VILHENA"),
    ("xavante", "Xavante", r"XAVANTE"),
    ("xingu", "Xingu", r"XINGU"),
    ("yanomami", "Yanomami", r"YANOMAMI|YANOAMAMI"),
]


def strip_accents(text):
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def geo(lat, lng):
    try:
        return {"lat": float(lat), "lng": float(lng)}
    except (TypeError, ValueError):
        return None


def location(id_, name, level, lat=None, lng=None, identifiers=(), synonyms=()):
    loc = {
        "id": id_,
        "name": name,
        "active": True,
        "geographicalLevelId": LEVEL.format(level),
        "identifiers": [{"code": c, "description": d} for c, d in identifiers],
        "synonyms": list(synonyms),
    }
    g = geo(lat, lng)
    if g:
        loc["geoLocation"] = g
    return loc


def synonyms_for(name):
    plain = strip_accents(name)
    return [plain] if plain != name else []


def build_ibge_tree():
    states = json.loads((RAW / "ibge_estados.json").read_text(encoding="utf-8"))
    municipalities = json.loads((RAW / "ibge_municipios.json").read_text(encoding="utf-8"))
    with open(RAW / "estados.csv", encoding="utf-8-sig") as f:
        state_coords = {r["codigo_uf"]: r for r in csv.DictReader(f)}
    with open(RAW / "municipios.csv", encoding="utf-8") as f:
        mun_coords = {r["codigo_ibge"]: r for r in csv.DictReader(f)}

    missing_coords = []
    by_state = {}
    for m in municipalities:
        code7 = str(m["municipio-id"])
        c = mun_coords.get(code7)
        if not c:
            missing_coords.append(f'{code7} {m["municipio-nome"]}/{m["UF-sigla"]}')
        by_state.setdefault(str(m["UF-id"]), []).append(
            {
                "location": location(
                    f"br-mun-{code7}",
                    m["municipio-nome"],
                    2,
                    c and c["latitude"],
                    c and c["longitude"],
                    identifiers=[
                        (code7, "IBGE"),
                        (code7[:6], "IBGE6 (SINAN)"),
                    ],
                    synonyms=synonyms_for(m["municipio-nome"]),
                ),
                "children": [],
            }
        )

    state_nodes = []
    for s in sorted(states, key=lambda s: s["nome"]):
        uf = str(s["id"])
        c = state_coords.get(uf, {})
        children = sorted(by_state.get(uf, []), key=lambda n: n["location"]["name"])
        state_nodes.append(
            {
                "location": location(
                    f"br-uf-{uf}",
                    s["nome"],
                    1,
                    c.get("latitude"),
                    c.get("longitude"),
                    identifiers=[(uf, "IBGE"), (s["sigla"], "UF")],
                    synonyms=[s["sigla"]] + synonyms_for(s["nome"]),
                ),
                "children": children,
            }
        )

    root = {
        "location": location("br", "Brasil", 0, -14.235, -51.9253, identifiers=[("BR", "ISO 3166-1")],
                             synonyms=["Brazil", "BRA"]),
        "children": state_nodes,
    }
    return [root], len(municipalities), missing_coords


def load_cnes_polos():
    z = zipfile.ZipFile(RAW / "cnes_estab.zip")
    name = z.namelist()[0]
    reader = csv.DictReader(io.TextIOWrapper(z.open(name), encoding="latin-1"), delimiter=";")
    return [
        r for r in reader
        if r["TP_UNIDADE"] == "72" and re.search(r"\bPOLO\b", r["NO_FANTASIA"]) and not r["CO_MOTIVO_DESAB"]
    ]


def match_dsei(razao_social):
    text = strip_accents(razao_social.upper())
    if not re.search(r"INDIG|DSEI|DISTRITO SANITARIO ESPECIAL", text):
        return None
    hits = [slug for slug, _, pattern in DSEIS if re.search(pattern, text)]
    return hits[0] if len(hits) == 1 else None


def polo_name(fantasia):
    name = re.sub(r"\s+", " ", fantasia).strip().title()
    return name.replace(" Do ", " do ").replace(" Da ", " da ").replace(" De ", " de ").replace(" Dos ", " dos ")


def build_dsei_tree():
    polos = load_cnes_polos()
    by_dsei = {slug: [] for slug, _, _ in DSEIS}
    unmatched = []
    for p in polos:
        slug = match_dsei(p["NO_RAZAO_SOCIAL"])
        if not slug:
            unmatched.append(p)
            continue
        by_dsei[slug].append(
            {
                "location": location(
                    f"br-polo-{p['CO_CNES']}",
                    polo_name(p["NO_FANTASIA"]),
                    2,
                    p["NU_LATITUDE"],
                    p["NU_LONGITUDE"],
                    identifiers=[(p["CO_CNES"], "CNES"), (p["CO_IBGE"], "IBGE6 (SINAN) município")],
                ),
                "children": [],
            }
        )

    dsei_nodes = []
    for slug, name, _ in DSEIS:
        children = sorted(by_dsei[slug], key=lambda n: n["location"]["name"])
        names = [c["location"]["name"] for c in children]
        dups = {n for n in names if names.count(n) > 1}
        for c in children:
            if c["location"]["name"] in dups:
                c["location"]["name"] += f' (CNES {c["location"]["identifiers"][0]["code"]})'
        dsei_nodes.append(
            {
                "location": location(f"br-dsei-{slug}", f"DSEI {name}", 1, synonyms=synonyms_for(f"DSEI {name}")),
                "children": children,
            }
        )
    root = {
        "location": location("br-dsei", "Brasil - Distritos Sanitários Especiais Indígenas (DSEI)", 0,
                             synonyms=["DSEI", "SESAI"]),
        "children": dsei_nodes,
    }
    matched = sum(len(v) for v in by_dsei.values())
    return [root], matched, unmatched


def flatten(tree, parent_id=None):
    for node in tree:
        loc = node["location"]
        yield loc, parent_id
        yield from flatten(node["children"], loc["id"])


def write_outputs(prefix, tree):
    DIST.mkdir(exist_ok=True)
    (DIST / f"{prefix}.json").write_text(json.dumps(tree, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(DIST / f"{prefix}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["NAME", "ID", "CODE", "LONG", "LAT", "ADMIN_LEVEL", "PARENTLOCATIONID"])
        for loc, parent in flatten(tree):
            g = loc.get("geoLocation") or {}
            code = loc["identifiers"][0]["code"] if loc["identifiers"] else ""
            level = loc["geographicalLevelId"].rsplit("_", 1)[-1]
            w.writerow([loc["name"], loc["id"], code, g.get("lng", ""), g.get("lat", ""), level, parent or ""])


def main():
    ibge, n_mun, missing = build_ibge_tree()
    write_outputs("brasil-uf-municipios", ibge)
    print(f"IBGE tree: 27 UFs, {n_mun} municipios; sem coordenadas: {missing}")

    dsei, matched, unmatched = build_dsei_tree()
    write_outputs("brasil-dsei-polos-base", dsei)
    per = {n["location"]["name"]: len(n["children"]) for n in dsei[0]["children"]}
    print(f"DSEI tree: 34 DSEIs, {matched} polos base com DSEI identificado; {len(unmatched)} sem DSEI (fora)")
    print(json.dumps(per, ensure_ascii=False, indent=1))
    if "--show-unmatched" in sys.argv:
        for p in unmatched:
            print("  ?", p["NO_FANTASIA"], "|", p["NO_RAZAO_SOCIAL"])


if __name__ == "__main__":
    main()
