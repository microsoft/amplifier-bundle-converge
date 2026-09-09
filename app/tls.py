"""A local certificate authority, and the one leaf certificate it signs.

Why a local CA at all, rather than one self-signed leaf: a browser trusts a
certificate by walking to a root it already trusts. A single self-signed leaf
*is* its own root, and every renewal (a new SAN, a new machine hostname) would
ask a person to re-trust a brand new root -- forever re-teaching the trust
prompt. A CA that is created once and never rotated lets the leaf be reissued
freely (new hostname, new LAN address, approaching expiry) while the one
thing a person actually trusted -- ``ca.crt`` -- never changes underneath
them. That is the whole reason this module is two certificates and not one.

Layout, under ``tls_dir`` (default ``~/.amplifier/converge-app-tls``, override
with ``--tls-dir`` or ``$CONVERGE_TLS_DIR``):

    ca.key    0600  -- the CA's private key. Never served, never rotated once made.
    ca.crt    0644  -- the CA's public certificate. This is the ONE file /ca.crt serves.
    leaf.key  0600  -- the server's private key. Never served.
    leaf.crt  0644  -- the server's certificate, signed by ca.crt, reissued as needed.

The directory itself is ``0700``: only this account can even list what is in
it, on top of the per-file permissions above.

Nothing here is silent. ``ensure()`` is the only function that writes, and it
writes for exactly three reasons, each one a fact this module can name out
loud: the CA is absent (first run), the leaf is absent or expiring inside
``RENEW_WITHIN_DAYS``, or the leaf's own SAN list no longer covers every
hostname/address being asked for (the machine's address changed, or a caller
asked to serve a name it did not before). The CA itself is never touched by
a leaf renewal -- rotating it silently would break the one thing a person
already told their browser to trust.

``inspect()`` is the read-only twin doctor uses: it says what is on disk, its
expiry, its SAN coverage, and whether the key on disk actually belongs to the
certificate beside it -- and it never writes a byte.
"""

from __future__ import annotations

import datetime as _dt
import ipaddress
import os
import socket
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

#: Default home for the CA and the leaf cert it signs -- separate from the
#: existing `~/.amplifier/converge-app.*` files on purpose (acceptance #1:
#: "Expose app root/state dir and port explicitly so preview is fully
#: separate"). Override with `--tls-dir` or `$CONVERGE_TLS_DIR`.
DEFAULT_TLS_DIR = Path.home() / ".amplifier" / "converge-app-tls"
TLS_DIR_ENV = "CONVERGE_TLS_DIR"

CA_KEY_NAME = "ca.key"
CA_CERT_NAME = "ca.crt"
LEAF_KEY_NAME = "leaf.key"
LEAF_CERT_NAME = "leaf.crt"

CA_COMMON_NAME = "Converge Preview Local CA"
LEAF_COMMON_NAME = "converge-app"

#: A local root is not a publicly-trusted one, so it is not bound to the
#: public CA/Browser Forum's shrinking maximum lifetimes -- ten years is a
#: root a person sets up once. The leaf still respects a conservative
#: lifetime so "reused across a renewal" never means "never re-checked".
CA_VALIDITY_DAYS = 3650
LEAF_VALIDITY_DAYS = 397

#: Renew the leaf when its own expiry is closer than this many days, or when
#: its recorded SAN set no longer covers what is being asked for.
RENEW_WITHIN_DAYS = 30


def _tls_dir(tls_dir: Path | None) -> Path:
    if tls_dir is not None:
        return Path(tls_dir).expanduser()
    env = os.environ.get(TLS_DIR_ENV, "").strip()
    if env:
        return Path(env).expanduser()
    return DEFAULT_TLS_DIR


@dataclass(frozen=True)
class CertPaths:
    """Where every file lives, once `ensure()` has run."""

    tls_dir: Path
    ca_key: Path
    ca_cert: Path
    leaf_key: Path
    leaf_cert: Path


def paths(tls_dir: Path | None = None) -> CertPaths:
    base = _tls_dir(tls_dir)
    return CertPaths(
        tls_dir=base,
        ca_key=base / CA_KEY_NAME,
        ca_cert=base / CA_CERT_NAME,
        leaf_key=base / LEAF_KEY_NAME,
        leaf_cert=base / LEAF_CERT_NAME,
    )


# --------------------------------------------------------------------------
# writing -- private material 0600, the directory 0700, atomic either way
# --------------------------------------------------------------------------


