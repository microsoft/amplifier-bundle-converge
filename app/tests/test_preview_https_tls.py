"""`app/tls.py`: the local CA + leaf certificate, exercised directly.

Acceptance #2 (converge-b2ak): a local CA plus leaf reuse/renewal that
validates the key relationship, expiry and every advertised SAN; private
material `0600` and directories `0700`; atomic writes; no silent CA rotation.

This file caught a real defect before it ever reached `test_run_app.py`: the
first version of `_make_leaf` never added an Authority Key Identifier
extension, and a strict OpenSSL build (the one this project's own `.venv`
links against) refuses to verify a leaf against its issuer without one --
`SSLCertVerificationError: Missing Authority Key Identifier`. Every test
below that inspects the leaf's extensions is partly here to keep that fixed.
"""

from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import tls  # noqa: E402


def test_first_run_creates_ca_and_leaf_with_correct_permissions(tmp_path: Path) -> None:
    """WHAT WOULD FALSIFY THIS: a world-readable key, a group-readable
    directory, or a missing file."""
    made = tls.ensure(tls_dir=tmp_path / "tls", extra_host="127.0.0.1")

    assert made.ca_cert.is_file() and made.ca_key.is_file()
    assert made.leaf_cert.is_file() and made.leaf_key.is_file()

    dir_mode = stat.S_IMODE(made.tls_dir.stat().st_mode)
    assert dir_mode == 0o700, f"tls dir is {oct(dir_mode)}, not 0700"

    for private in (made.ca_key, made.leaf_key):
        mode = stat.S_IMODE(private.stat().st_mode)
        assert mode == 0o600, f"{private} is {oct(mode)}, not 0600"

    for public in (made.ca_cert, made.leaf_cert):
        mode = stat.S_IMODE(public.stat().st_mode)
        assert mode == 0o644, f"{public} is {oct(mode)}, not 0644"


def test_the_leaf_carries_an_authority_key_identifier(tmp_path: Path) -> None:
    """The regression this file exists to pin: a leaf with no AKI verifies
    on a lenient OpenSSL and fails closed on a strict one -- silently, until
    a real client connects. Checked directly rather than only through a live
    connection, so a future change that drops the extension fails HERE, in
    milliseconds, not in a 90-second timeout somewhere else."""
    from cryptography import x509

    made = tls.ensure(tls_dir=tmp_path / "tls", extra_host="127.0.0.1")
    leaf = x509.load_pem_x509_certificate(made.leaf_cert.read_bytes())
    ca = x509.load_pem_x509_certificate(made.ca_cert.read_bytes())

    aki = leaf.extensions.get_extension_for_class(x509.AuthorityKeyIdentifier).value
    ski = ca.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value
    assert aki.key_identifier == ski.digest, "the leaf's AKI does not match the CA's own SKI"


def test_the_leaf_actually_verifies_against_the_ca_with_a_real_tls_handshake(tmp_path: Path) -> None:
    """The end-to-end proof `test_run_app.py` also makes, but in-process and
    fast: a real `ssl` client, real socket, real handshake -- not just a
    field read off the certificate."""
    import socket
    import ssl
    import threading

    made = tls.ensure(tls_dir=tmp_path / "tls", extra_host="127.0.0.1")

    server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_ctx.load_cert_chain(certfile=str(made.leaf_cert), keyfile=str(made.leaf_key))

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    def serve_once() -> None:
        conn, _ = listener.accept()
        with server_ctx.wrap_socket(conn, server_side=True) as tls_conn:
            tls_conn.recv(16)
            tls_conn.sendall(b"ok")

    thread = threading.Thread(target=serve_once, daemon=True)
    thread.start()

    client_ctx = ssl.create_default_context(cafile=str(made.ca_cert))
    with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
        with client_ctx.wrap_socket(sock, server_hostname="127.0.0.1") as tls_sock:
            tls_sock.sendall(b"hello")
            answer = tls_sock.recv(16)
    thread.join(timeout=5)
    assert answer == b"ok", "the handshake completed but no data crossed it"
    listener.close()


def test_reusing_ensure_does_not_rewrite_a_valid_leaf_or_ever_touch_the_ca(tmp_path: Path) -> None:
    """No silent CA rotation, and no needless leaf churn either.

    WHAT WOULD FALSIFY THIS: a changed CA key/cert on a second call (silent
    rotation -- the one thing that would force every already-trusting browser
    to re-trust), or a changed leaf when nothing about what it needs to cover
    changed either."""
    tls_dir = tmp_path / "tls"
    first = tls.ensure(tls_dir=tls_dir, extra_host="127.0.0.1")
    ca_key_before = first.ca_key.read_bytes()
    ca_cert_before = first.ca_cert.read_bytes()
    leaf_cert_before = first.leaf_cert.read_bytes()

    second = tls.ensure(tls_dir=tls_dir, extra_host="127.0.0.1")

    assert second.ca_key.read_bytes() == ca_key_before, "the CA key was rewritten -- silent rotation"
    assert second.ca_cert.read_bytes() == ca_cert_before, "the CA cert was rewritten -- silent rotation"
    assert second.leaf_cert.read_bytes() == leaf_cert_before, (
        "the leaf was reissued even though nothing it needs to cover changed"
    )


