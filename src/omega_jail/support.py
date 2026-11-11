"""Contact et support d'omega-jail (2026-11-09), en ligne de commande : omega-jail n'a pas
d'interface TUI. Meme fonction que l'ecran « Contact et support » d'omega-serv / omega-log et des
outils de la suite (omega-lib, D-016), bibliotheque standard seulement (omega-jail ne depend que
de PyYAML) :

- `omega-jail contact` : payer un cafe, contacter le support (adresses en clair, aucun formulaire
  ici, aucun mail envoye), comment se declarer ;
- `omega-jail declaration status | declare [--continent X] [--pays Y] [--yes] | withdraw [--yes]` :
  declaration anonyme UNE SEULE FOIS (omega-jail n'a pas de service qui enverrait chaque jour). Sans
  `--yes`, rien n'est envoye : le message exact est seulement affiche (comme le dry-run des jails) ;
- `omega-jail version [--check]` : version installee ; `--check` lit download/sha.txt du site
  (rien n'est envoye, jamais sans cette option).

Message envoye, et rien d'autre : une cle tiree au hasard (sans lien avec la machine), « omega-jail »,
la version, « unique » et, facultatifs, un continent et un pays pris dans des listes fermees (les
memes que la reception, SERV/compteur-reception/index.php). Cle dans var/declaration.json (0600),
jamais livree dans l'archive."""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import secrets
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SOFTWARE = "omega-jail"
SITE_URL = "https://kraynux.snake-mackarel.ts.net/"
RECEPTION_URL = SITE_URL + "compteur/"
DOWNLOAD_URL = SITE_URL + "omega-jail/download/"
PAYPAL_URL = "https://paypal.me/kraynux"
SUPPORT_MAIL = "kraynux@proton.me"
CONTACT_FORM_URL = SITE_URL + "contact/"
TIMEOUT_SECONDS = 5.0
MAX_BYTES = 64 * 1024
MODE_ONCE = "unique"
OTHER = "autre"
CONTINENTS = ("AF", "AN", "AS", "EU", "NA", "OC", "SA")
COUNTRY_CODES = (
    "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT", "AU", "AW", "AX", "AZ",
    "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BL", "BM", "BN", "BO", "BQ", "BR", "BS",
    "BT", "BV", "BW", "BY", "BZ", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN",
    "CO", "CR", "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM", "DO", "DZ", "EC", "EE",
    "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FK", "FM", "FO", "FR", "GA", "GB", "GD", "GE", "GF",
    "GG", "GH", "GI", "GL", "GM", "GN", "GP", "GQ", "GR", "GS", "GT", "GU", "GW", "GY", "HK", "HM",
    "HN", "HR", "HT", "HU", "ID", "IE", "IL", "IM", "IN", "IO", "IQ", "IR", "IS", "IT", "JE", "JM",
    "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN", "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC",
    "LI", "LK", "LR", "LS", "LT", "LU", "LV", "LY", "MA", "MC", "MD", "ME", "MF", "MG", "MH", "MK",
    "ML", "MM", "MN", "MO", "MP", "MQ", "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA",
    "NC", "NE", "NF", "NG", "NI", "NL", "NO", "NP", "NR", "NU", "NZ", "OM", "PA", "PE", "PF", "PG",
    "PH", "PK", "PL", "PM", "PN", "PR", "PS", "PT", "PW", "PY", "QA", "RE", "RO", "RS", "RU", "RW",
    "SA", "SB", "SC", "SD", "SE", "SG", "SH", "SI", "SJ", "SK", "SL", "SM", "SN", "SO", "SR", "SS",
    "ST", "SV", "SX", "SY", "SZ", "TC", "TD", "TF", "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO",
    "TR", "TT", "TV", "TW", "TZ", "UA", "UG", "UM", "US", "UY", "UZ", "VA", "VC", "VE", "VG", "VI",
    "VN", "VU", "WF", "WS", "YE", "YT", "ZA", "ZM", "ZW",
)

_KEY = re.compile(r"^[0-9a-f]{32}$")
_VERSION_LINE = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)


@dataclass(frozen=True)
class StoredDeclaration:
    key: str
    continent: str
    country: str
    declared_at: datetime


# ------------------------------------------------------------------------------ regles (pures)
def project_version(project_root: Path) -> str:
    """pyproject.toml, seule source de la version (livre dans l'archive)."""
    try:
        match = _VERSION_LINE.search((project_root / "pyproject.toml").read_text(encoding="utf-8"))
    except OSError:
        match = None
    return match.group(1) if match else "0.0.0"