def _write(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    tmp = path.with_name(path.name + ".writing")
    handle = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(handle, "wb") as out:
        out.write(data)
    os.chmod(tmp, mode)  # belt: O_CREAT's mode is filtered by umask
    tmp.replace(path)


def _write_private(path: Path, data: bytes) -> None:
    _write(path, data, 0o600)


def _write_public(path: Path, data: bytes) -> None:
    _write(path, data, 0o644)


# --------------------------------------------------------------------------
# names this leaf should cover
# --------------------------------------------------------------------------


def default_names(extra_host: str | None = None) -> tuple[frozenset[str], frozenset[str]]:
    """localhost, loopbacks, this machine's own hostname(s), and its current
    non-loopback addresses -- plus whatever `extra_host` (the requested bind
    address, when it names one host rather than "every interface") adds.
    """
    hostnames: set[str] = {"localhost"}
    ips: set[str] = {"127.0.0.1", "::1"}
    try:
        hostnames.add(socket.gethostname())
    except OSError:
        pass
    try:
        fqdn = socket.getfqdn()
        if fqdn and fqdn.lower() != "localhost":
            hostnames.add(fqdn)
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            addr = info[4][0]
            if ":" not in addr and not addr.startswith("127."):
                ips.add(addr)
    except OSError:
        pass
    if extra_host:
        candidate = extra_host.strip()
        if candidate and candidate not in ("0.0.0.0", "::", ""):
            try:
                ipaddress.ip_address(candidate)
                ips.add(candidate)
            except ValueError:
                hostnames.add(candidate)
    return frozenset(hostnames), frozenset(ips)


def _san_extension(hostnames: frozenset[str], ips: frozenset[str]) -> x509.SubjectAlternativeName:
    entries: list[x509.GeneralName] = [x509.DNSName(h) for h in sorted(hostnames)]
    entries += [x509.IPAddress(ipaddress.ip_address(ip)) for ip in sorted(ips)]
    return x509.SubjectAlternativeName(entries)


# --------------------------------------------------------------------------
# making the two certificates
# --------------------------------------------------------------------------


def _make_ca() -> tuple[bytes, bytes]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, CA_COMMON_NAME)])
    now = _dt.datetime.now(_dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - _dt.timedelta(minutes=5))
        .not_valid_after(now + _dt.timedelta(days=CA_VALIDITY_DAYS))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .sign(key, hashes.SHA256())
    )
    key_bytes = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    return key_bytes, cert.public_bytes(serialization.Encoding.PEM)


def _make_leaf(
    ca_key_bytes: bytes, ca_cert_bytes: bytes, hostnames: frozenset[str], ips: frozenset[str]
) -> tuple[bytes, bytes]:
    ca_key = serialization.load_pem_private_key(ca_key_bytes, password=None)
    ca_cert = x509.load_pem_x509_certificate(ca_cert_bytes)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, LEAF_COMMON_NAME)])
    now = _dt.datetime.now(_dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - _dt.timedelta(minutes=5))
        .not_valid_after(now + _dt.timedelta(days=LEAF_VALIDITY_DAYS))
        .add_extension(_san_extension(hostnames, ips), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False
        )
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    key_bytes = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    return key_bytes, cert.public_bytes(serialization.Encoding.PEM)


# --------------------------------------------------------------------------
# reading what is already there -- no side effects, ever
# --------------------------------------------------------------------------


def _cert_names(cert: x509.Certificate) -> tuple[set[str], set[str]]:
    hostnames: set[str] = set()
    ips: set[str] = set()
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        hostnames = set(san.get_values_for_type(x509.DNSName))
        ips = {str(one) for one in san.get_values_for_type(x509.IPAddress)}
    except x509.ExtensionNotFound:
        pass
    return hostnames, ips


def _keys_match(cert: x509.Certificate, key_bytes: bytes) -> bool:
    try:
        key = serialization.load_pem_private_key(key_bytes, password=None)
        return key.public_key().public_numbers() == cert.public_key().public_numbers()
    except Exception:  # noqa: BLE001 - a corrupt key is "does not match", not a crash
        return False


@dataclass
class Inspection:
    tls_dir: Path
    ca_present: bool = False
    ca_expires: str = ""
    leaf_present: bool = False
    leaf_expires: str = ""
    leaf_days_left: int | None = None
    leaf_sans: list[str] = field(default_factory=list)
    leaf_key_matches_cert: bool = False
    covers: tuple[frozenset[str], frozenset[str]] | None = None
    covered: bool = False
    problems: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "tls_dir": str(self.tls_dir),
            "ca_present": self.ca_present,
            "ca_expires": self.ca_expires,
            "leaf_present": self.leaf_present,
            "leaf_expires": self.leaf_expires,
            "leaf_days_left": self.leaf_days_left,
            "leaf_sans": self.leaf_sans,
            "leaf_key_matches_cert": self.leaf_key_matches_cert,
            "covered": self.covered,
            "problems": self.problems,
        }