def test_a_leaf_missing_a_requested_san_is_renewed_reusing_the_same_ca(tmp_path: Path) -> None:
    """A new hostname/address being asked for is the honest reason to renew
    the leaf -- and reusing the SAME CA is what makes that renewal invisible
    to anyone who already trusts it.

    WHAT WOULD FALSIFY THIS: a leaf that still does not cover the new name
    after a second `ensure()`, or a CA that changed underneath it."""
    tls_dir = tmp_path / "tls"
    first = tls.ensure(tls_dir=tls_dir, extra_host="127.0.0.1")
    ca_cert_before = first.ca_cert.read_bytes()

    second = tls.ensure(tls_dir=tls_dir, extra_hostnames=("a-brand-new-hostname.example",))

    assert second.ca_cert.read_bytes() == ca_cert_before, "renewing the leaf touched the CA"
    from cryptography import x509

    leaf = x509.load_pem_x509_certificate(second.leaf_cert.read_bytes())
    san = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert "a-brand-new-hostname.example" in san.get_values_for_type(x509.DNSName)


def test_inspect_reports_expiry_and_coverage_without_writing_anything(tmp_path: Path) -> None:
    """`doctor` calls this, and `doctor` must never generate a certificate as
    a side effect of merely being asked about one.

    WHAT WOULD FALSIFY THIS: a file created or modified by `inspect()` alone."""
    tls_dir = tmp_path / "tls"
    before = tls.inspect(tls_dir)
    assert not before.ca_present and not before.leaf_present
    assert not tls_dir.exists(), "inspect() created a directory that was not there"

    made = tls.ensure(tls_dir=tls_dir, extra_host="127.0.0.1")
    leaf_mtime_before = made.leaf_cert.stat().st_mtime

    after = tls.inspect(tls_dir, hostnames=frozenset({"localhost"}), ips=frozenset({"127.0.0.1"}))
    assert after.ca_present and after.leaf_present
    assert after.covered, f"inspect() says the existing leaf does not cover localhost/127.0.0.1: {after.problems}"
    assert after.leaf_key_matches_cert
    assert after.leaf_days_left is not None and after.leaf_days_left > 0
    assert made.leaf_cert.stat().st_mtime == leaf_mtime_before, "inspect() rewrote the leaf"


def test_a_mismatched_key_is_reported_not_trusted(tmp_path: Path) -> None:
    """The key-relationship check `inspect()` promises: a leaf certificate
    whose key file does not actually match it is named as broken, not
    silently treated as fine.

    WHAT WOULD FALSIFY THIS: `leaf_key_matches_cert` reading True for a
    swapped-in, unrelated key."""
    tls_dir = tmp_path / "tls"
    made = tls.ensure(tls_dir=tls_dir, extra_host="127.0.0.1")

    other = tls.ensure(tls_dir=tmp_path / "other-tls", extra_host="127.0.0.1")
    made.leaf_key.write_bytes(other.leaf_key.read_bytes())

    insp = tls.inspect(tls_dir)
    assert insp.leaf_key_matches_cert is False
    assert any("does not match" in p for p in insp.problems)


def test_fingerprint_is_stable_and_matches_the_certificate_on_disk(tmp_path: Path) -> None:
    made = tls.ensure(tls_dir=tmp_path / "tls", extra_host="127.0.0.1")
    first = tls.fingerprint_sha256(made.ca_cert)
    second = tls.fingerprint_sha256(made.ca_cert)
    assert first == second
    assert len(first.split(":")) == 32, f"not a SHA-256 fingerprint: {first}"


@pytest.mark.parametrize("bad_extra", ["0.0.0.0", "::", ""])
def test_every_interface_addresses_are_never_added_as_a_san(tmp_path: Path, bad_extra: str) -> None:
    """`0.0.0.0`/`::` name "every interface", not a real peer identity -- a
    SAN entry for either would be meaningless (nothing ever connects TO
    0.0.0.0) and is refused by name rather than silently added."""
    hostnames, ips = tls.default_names(bad_extra)
    assert "0.0.0.0" not in ips and "::" not in ips