def build_payload(key: str, version: str, continent: str = "", country: str = "") -> dict[str, str]:
    """Le message exact envoye (et affiche avant l'envoi)."""
    errors = []
    if not _KEY.match(key):
        errors.append("cle")
    if continent and continent not in (*CONTINENTS, OTHER):
        errors.append("continent")
    if country and country not in (*COUNTRY_CODES, OTHER):
        errors.append("pays")
    if errors:
        raise ValueError(", ".join(errors))
    payload = {"cle": key, "logiciel": SOFTWARE, "version": version, "envoi": MODE_ONCE}
    if continent:
        payload["continent"] = continent
    if country:
        payload["pays"] = country
    return payload


def version_key(version: str) -> tuple[int, ...] | None:
    parts = version.strip().split(".")
    if not parts or not all(part.isdigit() for part in parts):
        return None
    numbers = [int(part) for part in parts]
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)


def latest_published(sha_list: str) -> str | None:
    """Plus haute version citee dans sha.txt (`<empreinte>  omega-jail-1.2.0.tar.gz`)."""
    found = set(re.findall(r"omega-jail-(\d+(?:\.\d+){1,3})\.tar\.gz", sha_list))
    return max(found, key=lambda version: version_key(version) or ()) if found else None


# ------------------------------------------------------------------------------ stockage, reseau
class DeclarationStore:
    """var/declaration.json : ecriture atomique (temporaire puis rename), fichier en 0600."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> StoredDeclaration | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            declared_at = datetime.fromisoformat(str(data.get("declare_le") or ""))
        except (OSError, ValueError, AttributeError):
            return None
        if not isinstance(data.get("cle"), str):
            return None
        return StoredDeclaration(data["cle"], str(data.get("continent") or ""), str(data.get("pays") or ""),
                                 declared_at)

    def save(self, stored: StoredDeclaration) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"cle": stored.key, "continent": stored.continent, "pays": stored.country,
                   "declare_le": stored.declared_at.isoformat()}
        tmp = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
            os.replace(tmp, self.path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

    def delete(self) -> None:
        with contextlib.suppress(OSError):
            self.path.unlink(missing_ok=True)


def send(payload: Mapping[str, object], version: str, url: str = RECEPTION_URL) -> str:
    """POST HTTPS (certificat verifie, 5 s). Renvoie "" si accepte, sinon la raison. Ne leve jamais."""
    request = urllib.request.Request(
        url, data=json.dumps(payload, separators=(",", ":")).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "User-Agent": f"{SOFTWARE}/{version}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        return f"http-{error.code}"
    except (urllib.error.URLError, OSError, ValueError):
        return "unreachable"
    return "" if 200 <= status < 300 else f"http-{status}"


def fetch_sha_list(version: str, url: str = DOWNLOAD_URL + "sha.txt") -> str | None:
    request = urllib.request.Request(url, headers={"User-Agent": f"{SOFTWARE}/{version}"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            if not 200 <= response.status < 300:
                return None
            body: bytes = response.read(MAX_BYTES)
            return body.decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError):
        return None


# ------------------------------------------------------------------------------ commandes
SUPPORT_COMMANDS = ("contact", "declaration", "version")


def build_support_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="omega-jail", description="Contact et support d'omega-jail")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("contact", help="Payer un cafe, contacter le support, se declarer")
    declaration = sub.add_parser("declaration", help="Declaration anonyme d'utilisateur (une seule fois)")
    actions = declaration.add_subparsers(dest="action", required=True)
    actions.add_parser("status", help="Etat de la declaration sur cette installation")
    declare = actions.add_parser("declare", help="Se declarer utilisateur anonyme (une seule fois)")
    declare.add_argument("--continent", choices=(*CONTINENTS, OTHER), default="", help="Facultatif")
    declare.add_argument("--pays", default="", help="Facultatif : code ISO 3166-1 alpha-2 (FR, BE...) ou autre")
    declare.add_argument("--yes", action="store_true", help="Confirme l'envoi (sans : message affiche seulement)")
    withdraw = actions.add_parser("withdraw", help="Ne plus se declarer (l'entree est supprimee a la reception)")
    withdraw.add_argument("--yes", action="store_true", help="Confirme le retrait")
    version = sub.add_parser("version", help="Version installee")
    version.add_argument("--check", action="store_true", help="Comparer a la derniere version publiee sur le site")
    return parser


def _when(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


def run_support(argv: list[str], project_root: Path) -> int:
    args = build_support_parser().parse_args(argv)
    version = project_version(project_root)
    store = DeclarationStore(project_root / "var" / "declaration.json")
    if args.command == "contact":
        return _contact(store)
    if args.command == "version":
        return _version(version, check=args.check)
    if args.action == "status":
        return _status(store)
    if args.action == "declare":
        return _declare(store, version, args.continent, args.pays.upper() if args.pays != OTHER else OTHER,
                        confirmed=args.yes)
    return _withdraw(store, version, confirmed=args.yes)


def _contact(store: DeclarationStore) -> int:
    print("CONTACT ET SUPPORT")
    print("Aidez le developpeur : omega-jail est developpe et maintenu par une seule personne.\n")
    print("Payer un cafe")
    print("  Un don aide a couvrir les frais des serveurs (electricite).")
    print(f"  {PAYPAL_URL}\n")
    print("Se declarer utilisateur (anonyme)")
    print("  Une declaration volontaire et anonyme, qui sert uniquement a compter les utilisateurs et,")
    print("  si vous le souhaitez, leur continent ou leur pays. Envoi : une seule fois.")
    stored = store.load()
    state = f"declare le {_when(stored.declared_at)}" if stored else "non declare"
    print(f"  Etat : {state}.")
    print("  omega-jail declaration declare [--continent EU] [--pays FR]   (affiche le message exact)")
    print("  omega-jail declaration withdraw --yes                          (ne plus me declarer)\n")
    print("Contacter le support")
    print(f"  Mail : {SUPPORT_MAIL}")
    print(f"  Formulaire de contact : {CONTACT_FORM_URL}\n")
    print("Version et mises a jour")
    print("  omega-jail version --check   (lit la liste des versions publiees ; rien n'est envoye)")
    return 0


def _status(store: DeclarationStore) -> int:
    stored = store.load()
    if stored is None:
        print("Non declare (aucune cle sur cette installation).")
    else:
        print(f"Declare utilisateur anonyme depuis le {_when(stored.declared_at)}.")
        print("Envoi : une seule fois")
        print(f"Cle : {stored.key}")
        print(f"Continent : {stored.continent or '-'}")
        print(f"Pays : {stored.country or '-'}")
    print(f"Destination : {RECEPTION_URL}")
    return 0


def _declare(store: DeclarationStore, version: str, continent: str, country: str, *, confirmed: bool) -> int:
    existing = store.load()
    key = existing.key if existing is not None else secrets.token_hex(16)
    try:
        payload = build_payload(key, version, continent, country)
    except ValueError as error:
        print(f"erreur : declaration refusee ({error}) - pays : code ISO a deux lettres (FR, BE...) ou autre.")
        return 2
    if not confirmed:
        shown = dict(payload)
        if existing is None:
            shown["cle"] = "<cle tiree au hasard a l'envoi>"
        print(f"Message qui sera envoye a {RECEPTION_URL} :")
        print("  " + json.dumps(shown, ensure_ascii=False))
        print("Jamais envoyes : votre nom, le nom de la machine, vos reglages, vos jails ni vos journaux.")
        print("Votre adresse IP n'est pas enregistree dans les declarations. Comme pour toute visite d'un site,")
        print("elle passe par les controles de securite et le journal technique du serveur de reception.")
        print("Ajoutez --yes pour confirmer la declaration.")
        return 1
    reason = send(payload, version)
    if reason:
        print(f"Reception injoignable ({reason}) : rien n'a ete enregistre, reessayez plus tard.")
        return 1
    declared_at = existing.declared_at if existing is not None else datetime.now(timezone.utc)
    store.save(StoredDeclaration(key, continent, country, declared_at))
    print("Merci ! Vous etes declare utilisateur anonyme.")
    return 0


def _withdraw(store: DeclarationStore, version: str, *, confirmed: bool) -> int:
    existing = store.load()
    if existing is None:
        print("Non declare : rien a retirer.")
        return 0
    if not confirmed:
        print("Votre entree sera supprimee du compteur et la cle effacee de cette installation.")
        print("Ajoutez --yes pour confirmer le retrait.")
        return 1
    reason = send({"cle": existing.key, "retrait": True}, version)
    store.delete()
    if reason:
        print("Cle effacee. Reception injoignable : votre entree y disparaitra seule (1 an).")
    else:
        print("Vous n'etes plus declare : votre entree est supprimee et la cle effacee.")
    return 0


def _version(version: str, *, check: bool) -> int:
    print(f"omega-jail {version}")
    if not check:
        return 0
    sha_list = fetch_sha_list(version)
    latest = latest_published(sha_list) if sha_list else None
    installed_key = version_key(version)
    if latest is None or installed_key is None:
        print("Site injoignable ou liste des versions illisible : reessayez plus tard.")
        return 1
    latest_key = version_key(latest) or ()
    if latest_key > installed_key:
        print(f"Nouvelle version disponible : {latest}.")
        print(f"Archive : {DOWNLOAD_URL}omega-jail-{latest}.tar.gz")
        print(f"Nouveautes : {DOWNLOAD_URL}omega-jail-{latest}-nouveautes.txt")
    elif latest_key < installed_key:
        print(f"Votre version est plus recente que la derniere publiee ({latest}) : version en cours, "
              "pas encore publiee.")
    else:
        print("Vous avez la derniere version publiee.")
    return 0