def inspect(
    tls_dir: Path | None = None,
    hostnames: frozenset[str] | None = None,
    ips: frozenset[str] | None = None,
) -> Inspection:
    """What is on disk, right now. Never writes, never generates."""
    p = paths(tls_dir)
    out = Inspection(tls_dir=p.tls_dir)
    now = _dt.datetime.now(_dt.timezone.utc)

    if p.ca_cert.is_file():
        out.ca_present = True
        try:
            ca_cert = x509.load_pem_x509_certificate(p.ca_cert.read_bytes())
            out.ca_expires = ca_cert.not_valid_after_utc.isoformat()
        except Exception as exc:  # noqa: BLE001
            out.problems.append(f"ca.crt could not be read: {exc}")
    else:
        out.problems.append(f"no CA certificate at {p.ca_cert}")

    if p.leaf_cert.is_file():
        out.leaf_present = True
        try:
            leaf_cert = x509.load_pem_x509_certificate(p.leaf_cert.read_bytes())
            out.leaf_expires = leaf_cert.not_valid_after_utc.isoformat()
            out.leaf_days_left = (leaf_cert.not_valid_after_utc - now).days
            san_hosts, san_ips = _cert_names(leaf_cert)
            out.leaf_sans = sorted(san_hosts) + sorted(san_ips)
            if out.leaf_days_left < 0:
                out.problems.append(f"leaf.crt expired {-out.leaf_days_left} day(s) ago")
            elif out.leaf_days_left < RENEW_WITHIN_DAYS:
                out.problems.append(f"leaf.crt expires in {out.leaf_days_left} day(s) -- due for renewal")
            if p.leaf_key.is_file():
                out.leaf_key_matches_cert = _keys_match(leaf_cert, p.leaf_key.read_bytes())
                if not out.leaf_key_matches_cert:
                    out.problems.append("leaf.key does not match the public key in leaf.crt")
            else:
                out.problems.append(f"no private key at {p.leaf_key}")
            if hostnames is not None or ips is not None:
                want_hosts = hostnames or frozenset()
                want_ips = ips or frozenset()
                out.covered = want_hosts <= san_hosts and want_ips <= san_ips
                if not out.covered:
                    missing = sorted((want_hosts - san_hosts) | (want_ips - san_ips))
                    out.problems.append(f"leaf.crt does not cover: {', '.join(missing)}")
        except Exception as exc:  # noqa: BLE001
            out.problems.append(f"leaf.crt could not be read: {exc}")
    else:
        out.problems.append(f"no server certificate at {p.leaf_cert}")

    return out


def fingerprint_sha256(cert_path: Path) -> str:
    """The colon-separated SHA-256 fingerprint a person compares by eye."""
    cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    digest = cert.fingerprint(hashes.SHA256())
    return ":".join(f"{b:02X}" for b in digest)


# --------------------------------------------------------------------------
# the one function that writes
# --------------------------------------------------------------------------


def ensure(
    tls_dir: Path | None = None,
    extra_host: str | None = None,
    extra_hostnames: frozenset[str] | tuple[str, ...] = (),
    extra_ips: frozenset[str] | tuple[str, ...] = (),
) -> CertPaths:
    """Create the CA if it is missing; (re)issue the leaf as needed.

    Three, and only three, reasons the leaf is (re)written: it is absent, it
    is inside `RENEW_WITHIN_DAYS` of expiry, or its SAN set no longer covers
    every name being asked for. The CA is created once, on the first call
    that finds none, and is never touched again by this function.
    """
    p = paths(tls_dir)
    want_hosts, want_ips = default_names(extra_host)
    want_hosts = frozenset(want_hosts) | frozenset(extra_hostnames)
    want_ips = frozenset(want_ips) | frozenset(extra_ips)

    if not (p.ca_key.is_file() and p.ca_cert.is_file()):
        ca_key_bytes, ca_cert_bytes = _make_ca()
        _write_private(p.ca_key, ca_key_bytes)
        _write_public(p.ca_cert, ca_cert_bytes)
    ca_key_bytes = p.ca_key.read_bytes()
    ca_cert_bytes = p.ca_cert.read_bytes()

    needs_leaf = True
    if p.leaf_cert.is_file() and p.leaf_key.is_file():
        try:
            leaf_cert = x509.load_pem_x509_certificate(p.leaf_cert.read_bytes())
            now = _dt.datetime.now(_dt.timezone.utc)
            days_left = (leaf_cert.not_valid_after_utc - now).days
            san_hosts, san_ips = _cert_names(leaf_cert)
            covers = want_hosts <= san_hosts and want_ips <= san_ips
            key_ok = _keys_match(leaf_cert, p.leaf_key.read_bytes())
            issuer_ok = leaf_cert.issuer == x509.load_pem_x509_certificate(ca_cert_bytes).subject
            needs_leaf = not (days_left >= RENEW_WITHIN_DAYS and covers and key_ok and issuer_ok)
        except Exception:  # noqa: BLE001 - unreadable is exactly "needs (re)issuing"
            needs_leaf = True

    if needs_leaf:
        leaf_key_bytes, leaf_cert_bytes = _make_leaf(ca_key_bytes, ca_cert_bytes, want_hosts, want_ips)
        _write_private(p.leaf_key, leaf_key_bytes)
        _write_public(p.leaf_cert, leaf_cert_bytes)

    return p


def origin_host(url: str) -> str:
    """scheme://host[:port] of a URL, for the same-origin checks in auth.py."""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


__all__ = [
    "CA_CERT_NAME",
    "CA_KEY_NAME",
    "DEFAULT_TLS_DIR",
    "LEAF_CERT_NAME",
    "LEAF_KEY_NAME",
    "RENEW_WITHIN_DAYS",
    "TLS_DIR_ENV",
    "CertPaths",
    "Inspection",
    "default_names",
    "ensure",
    "fingerprint_sha256",
    "inspect",
    "origin_host",
    "paths",
]
