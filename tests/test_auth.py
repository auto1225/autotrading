from __future__ import annotations

from pathlib import Path
import base64
import hashlib
import hmac
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upbit_autotrader.upbit_client import build_query_string, create_jwt


def decode_part(part: str) -> dict[str, str]:
    padding = "=" * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode((part + padding).encode("ascii")))


class AuthTests(unittest.TestCase):
    def test_query_string_preserves_array_key_order(self) -> None:
        query = build_query_string(
            {
                "market": "KRW-BTC",
                "states[]": ["wait", "watch"],
                "limit": 10,
            }
        )
        self.assertEqual(query, "market=KRW-BTC&states[]=wait&states[]=watch&limit=10")

    def test_create_jwt_includes_sha512_query_hash(self) -> None:
        query = "market=KRW-BTC&side=bid&price=5000&ord_type=price"
        token = create_jwt("access", "secret", query, nonce="fixed-nonce")
        header_part, payload_part, signature_part = token.split(".")

        header = decode_part(header_part)
        payload = decode_part(payload_part)
        expected_signature = base64.urlsafe_b64encode(
            hmac.new(
                b"secret",
                f"{header_part}.{payload_part}".encode("ascii"),
                hashlib.sha512,
            ).digest()
        ).rstrip(b"=").decode("ascii")

        self.assertEqual(header["alg"], "HS512")
        self.assertEqual(payload["access_key"], "access")
        self.assertEqual(payload["nonce"], "fixed-nonce")
        self.assertEqual(payload["query_hash"], hashlib.sha512(query.encode("utf-8")).hexdigest())
        self.assertEqual(payload["query_hash_alg"], "SHA512")
        self.assertEqual(signature_part, expected_signature)


if __name__ == "__main__":
    unittest.main()
